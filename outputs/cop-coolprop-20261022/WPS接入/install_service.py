"""Install the loopback CoolProp bridge as the current user's login service."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
PROJECT = ROOT.parents[2]
LABEL = 'com.heatcalc.coolprop-wps'
PLIST = Path.home() / 'Library/LaunchAgents' / f'{LABEL}.plist'
TARGET = f'gui/{os.getuid()}'


def main():
    payload = {
        'Label': LABEL,
        'ProgramArguments': [str(PROJECT / '.venv/bin/python'), str(ROOT / 'coolprop_bridge.py')],
        'WorkingDirectory': str(PROJECT),
        'RunAtLoad': True,
        'KeepAlive': {'SuccessfulExit': False},
        'ThrottleInterval': 10,
        'ProcessType': 'Background',
        'StandardOutPath': str(ROOT / 'service.log'),
        'StandardErrorPath': str(ROOT / 'service-error.log'),
    }
    PLIST.parent.mkdir(parents=True, exist_ok=True)
    if PLIST.exists():
        if plistlib.loads(PLIST.read_bytes()) != payload:
            raise SystemExit(f'已有不同的服务配置，请先核对：{PLIST}')
    else:
        PLIST.write_bytes(plistlib.dumps(payload))
        PLIST.chmod(0o644)
    active = subprocess.run(['/bin/launchctl', 'print', f'{TARGET}/{LABEL}'], capture_output=True)
    if active.returncode:
        subprocess.run(['/bin/launchctl', 'bootstrap', TARGET, str(PLIST)], check=True)
    else:
        subprocess.run(['/bin/launchctl', 'kickstart', f'{TARGET}/{LABEL}'], check=True)
    for _ in range(30):
        try:
            health = json.load(urllib.request.urlopen('http://127.0.0.1:18764/health', timeout=2))
            assert health['ok'] is True and health['version'] == '8.0.0'
            print(json.dumps({'service': LABEL, 'plist': str(PLIST), 'health': health}, ensure_ascii=False))
            return
        except (OSError, ValueError):
            time.sleep(0.2)
    raise SystemExit('服务未启动，请检查 service-error.log')


if __name__ == '__main__':
    main()
