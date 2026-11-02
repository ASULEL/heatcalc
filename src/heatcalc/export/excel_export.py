"""按当前方案结果生成公式版 Excel 工作簿。"""

from io import BytesIO
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from openpyxl import Workbook
from openpyxl.styles import Alignment, Border, Font, PatternFill, Side
from openpyxl.utils import get_column_letter

from heatcalc.finance.cash_flow_schedule import calculate_cash_flow_schedule


MONEY_FORMAT = '#,##0.0000'
RATE_FORMAT = '0.00%'
YEAR_FORMAT = '0'

TITLE_FONT = Font(bold=True, size=14)
HEADER_FONT = Font(bold=True, size=10)
NOTE_FONT = Font(size=10)
TITLE_FILL = PatternFill('solid', fgColor='BDD7EE')
HEADER_FILL = PatternFill('solid', fgColor='DDEBF7')
GROUP_FILL = PatternFill('solid', fgColor='F2F2F2')
INPUT_FILL = PatternFill('solid', fgColor='FFF2CC')
THIN = Side(style='thin', color='D9D9D9')
BORDER = Border(left=THIN, right=THIN, top=THIN, bottom=THIN)
CENTER = Alignment(horizontal='center', vertical='center', wrap_text=True)
RIGHT = Alignment(horizontal='right', vertical='center')


def _title(ws, text: str, end_col: int) -> None:
    ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=end_col)
    cell = ws.cell(1, 1, text)
    cell.font = TITLE_FONT
    cell.fill = TITLE_FILL
    cell.alignment = CENTER


def _headers(ws, row: int, labels: list[str], start_col: int = 1) -> None:
    for offset, label in enumerate(labels):
        cell = ws.cell(row, start_col + offset, label)
        cell.font = HEADER_FONT
        cell.fill = HEADER_FILL
        cell.border = BORDER
        cell.alignment = CENTER


def _style_row(ws, row: int, start_col: int, end_col: int) -> None:
    for col in range(start_col, end_col + 1):
        cell = ws.cell(row, col)
        cell.border = BORDER
        if cell.font is None or cell.font.size != HEADER_FONT.size:
            cell.font = NOTE_FONT
        if col > start_col:
            cell.alignment = RIGHT


def _inputs(ws, entries: list[tuple[str, Any, str | None]], label_col: int, value_col: int, start_row: int = 2) -> None:
    for offset, (label, value, fmt) in enumerate(entries):
        row = start_row + offset
        label_cell = ws.cell(row, label_col, label)
        label_cell.font = NOTE_FONT
        value_cell = ws.cell(row, value_col, value)
        value_cell.fill = INPUT_FILL
        value_cell.border = BORDER
        if fmt:
            value_cell.number_format = fmt


def _widths(ws, widths: dict[int, float]) -> None:
    for col, width in widths.items():
        ws.column_dimensions[get_column_letter(col)].width = width


def _loan_sheet(wb: Workbook, loan: dict[str, Any]) -> tuple[Any, int]:
    ws = wb.create_sheet('借款利息计算')
    inputs = loan['inputs']
    rows = loan['schedule']
    total_years = len(rows)
    construction_years = sum(row['phase'] == '建设期' for row in rows)
    first_operating_row = 7 + construction_years + 1

    _title(ws, '熔盐储能项目', 6)
    ws['A2'] = '静态投资'
    ws['B2'] = inputs['static_investment']
    ws['B2'].number_format = MONEY_FORMAT
    ws['D2'] = '动态投资'
    ws['E2'] = f'=B2+SUM(E8:E{7 + construction_years})'
    ws['E2'].number_format = MONEY_FORMAT
    ws['A3'] = '贷款费用'
    ws['B3'] = '=B2*H2'
    ws['B3'].number_format = MONEY_FORMAT
    ws['A4'] = '建设期贷款利率'
    ws['B4'] = inputs['construction_interest_rate']
    ws['B4'].number_format = RATE_FORMAT
    ws['A5'] = '投资贷款利率'
    ws['B5'] = inputs['investment_interest_rate']
    ws['B5'].number_format = RATE_FORMAT

    _inputs(ws, [
        ('贷款比例', inputs['loan_ratio'], RATE_FORMAT),
        ('第1年提款比例', inputs['first_drawdown_ratio'], RATE_FORMAT),
        ('建设期年数', construction_years, YEAR_FORMAT),
        ('还本年数', inputs['repayment_years'], YEAR_FORMAT),
        ('表格总年数', total_years, YEAR_FORMAT),
        ('第二次提款年份', inputs['second_drawdown_year'], YEAR_FORMAT),
    ], 7, 8)

    _headers(ws, 7, ['年份', '年初借款余额', '当年新增借款', '当期还本', '当期利息', '年末借款余额'])
    for year in range(1, total_years + 1):
        row = 7 + year
        ws.cell(row, 1, year).number_format = YEAR_FORMAT
        beginning_balance = 0 if year == 1 else f'=F{row - 1}'
        ws.cell(row, 2, beginning_balance).number_format = MONEY_FORMAT
        if year == 1:
            new_borrowing = '=B3*H3'
        elif year == inputs['second_drawdown_year']:
            new_borrowing = '=B3*(1-H3)'
        else:
            new_borrowing = 0
        ws.cell(row, 3, new_borrowing).number_format = MONEY_FORMAT

        if year <= construction_years:
            interest = f'=(B{row}+C{row}/2)*$B$4'
        else:
            interest = f'=(B{row}+C{row})*$B$5'
        ws.cell(row, 5, interest).number_format = MONEY_FORMAT

        if year <= construction_years:
            principal = 0
        else:
            principal = (
                f'=IF(AND(A{row}>$H$4,A{row}<=$H$4+$H$5),'
                f'($F${7 + construction_years}+C{first_operating_row})/$H$5,0)'
            )
        ws.cell(row, 4, principal).number_format = MONEY_FORMAT

        if year <= construction_years:
            balance = f'=B{row}+C{row}+E{row}'
        else:
            balance = f'=MAX(0,B{row}+C{row}-D{row})'
        ws.cell(row, 6, balance).number_format = MONEY_FORMAT
        _style_row(ws, row, 1, 6)

    _widths(ws, {1: 8, 2: 18, 3: 16, 4: 16, 5: 16, 6: 18, 7: 22, 8: 12})
    ws.freeze_panes = 'A8'
    return ws, construction_years


def _cost_sheet(wb: Workbook, cost: dict[str, Any], construction_years: int) -> tuple[Any, int]:
    ws = wb.create_sheet('成本计算')
    inputs = cost['inputs']
    rows = cost['schedule']
    total_years = len(rows)
    operating_years = inputs['operating_years']
    last_operating_year = construction_years + operating_years
    table_end = 4 + total_years

    _title(ws, '熔盐储能项目', 12)
    ws.merge_cells('C3:G3')
    ws['C3'] = '经营成本'
    ws.merge_cells('H3:I3')
    ws['H3'] = '折旧摊销'
    ws.merge_cells('J3:K3')
    ws['J3'] = '财务成本'
    for cell in ('C3', 'H3', 'J3'):
        ws[cell].font = HEADER_FONT
        ws[cell].fill = GROUP_FILL
        ws[cell].alignment = CENTER
        ws[cell].border = BORDER

    _inputs(ws, [
        ('静态投资', "='借款利息计算'!B2", MONEY_FORMAT),
        ('建设期抵扣比例', inputs['construction_credit_ratio'], RATE_FORMAT),
        ('可折旧比例', inputs['depreciable_ratio'], RATE_FORMAT),
        ('保险费率', inputs['insurance_rate'], RATE_FORMAT),
        ('保险费除税系数', inputs['insurance_divisor'], '0.0000'),
        ('含税换算系数', inputs['tax_divisor'], '0.0000'),
        ('折旧年限', inputs['depreciation_years'], YEAR_FORMAT),
        ('运营年数', operating_years, YEAR_FORMAT),
        ('建设期利息合计', f"=SUM('借款利息计算'!E8:E{7 + construction_years})", MONEY_FORMAT),
        ('计价基数', '=O1*O3-O1*O2+O9', MONEY_FORMAT),
        ('建设期年数', construction_years, YEAR_FORMAT),
        ('最后运营年', last_operating_year, YEAR_FORMAT),
    ], 14, 15, start_row=1)

    _headers(ws, 4, [
        '年份', '维修费比例', '电费', '水费', '人工费', '保险费', '维修费',
        '折旧费', '摊销费', '长期借款利息', '流动资金借款利息', '总成本',
    ])
    ws.cell(4, 13, '含税电费输入').font = HEADER_FONT
    ws.cell(4, 13).fill = INPUT_FILL
    ws.cell(4, 13).border = BORDER
    ws.cell(4, 13).alignment = CENTER

    active = 'AND($A{row}>$O$11,$A{row}<=$O$12)'
    for year in range(1, total_years + 1):
        row = 4 + year
        ws.cell(row, 1, year).number_format = YEAR_FORMAT
        ratio = next((
            period['ratio'] for period in inputs['maintenance_ratio_periods']
            if period['start_year'] <= year <= period['end_year']
        ), 0.0)
        ws.cell(row, 2, ratio).number_format = '0.000000'
        ws.cell(row, 3, f'=IF({active.format(row=row)},M{row}/$O$6,0)').number_format = MONEY_FORMAT
        ws.cell(row, 4, inputs['water_cost_by_year'][year - 1]).number_format = MONEY_FORMAT
        ws.cell(row, 5, inputs['labor_cost_by_year'][year - 1]).number_format = MONEY_FORMAT
        ws.cell(row, 6, f'=IF({active.format(row=row)},$O$10*$O$4/$O$5,0)').number_format = MONEY_FORMAT
        ws.cell(row, 7, f'=IF({active.format(row=row)},$O$10*B{row}/$O$6,0)').number_format = MONEY_FORMAT
        ws.cell(row, 8, (
            f'=IF(AND({active.format(row=row)},$A{row}<=$O$11+$O$7),'
            f'$O$10*$O$3/$O$7,0)'
        )).number_format = MONEY_FORMAT
        ws.cell(row, 9, inputs['amortization_expense_by_year'][year - 1]).number_format = MONEY_FORMAT
        ws.cell(row, 10, (
            f"=IF({active.format(row=row)},'借款利息计算'!E{7 + year},0)"
        )).number_format = MONEY_FORMAT
        ws.cell(row, 11, inputs['working_capital_loan_interest_by_year'][year - 1]).number_format = MONEY_FORMAT
        ws.cell(row, 12, f'=SUM(C{row}:K{row})').number_format = MONEY_FORMAT
        ws.cell(row, 13, inputs['total_electricity_by_year'][year - 1]).number_format = MONEY_FORMAT
        _style_row(ws, row, 1, 12)

    depreciation_total_row = table_end + 2
    residual_row = table_end + 3
    ws.cell(depreciation_total_row, 7, '累计折旧').font = HEADER_FONT
    ws.cell(depreciation_total_row, 8, f'=SUM(H5:H{table_end})').number_format = MONEY_FORMAT
    ws.cell(residual_row, 7, '回收固定资产余值').font = HEADER_FONT
    ws.cell(residual_row, 8, (
        f'=$O$10-SUM(H5:INDEX(H5:H{table_end},\'收入及税金\'!$O$11))'
    )).number_format = MONEY_FORMAT

    _widths(ws, {1: 8, 2: 12, 3: 14, 4: 11, 5: 11, 6: 11, 7: 11, 8: 14, 9: 11, 10: 14, 11: 18, 12: 16, 13: 16, 14: 20, 15: 14})
    ws.freeze_panes = 'C5'
    return ws, residual_row


def _revenue_sheet(wb: Workbook, revenue: dict[str, Any], construction_years: int) -> Any:
    ws = wb.create_sheet('收入及税金')
    inputs = revenue['inputs']
    rows = revenue['schedule']
    total_years = len(rows)
    last_operating_year = construction_years + inputs['operating_years']
    table_end = 4 + total_years

    _title(ws, '熔盐储能项目', 9)
    ws.merge_cells('D3:I3')
    ws['D3'] = '税款'
    ws['D3'].font = HEADER_FONT
    ws['D3'].fill = GROUP_FILL
    ws['D3'].alignment = CENTER
    ws['D3'].border = BORDER

    _inputs(ws, [
        ('蒸汽除税率', inputs['steam_vat_rate'], RATE_FORMAT),
        ('碳收益除税率', inputs['carbon_vat_rate'], RATE_FORMAT),
        ('销项税率', inputs['output_vat_rate'], RATE_FORMAT),
        ('购电进项税率', inputs['input_vat_rate'], RATE_FORMAT),
        ('建设期抵扣比例', inputs['construction_credit_ratio'], RATE_FORMAT),
        ('附加税系数', inputs['surcharge_rate'], RATE_FORMAT),
        ('收入口径（1含税，0不含税）', 1 if inputs['income_amount_basis'] == 'tax_inclusive' else 0, YEAR_FORMAT),
        ('静态投资', "='借款利息计算'!B2", MONEY_FORMAT),
        ('初始抵扣额度', '=O8*O5', MONEY_FORMAT),
        ('建设期年数', construction_years, YEAR_FORMAT),
        ('最后运营年', last_operating_year, YEAR_FORMAT),
    ], 14, 15, start_row=1)

    _headers(ws, 4, ['年份', '蒸汽量', '蒸汽收益', '销项税', '进项税', '应缴增值税', '建设期可抵扣增值税', '实缴增值税', '城建及教育附加'])
    for col, label in ((10, '蒸汽收入输入'), (11, '碳收益输入')):
        cell = ws.cell(4, col, label)
        cell.font = HEADER_FONT
        cell.fill = INPUT_FILL
        cell.border = BORDER
        cell.alignment = CENTER

    for year in range(1, total_years + 1):
        row = 4 + year
        ws.cell(row, 1, year).number_format = YEAR_FORMAT
        steam_volume = inputs['steam_volume_by_year'][year - 1]
        ws.cell(row, 2, steam_volume if steam_volume is not None else '—')
        ws.cell(row, 10, inputs['steam_revenue_by_year'][year - 1]).number_format = MONEY_FORMAT
        ws.cell(row, 11, inputs['carbon_revenue_by_year'][year - 1]).number_format = MONEY_FORMAT
        active = f'AND($A{row}>$O$10,$A{row}<=$O$11)'
        ws.cell(row, 3, (
            f'=IF({active},IF($O$7=1,J{row}/(1+$O$1)+K{row}/(1+$O$2),J{row}+K{row}),0)'
        )).number_format = MONEY_FORMAT
        ws.cell(row, 4, f'=C{row}*$O$3').number_format = MONEY_FORMAT
        ws.cell(row, 5, f'=成本计算!C{row}*$O$4').number_format = MONEY_FORMAT
        ws.cell(row, 6, f'=MAX(D{row}-E{row},0)').number_format = MONEY_FORMAT
        if row == 5:
            credit = '=MIN(F5,$O$9)'
        else:
            credit = f'=MIN(F{row},MAX($O$9-SUM($G$5:G{row - 1}),0))'
        ws.cell(row, 7, credit).number_format = MONEY_FORMAT
        ws.cell(row, 8, f'=F{row}-G{row}').number_format = MONEY_FORMAT
        ws.cell(row, 9, f'=H{row}*$O$6').number_format = MONEY_FORMAT
        _style_row(ws, row, 1, 9)
        ws.cell(row, 10).fill = INPUT_FILL
        ws.cell(row, 11).fill = INPUT_FILL

    _widths(ws, {1: 8, 2: 10, 3: 16, 4: 14, 5: 14, 6: 16, 7: 20, 8: 14, 9: 16, 10: 16, 11: 16, 14: 24, 15: 14})
    ws.freeze_panes = 'C5'
    return ws


def _income_tax_sheet(wb: Workbook, income: dict[str, Any]) -> Any:
    ws = wb.create_sheet('所得税计算')
    inputs = income['inputs']
    rows = income['schedule']
    total_years = len(rows)
    table_end = 4 + total_years

    _title(ws, '熔盐储能项目', 11)
    _inputs(ws, [('所得税率', inputs['income_tax_rate'], RATE_FORMAT)], 14, 15, start_row=1)
    _headers(ws, 4, [
        '年份', '营业收入', '附加税', '总成本', '利润总额', '本年亏损',
        '本年累计亏损', '弥补亏损', '应纳税所得额', '所得税', '净利润',
    ])

    for year in range(1, total_years + 1):
        row = 4 + year
        ws.cell(row, 1, year).number_format = YEAR_FORMAT
        ws.cell(row, 2, f'=收入及税金!C{row}').number_format = MONEY_FORMAT
        ws.cell(row, 3, f'=收入及税金!I{row}').number_format = MONEY_FORMAT
        ws.cell(row, 4, f'=成本计算!L{row}').number_format = MONEY_FORMAT
        ws.cell(row, 5, f'=B{row}-C{row}-D{row}').number_format = MONEY_FORMAT
        ws.cell(row, 6, f'=MIN(E{row},0)').number_format = MONEY_FORMAT
        if row == 5:
            ws.cell(row, 8, 0).number_format = MONEY_FORMAT
            ws.cell(row, 7, f'=MAX(-E{row},0)').number_format = MONEY_FORMAT
        else:
            ws.cell(row, 8, f'=MIN(MAX(E{row},0),G{row - 1})').number_format = MONEY_FORMAT
            ws.cell(row, 7, f'=MAX(G{row - 1}+MAX(-E{row},0)-H{row},0)').number_format = MONEY_FORMAT
        ws.cell(row, 9, f'=MAX(E{row},0)-H{row}').number_format = MONEY_FORMAT
        ws.cell(row, 10, f'=I{row}*$O$1').number_format = MONEY_FORMAT
        ws.cell(row, 11, f'=E{row}-J{row}').number_format = MONEY_FORMAT
        _style_row(ws, row, 1, 11)

    total_row = table_end + 1
    ws.cell(total_row, 1, '合计').font = HEADER_FONT
    ws.cell(total_row, 10, f'=SUM(J5:J{table_end})').number_format = MONEY_FORMAT
    ws.cell(total_row, 11, f'=SUM(K5:K{table_end})').number_format = MONEY_FORMAT

    _widths(ws, {1: 8, 2: 14, 3: 12, 4: 14, 5: 14, 6: 12, 7: 14, 8: 12, 9: 16, 10: 14, 11: 14, 14: 16, 15: 12})
    ws.freeze_panes = 'B5'
    return ws


def _cash_flow_sheet(
    wb: Workbook, title: str, cash: dict[str, Any], capital: bool,
    equity_ratio: float, construction_years: int, residual_row: int,
) -> Any:
    ws = wb.create_sheet(title)
    rows = cash['schedule']
    total_years = len(rows)
    table_end = 4 + total_years

    _title(ws, title, 14)
    _inputs(ws, [
        ('资本金比例', equity_ratio, RATE_FORMAT),
        ('第1年投入比例', "='借款利息计算'!H3", RATE_FORMAT),
        ('第二次投入年份', "='借款利息计算'!H7", YEAR_FORMAT),
        ('建设期年数', construction_years, YEAR_FORMAT),
        ('最后运营年', "='收入及税金'!O11", YEAR_FORMAT),
        ('回收固定资产余值', f'=成本计算!H{residual_row}', MONEY_FORMAT),
    ], 15, 16, start_row=1)

    _headers(ws, 4, [
        '年份', '营业收入', '回收固定资产余值', '现金流入合计', '建设期现金流出',
        '借款本金偿还', '借款利息', '经营成本', '附加税', '所得税',
        '净现金流量', '累计净现金流量', '预计静态投资回收期（年）', '实际静态投资回收期（年）',
    ])

    for year in range(1, total_years + 1):
        row = 4 + year
        ws.cell(row, 1, year).number_format = YEAR_FORMAT
        ws.cell(row, 2, f'=所得税计算!B{row}').number_format = MONEY_FORMAT
        ws.cell(row, 3, f'=IF(A{row}=$P$5,$P$6,0)').number_format = MONEY_FORMAT
        ws.cell(row, 4, f'=B{row}+C{row}').number_format = MONEY_FORMAT
        ws.cell(row, 5, (
            f'=IF(A{row}=1,\'借款利息计算\'!$B$2*$P$1*$P$2,'
            f'IF(A{row}=$P$3,\'借款利息计算\'!$B$2*$P$1*(1-$P$2),0))'
        )).number_format = MONEY_FORMAT
        if capital:
            ws.cell(row, 6, f"='借款利息计算'!D{7 + year}").number_format = MONEY_FORMAT
            ws.cell(row, 7, f'=成本计算!J{row}+成本计算!K{row}').number_format = MONEY_FORMAT
        else:
            ws.cell(row, 6, 0).number_format = MONEY_FORMAT
            ws.cell(row, 7, 0).number_format = MONEY_FORMAT
        ws.cell(row, 8, f'=SUM(成本计算!C{row}:G{row})').number_format = MONEY_FORMAT
        ws.cell(row, 9, f'=收入及税金!I{row}').number_format = MONEY_FORMAT
        ws.cell(row, 10, f'=所得税计算!J{row}').number_format = MONEY_FORMAT
        ws.cell(row, 11, f'=D{row}-SUM(E{row}:J{row})').number_format = MONEY_FORMAT
        if row == 5:
            ws.cell(row, 12, f'=K{row}').number_format = MONEY_FORMAT
            ws.cell(row, 13, '')
            ws.cell(row, 14, '')
        else:
            ws.cell(row, 12, f'=L{row - 1}+K{row}').number_format = MONEY_FORMAT
            ws.cell(row, 13, (
                f'=IF(AND(A{row}>$P$4,K{row}>0,COUNT($N$5:N{row - 1})=0),'
                f'A{row}-$P$4-L{row}/K{row},"")'
            )).number_format = '0.00'
            ws.cell(row, 14, (
                f'=IF(AND(A{row}>$P$4,L{row}>=0,L{row - 1}<0,K{row}>0,'
                f'COUNT($N$5:N{row - 1})=0),M{row},"")'
            )).number_format = '0.00'
        # 年份保留；结束后的金额、累计值和回收期均为空。
        for col in range(2, 15):
            cell = ws.cell(row, col)
            expression = cell.value
            if expression == '':
                continue
            expression = expression[1:] if isinstance(expression, str) else str(expression)
            cell.value = f'=IF(A{row}>$P$5,"",{expression})'
        _style_row(ws, row, 1, 14)

    irr_row = table_end + 2
    payback_row = table_end + 3
    net_row = table_end + 4
    ws.cell(irr_row, 1, '内部收益率（IRR）').font = HEADER_FONT
    active_cash_flows = f'K5:INDEX(K5:K{table_end},$P$5)'
    ws.cell(irr_row, 2, f'=IFERROR(IRR({active_cash_flows}),"")').number_format = RATE_FORMAT
    ws.cell(payback_row, 1, '静态投资回收期（年）').font = HEADER_FONT
    ws.cell(payback_row, 2, (
        f'=IF(COUNT(N5:N{table_end})=0,"运营期内未回收",MAX(N5:N{table_end}))'
    )).number_format = '0.00'
    ws.cell(net_row, 1, '净现金流量合计').font = HEADER_FONT
    ws.cell(net_row, 2, f'=SUM({active_cash_flows})').number_format = MONEY_FORMAT

    _widths(ws, {1: 8, 2: 14, 3: 16, 4: 16, 5: 16, 6: 14, 7: 12, 8: 14, 9: 12, 10: 12, 11: 16, 12: 18, 13: 20, 14: 20, 15: 20, 16: 16})
    ws.freeze_panes = 'B5'
    return ws


def _formula_values(loan: dict, cost: dict, revenue: dict, income: dict, cash: dict) -> list[dict]:
    """为导出公式提供本次计算值，使表格预览无需先执行重算。"""
    loan_values = {'B3': loan['summary']['loan_amount'], 'E2': loan['summary']['total_investment_with_interest']}
    for row in loan['schedule']:
        for col, key in [('B', 'beginning_balance'), ('C', 'new_borrowing'), ('D', 'principal_repayment'), ('E', 'interest_expense'), ('F', 'ending_balance')]:
            loan_values[f'{col}{row["year"] + 7}'] = row[key]

    end_year = max(row['year'] for row in revenue['schedule'] if row['phase'] == '运营期')
    total_years = len(loan['schedule'])
    cost_values = {
        'O1': loan['summary']['static_investment'], 'O9': cost['summary']['construction_interest'],
        'O10': cost['summary']['cost_base'],
        f'H{total_years + 6}': sum(row['depreciation_cost'] for row in cost['schedule']),
        f'H{total_years + 7}': cash['capital']['summary']['residual_value'],
    }
    for row in cost['schedule']:
        for col, key in [('C', 'electricity_cost'), ('F', 'insurance_cost'), ('G', 'maintenance_cost'), ('H', 'depreciation_cost'), ('J', 'long_term_loan_interest'), ('L', 'total_cost')]:
            cost_values[f'{col}{row["year"] + 4}'] = row[key]

    revenue_values = {'O8': loan['summary']['static_investment'], 'O9': revenue['summary']['initial_construction_credit']}
    for row in revenue['schedule']:
        for col, key in [('C', 'revenue_excluding_tax'), ('D', 'output_vat'), ('E', 'input_vat'), ('F', 'vat_before_credit'), ('G', 'construction_credit_used'), ('H', 'vat_paid'), ('I', 'surcharge')]:
            revenue_values[f'{col}{row["year"] + 4}'] = row[key]

    income_values = {}
    income_fields = [
        'revenue', 'surcharge', 'total_cost', 'total_profit', 'current_year_loss',
        'carryforward_loss', 'loss_offset', 'taxable_income', 'income_tax', 'net_profit',
    ]
    for row in income['schedule']:
        for col, key in enumerate(income_fields, start=2):
            income_values[f'{get_column_letter(col)}{row["year"] + 4}'] = row[key]
    income_values[f'J{total_years + 5}'] = income['summary']['income_tax_total']
    income_values[f'K{total_years + 5}'] = income['summary']['net_profit_total']

    cash_values = []
    cash_fields = [
        'revenue', 'residual_value', 'inflow', 'construction_investment', 'principal_repayment',
        'interest', 'operating_cost', 'surcharge', 'income_tax', 'net_cash_flow',
        'cumulative_cash_flow', 'estimated_payback_period', 'payback_period',
    ]
    for table in [cash['capital'], cash['total_investment']]:
        values = {
            'P2': loan['inputs']['first_drawdown_ratio'], 'P3': loan['inputs']['second_drawdown_year'],
            'P5': end_year, 'P6': table['summary']['residual_value'],
            f'B{total_years + 6}': table['summary']['irr'],
            f'B{total_years + 7}': table['summary']['static_payback_period'] if table['summary']['static_payback_period'] is not None else '运营期内未回收',
            f'B{total_years + 8}': table['summary']['net_cash_flow_total'],
        }
        for row in table['schedule']:
            for col, key in enumerate(cash_fields, start=2):
                values[f'{get_column_letter(col)}{row["year"] + 4}'] = row[key]
        cash_values.append(values)
    return [loan_values, cost_values, revenue_values, income_values, *cash_values]


def _cache_formulas(content: bytes, sheet_values: list[dict]) -> bytes:
    """保留 openpyxl 生成的公式，补充标准 OOXML 的公式结果缓存。"""
    namespace = 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'
    ET.register_namespace('', namespace)
    replacements = {}
    with ZipFile(BytesIO(content)) as source:
        for index, values in enumerate(sheet_values, start=1):
            name = f'xl/worksheets/sheet{index}.xml'
            root = ET.fromstring(source.read(name))
            for cell in root.iter(f'{{{namespace}}}c'):
                if cell.find(f'{{{namespace}}}f') is None:
                    continue
                value = values[cell.attrib['r']]
                cached = cell.find(f'{{{namespace}}}v')
                cell.set('t', 'str' if value is None or isinstance(value, str) else 'n')
                cached.text = '' if value is None else str(value)
            replacements[name] = ET.tostring(root, encoding='utf-8')
        buffer = BytesIO()
        with ZipFile(buffer, 'w') as target:
            for entry in source.infolist():
                target.writestr(entry, replacements.get(entry.filename, source.read(entry.filename)))
    return buffer.getvalue()


def _notes_sheet(wb: Workbook, scheme_name: str, exported_at: str, results: dict[str, Any]) -> Any:
    ws = wb.create_sheet('测算说明')
    ws.column_dimensions['A'].width = 24
    ws.column_dimensions['B'].width = 110
    _title(ws, '经济测算说明', 2)

    lines = [
        ('方案名称', scheme_name),
        ('导出时间', exported_at),
        ('工作表', '借款利息计算、成本计算、收入及税金、所得税计算、资本金现金流量表、全投资现金流量表。'),
        ('数据来源', '所有表由当前网页方案的分步结果生成；黄色单元格为可修改输入。'),
        ('公式版本', '工作簿同时保存公式和本次计算值，打开可直接查看；修改输入单元格后自动重算。'),
        ('借款表', '静态投资 × 贷款比例得到贷款费用；建设期利息资本化，运营期按等额本金还本。'),
        ('成本表', '计价基数 = 静态投资 × 可折旧比例 − 静态投资 × 建设期抵扣比例 + 建设期利息合计。'
                 '电费、维修费按含税换算系数除税；保险费再按保险费除税系数换算；折旧费按计价基数 × 可折旧比例 ÷ 折旧年限。'),
        ('收入及税金', '含税收入按各自除税率换算后相加；销项税对合计不含税收入计税；购电进项税引用同年成本表不含税电费。'
                     '建设期抵扣按年初剩余额度递推，附加税以实缴增值税为基数。'),
        ('所得税', '利润总额 = 营业收入 − 附加税 − 总成本；亏损年度不缴税，亏损结转到以后年度，盈利时先弥补再计税。'
                 '当前不设亏损结转年限。'),
        ('现金流量表', '两张表同一套公式。资本金表投入静态投资 × 资本金比例，并偿还本金和利息；'
                     '全投资表投入静态投资的100%，没有借款本金和利息。分年投入引用借款参数，运营结束后只保留年份。'),
        ('回收固定资产余值', '计价基数 − 截至项目结束的累计折旧，假设期末剩余账面价值可回收；只在最后一个运营年计入一次。'),
        ('预计静态投资回收期', '项目年份 − 建设期年数 − 累计净现金流量 ÷ 当年净现金流量。仅在运营期且当年净现金流为正时估算，首次回本后停止列示。'),
        ('静态投资回收期', '累计净现金流量第一次由负转正时确认，按“已过年数 + 上年累计绝对值 ÷ 当年净现金流量”计算，自运营期起算。未回本显示“运营期内未回收”。'),
        ('与原 Excel 的差异', '购电进项税改为同年引用；建设期抵扣按余额递推；所得税按标准亏损弥补；'
                          '现金流量表增加回收余值单列，不输出原表最右侧的辅助累计列。'),
    ]
    for index, (label, text) in enumerate(lines, start=2):
        label_cell = ws.cell(index, 1, label)
        label_cell.font = HEADER_FONT
        label_cell.alignment = Alignment(vertical='top', wrap_text=True)
        value_cell = ws.cell(index, 2, text)
        value_cell.font = NOTE_FONT
        value_cell.alignment = Alignment(vertical='top', wrap_text=True)

    summary_row = len(lines) + 4
    ws.cell(summary_row, 1, '关键结果').font = TITLE_FONT
    ws.cell(summary_row + 1, 1, '资本金 IRR')
    ws.cell(summary_row + 1, 2, results['cash_flow_result']['capital']['summary']['irr']).number_format = RATE_FORMAT
    ws.cell(summary_row + 2, 1, '全投资 IRR')
    ws.cell(summary_row + 2, 2, results['cash_flow_result']['total_investment']['summary']['irr']).number_format = RATE_FORMAT
    ws.cell(summary_row + 3, 1, '资本金回收期')
    ws.cell(summary_row + 3, 2, results['cash_flow_result']['capital']['summary']['static_payback_period']).number_format = '0.00'
    ws.cell(summary_row + 4, 1, '全投资回收期')
    ws.cell(summary_row + 4, 2, results['cash_flow_result']['total_investment']['summary']['static_payback_period']).number_format = '0.00'
    return ws


def build_scheme_workbook(
    scheme_name: str,
    loan_result: dict[str, Any],
    cost_result: dict[str, Any],
    revenue_tax_result: dict[str, Any],
    income_tax_result: dict[str, Any],
    cash_flow_result: dict[str, Any],
    exported_at: str,
) -> bytes:
    """按六张财务表生成公式版工作簿，返回 xlsx 字节。"""
    wb = Workbook()
    wb.remove(wb.active)
    cash_flow_result = {
        'inputs': cash_flow_result['inputs'],
        **calculate_cash_flow_schedule(
            loan_result, cost_result, revenue_tax_result, income_tax_result,
            cash_flow_result['inputs']['equity_ratio'],
        ),
    }

    _, construction_years = _loan_sheet(wb, loan_result)
    _, residual_row = _cost_sheet(wb, cost_result, construction_years)
    _revenue_sheet(wb, revenue_tax_result, construction_years)
    _income_tax_sheet(wb, income_tax_result)
    capital = cash_flow_result['capital']
    total = cash_flow_result['total_investment']
    _cash_flow_sheet(
        wb, '资本金现金流量表', capital, True,
        cash_flow_result['inputs']['equity_ratio'], construction_years, residual_row,
    )
    _cash_flow_sheet(
        wb, '全投资现金流量表', total, False,
        1.0, construction_years, residual_row,
    )
    _notes_sheet(wb, scheme_name, exported_at, {
        'cash_flow_result': cash_flow_result,
    })

    wb.calculation.calcMode = 'auto'
    wb.calculation.fullCalcOnLoad = False
    wb.calculation.forceFullCalc = False
    buffer = BytesIO()
    wb.save(buffer)
    return _cache_formulas(buffer.getvalue(), _formula_values(
        loan_result, cost_result, revenue_tax_result, income_tax_result, cash_flow_result,
    ))
