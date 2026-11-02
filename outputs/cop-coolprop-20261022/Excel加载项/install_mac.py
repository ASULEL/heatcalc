"""Install this machine's CoolProp files in the official Mac Excel location."""
from datetime import datetime
import ctypes
import hashlib
import json
import math
from pathlib import Path
import platform
import shutil


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    source = Path(__file__).resolve().parent
    expected_home = Path('/Users/asule')
    if Path.home() != expected_home or platform.machine() != 'arm64':
        raise SystemExit('此加载项已配置为 /Users/asule 的 Mac arm64 版本，请勿直接用于其他用户或架构。')
    target = expected_home / 'Library/Group Containers/UBF8T346G9.Office'
    target.mkdir(parents=True, exist_ok=True)
    installed = []
    for src in [source / 'CoolProp.xlam', source / 'Mac/libCoolProp.dylib']:
        dest = target / src.name
        if dest.exists() and digest(dest) != digest(src):
            backup = dest.with_name(dest.name + '.backup-' + datetime.now().strftime('%Y%m%d-%H%M%S-%f'))
            shutil.copy2(dest, backup)
            print('已备份：', backup)
        if not dest.exists() or digest(dest) != digest(src):
            shutil.copy2(src, dest)
        assert digest(dest) == digest(src)
        installed.append({'path': str(dest), 'sha256': digest(dest)})
    lib = ctypes.CDLL(str(target / 'libCoolProp.dylib'))
    props = lib.PropsSI
    props.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_double,
                      ctypes.c_char_p, ctypes.c_double, ctypes.c_char_p]
    props.restype = ctypes.c_double
    boiling_k = props(b'T', b'P', 101325, b'Q', 0, b'Water')
    assert math.isclose(boiling_k, 373.1242958476663, rel_tol=1e-12)
    result = {'installed': installed, 'native_test_water_boiling_K': boiling_k,
              'excel_addin_enabled': False, 'excel_recalculation_verified': False}
    (source / 'installation-status.json').write_text(json.dumps(result, ensure_ascii=False, indent=2))
    print(json.dumps(result, ensure_ascii=False, indent=2))
    print('文件已安装。还需在 Microsoft Excel 的“工具 → Excel 加载项”中勾选 CoolProp.xlam。')


if __name__ == '__main__':
    main()
