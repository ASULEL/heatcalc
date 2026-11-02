"""Local, computation-only CoolProp endpoint for WPS JavaScript functions."""
from __future__ import annotations

import argparse
from functools import lru_cache
from http.server import BaseHTTPRequestHandler, HTTPServer
import json
import math
from pathlib import Path
import secrets
from urllib.parse import urlsplit

import CoolProp
from CoolProp.CoolProp import PropsSI

ROOT = Path(__file__).resolve().parent


def load_config(path: Path) -> dict:
    config = json.loads(path.read_text())
    if config['host'] != '127.0.0.1':
        raise ValueError('Only the loopback interface is supported')
    if not isinstance(config['token'], str) or len(config['token']) < 32:
        raise ValueError('Invalid local connection token')
    return config


@lru_cache(maxsize=8192)
def calculate(output, name1, value1, name2, value2, fluid):
    value = float(PropsSI(output, name1, value1, name2, value2, fluid))
    if not math.isfinite(value) or abs(value) > 1e30:
        raise ValueError('CoolProp returned an invalid property value')
    return value


class Handler(BaseHTTPRequestHandler):
    server_version = 'LocalCoolProp/1'

    def log_message(self, format, *args):
        # Property calls do not need per-cell logs or stored workbook inputs.
        pass

    def reply(self, status, payload):
        data = json.dumps(payload, ensure_ascii=True, allow_nan=False).encode()
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(data)))
        self.send_header('Cache-Control', 'no-store')
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self):
        if urlsplit(self.path).path != '/props':
            self.reply(404, {'ok': False, 'error': 'Unknown endpoint'})
            return
        try:
            size = int(self.headers.get('Content-Length', '0'))
            if not 0 < size <= 4096:
                raise ValueError('Request must contain at most 4096 bytes')
            request = json.loads(self.rfile.read(size))
            if not isinstance(request, dict):
                raise ValueError('Request must be a JSON object')
            token = request.get('token', '')
            if not isinstance(token, str) or not secrets.compare_digest(token, self.server.config['token']):
                self.reply(403, {'ok': False, 'error': 'Invalid local connection token'})
                return
            args = request.get('args')
            if not isinstance(args, list) or len(args) != 6:
                raise ValueError('PropsSI expects six arguments')
            for index in (0, 1, 3, 5):
                if not isinstance(args[index], str) or not 0 < len(args[index]) <= 256:
                    raise ValueError('Invalid property name or fluid')
            for index in (2, 4):
                if isinstance(args[index], bool) or not isinstance(args[index], (int, float)) or not math.isfinite(args[index]):
                    raise ValueError('State inputs must be finite numbers')
            self.reply(200, {'ok': True, 'value': calculate(*args), 'version': CoolProp.__version__})
        except (ValueError, TypeError, KeyError, OverflowError) as exc:
            self.reply(400, {'ok': False, 'error': str(exc)[:1000]})

    def do_GET(self):
        if self.path == '/health':
            self.reply(200, {'ok': True, 'version': CoolProp.__version__})
        else:
            self.reply(404, {'ok': False, 'error': 'Unknown endpoint'})


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', type=Path, default=ROOT / 'connection.json')
    options = parser.parse_args()
    config = load_config(options.config)
    server = HTTPServer((config['host'], config['port']), Handler)
    server.config = config
    print(f'CoolProp {CoolProp.__version__} ready on {config["host"]}:{config["port"]}', flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == '__main__':
    main()
