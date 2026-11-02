"""用已安装的 CoolProp 重算本次 COP 工作簿；保留公式、格式和图示。"""
from __future__ import annotations

import argparse
import ast
import json
import math
import operator
from pathlib import Path
import re
import tempfile
import xml.etree.ElementTree as ET
from xml.sax.saxutils import escape
import zipfile

from CoolProp.CoolProp import PropsSI

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}
REL = 'http://schemas.openxmlformats.org/officeDocument/2006/relationships'
REF = re.compile(r'(?<![A-Za-z0-9_])([$]?)([A-Z]{1,3})([$]?)([1-9][0-9]*)(?![A-Za-z0-9_])')


def column_number(name):
    result = 0
    for letter in name:
        result = result * 26 + ord(letter) - 64
    return result


def column_name(number):
    result = ''
    while number:
        number, rem = divmod(number - 1, 26)
        result = chr(65 + rem) + result
    return result


def translate(formula, origin, target):
    a = REF.fullmatch(origin)
    b = REF.fullmatch(target)
    dx = column_number(b[2]) - column_number(a[2])
    dy = int(b[4]) - int(a[4])
    def shift(match):
        x = column_number(match[2]) + (0 if match[1] else dx)
        y = int(match[4]) + (0 if match[3] else dy)
        if x < 1 or y < 1:
            raise ValueError('Invalid shared-formula reference')
        return match[1] + column_name(x) + match[3] + str(y)
    # Quoted fluid names and property identifiers must remain literal strings.
    parts = re.split(r'("(?:[^\"]|\"\")*")', formula)
    return ''.join(part if i % 2 else REF.sub(shift, part) for i, part in enumerate(parts))


def read_workbook(path):
    records, paths = {}, {}
    with zipfile.ZipFile(path) as archive:
        shared_strings = []
        if 'xl/sharedStrings.xml' in archive.namelist():
            for si in ET.fromstring(archive.read('xl/sharedStrings.xml')).findall('m:si', NS):
                shared_strings.append(''.join(t.text or '' for t in si.findall('.//m:t', NS)))
        links = {e.get('Id'): e.get('Target') for e in ET.fromstring(archive.read('xl/_rels/workbook.xml.rels'))}
        book = ET.fromstring(archive.read('xl/workbook.xml'))
        for sheet in book.findall('m:sheets/m:sheet', NS):
            name = sheet.get('name')
            target = links[sheet.get(f'{{{REL}}}id')]
            entry = target.lstrip('/') if target.startswith('/') else 'xl/' + target
            paths[name] = entry
            cells, shared = {}, {}
            elements = ET.fromstring(archive.read(entry)).findall('.//m:sheetData/m:row/m:c', NS)
            for cell in elements:
                f = cell.find('m:f', NS)
                if f is not None and f.get('t') == 'shared' and f.text:
                    shared[f.get('si')] = (cell.get('r'), f.text)
            for cell in elements:
                address = cell.get('r')
                f = cell.find('m:f', NS)
                formula = None
                if f is not None:
                    formula = f.text
                    if f.get('t') == 'shared' and not formula:
                        origin, master = shared[f.get('si')]
                        formula = translate(master, origin, address)
                    if not formula:
                        raise ValueError(f'Unresolved formula: {name}!{address}')
                    formula = '=' + formula
                raw = cell.findtext('m:v', namespaces=NS)
                kind = cell.get('t')
                if kind == 's':
                    value = shared_strings[int(raw)] if raw is not None else ''
                elif kind == 'inlineStr':
                    value = ''.join(t.text or '' for t in cell.findall('.//m:t', NS))
                elif kind == 'str':
                    value = raw or ''
                elif kind == 'b':
                    value = bool(int(raw))
                elif kind == 'e':
                    if not formula:
                        raise ValueError(f'Input error: {name}!{address}: {raw}')
                    value = None
                else:
                    value = float(raw) if raw is not None else None
                cells[address] = {'formula': formula, 'value': value}
            records[name] = cells
    return records, paths


class Calculator:
    def __init__(self, sheets):
        self.sheets, self.cache, self.active = sheets, {}, set()

    def value(self, sheet, address):
        address = address.replace('$', '')
        key = (sheet, address)
        if key in self.cache:
            return self.cache[key]
        if key in self.active:
            raise ValueError(f'Circular reference: {sheet}!{address}')
        cell = self.sheets[sheet].get(address, {'formula': None, 'value': None})
        if not cell['formula']:
            return cell['value'] if cell['value'] is not None else 0.0
        formula = cell['formula'].lstrip('=')
        formula = formula.replace('_xlfn.PropsSI', 'PropsSI').replace('_xludf.PropsSI', 'PropsSI')
        formula = re.sub(r'MIN\(\s*([$A-Z0-9]+):([$A-Z0-9]+)\s*\)', r'MIN_RANGE("\1","\2")', formula, flags=re.I)
        formula = formula.replace('$', '').replace('^', '**')
        self.active.add(key)
        try:
            value = self.node(sheet, ast.parse(formula, mode='eval').body)
            if not isinstance(value, (float, int)) or not math.isfinite(value):
                raise ValueError(f'Non-finite result: {value}')
            self.cache[key] = float(value)
            return float(value)
        except Exception as error:
            raise ValueError(f'{sheet}!{address}: {error}') from error
        finally:
            self.active.remove(key)

    def node(self, sheet, node):
        if isinstance(node, ast.Constant) and isinstance(node.value, (float, int, str)):
            return node.value
        if isinstance(node, ast.Name) and REF.fullmatch(node.id):
            return self.value(sheet, node.id)
        if isinstance(node, ast.BinOp):
            op = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul,
                  ast.Div: operator.truediv, ast.Pow: operator.pow}.get(type(node.op))
            if op:
                return op(self.node(sheet, node.left), self.node(sheet, node.right))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = self.node(sheet, node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name) and not node.keywords:
            args = [self.node(sheet, arg) for arg in node.args]
            if node.func.id == 'PropsSI' and len(args) == 6:
                return PropsSI(*args)
            if node.func.id == 'MIN_RANGE' and len(args) == 2:
                a, b = (REF.fullmatch(x) for x in args)
                values = [self.value(sheet, f'{column_name(c)}{r}')
                          for c in range(column_number(a[2]), column_number(b[2]) + 1)
                          for r in range(int(a[4]), int(b[4]) + 1)]
                return min(v for v in values if isinstance(v, (int, float)))
        raise ValueError(f'Unsupported formula element: {ast.dump(node)}')

    def calculate(self):
        return {sheet: {address: self.value(sheet, address) for address, cell in cells.items()
                        if cell['formula']} for sheet, cells in self.sheets.items()}


def update_caches(source, destination, values, sheet_paths, formulas=None, remove_refprop=False):
    reverse = {path: sheet for sheet, path in sheet_paths.items()}
    replacements = formulas or {}
    with zipfile.ZipFile(source) as original, zipfile.ZipFile(destination, 'w') as output:
        for info in original.infolist():
            name = info.filename
            if remove_refprop and name.startswith('xl/externalLinks/'):
                continue
            content = original.read(name)
            if name in reverse:
                sheet = reverse[name]
                text = content.decode('utf-8')
                def patch(match):
                    cell = match.group(0)
                    address = re.search(r'\br="([A-Z]+[0-9]+)"', cell)[1]
                    if address not in values[sheet]:
                        return cell
                    opening, rest = cell.split('>', 1)
                    cell = re.sub(r'\s+t="[^"]*"', '', opening, count=1) + '>' + rest
                    if (sheet, address) in replacements:
                        formula = escape(replacements[sheet, address].lstrip('='))
                        cell, count = re.subn(r'(<f\b[^>]*>).*?(</f>)', lambda m: m[1] + formula + m[2], cell, count=1, flags=re.S)
                        if count != 1:
                            raise ValueError(f'Missing formula: {sheet}!{address}')
                    value = f'<v>{values[sheet][address]:.17g}</v>'
                    if re.search(r'<v(?:\s[^>]*)?>.*?</v>|<v\s*/>', cell, re.S):
                        cell = re.sub(r'<v(?:\s[^>]*)?>.*?</v>|<v\s*/>', value, cell, count=1, flags=re.S)
                    else:
                        cell = cell.replace('</c>', value + '</c>')
                    return cell
                content = re.sub(r'<c\b[^>]*(?<!/)>.*?</c>', patch, text, flags=re.S).encode('utf-8')
            elif remove_refprop and name == 'xl/workbook.xml':
                content = re.sub(rb'<externalReferences>.*?</externalReferences>', b'', content, flags=re.S)
            elif remove_refprop and name == 'xl/_rels/workbook.xml.rels':
                content = re.sub(rb'<Relationship\b(?=[^>]*Type="[^"]*/externalLink")[^>]*/>', b'', content)
            elif remove_refprop and name == '[Content_Types].xml':
                content = re.sub(rb'<Override\b(?=[^>]*PartName="/xl/externalLinks/)[^>]*/>', b'', content)
            output.writestr(info, content)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('workbook', type=Path, nargs='?', default=Path(__file__).with_name('系统COP计算_CoolProp.xlsx'))
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    destination = args.output or args.workbook.with_name(args.workbook.stem + '_已重算.xlsx')
    if destination.resolve() == args.workbook.resolve():
        parser.error('请使用不同的输出文件名，保留输入工作簿。')
    records, paths = read_workbook(args.workbook)
    values = Calculator(records).calculate()
    # Stage the output so a property or write error cannot leave a partial file.
    destination.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
        staged = Path(temporary) / 'result.xlsx'
        update_caches(args.workbook, staged, values, paths)
        staged.replace(destination)
    key = values.get('系统COP计算', {})
    print(json.dumps({'output': str(destination.resolve()), 'COP': key.get('E10'),
                      'input_power_MW': key.get('E8'), 'compressor_outlet_C': key.get('E15')}, ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
