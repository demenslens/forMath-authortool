"""
Integratie-test: bevestigt dat parse-fouten via /api/process als
FriendlyError in het JSON-response terecht komen.

Draait de HTTP handler in-process (zoals smoke_test.py) en controleert
voor elk slecht invoergeval dat `error_detail` aanwezig is met de
verwachte velden (message, hint, snippet, position, raw).
"""
import os
import sys
import json
import socket
import threading
import time
import tempfile
from http.server import HTTPServer
from http.client import HTTPConnection

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'formath_web'))
sys.path.insert(0, os.path.join(ROOT, 'python_bestanden'))

from server import ForMathHandler
import json_exporter
json_exporter.OUTPUT_DIR = tempfile.mkdtemp(prefix='formath_err_')

# Pak vrije poort
s = socket.socket(); s.bind(('127.0.0.1', 0)); free_port = s.getsockname()[1]; s.close()
server = HTTPServer(('127.0.0.1', free_port), ForMathHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
time.sleep(0.3)


def post(path, body):
    conn = HTTPConnection('127.0.0.1', free_port, timeout=5)
    conn.request('POST', path, body=json.dumps(body),
                 headers={'Content-Type': 'application/json'})
    resp = conn.getresponse()
    data = json.loads(resp.read())
    conn.close()
    return data


ok = 0
fail = 0

print("Integratie: parse-fouten → /api/process → FriendlyError JSON")
print("=" * 65)

cases = [
    # (latex_input, verwachte substring in message, moet snippet hebben?)
    ('2.(9+3)-4+10',  "Onbekend teken",         True),
    ('(1+2',          "Ongesloten",             False),
    ('1+',            "eindigt halverwege",     False),
    ('root(27)',      "root()",                 False),
    ('log(10)',       "Onbekende functie",      False),
]

for latex, expected, want_snippet in cases:
    resp = post('/api/process', {'latex': latex})
    if resp.get('success'):
        print(f"  ✗ {latex!r}: verwachtte fout, kreeg success")
        fail += 1
        continue

    if 'error_detail' not in resp:
        print(f"  ✗ {latex!r}: geen error_detail in response")
        fail += 1
        continue

    detail = resp['error_detail']
    # verplichte velden
    missing = [k for k in ('message', 'hint', 'position', 'snippet', 'raw')
               if k not in detail]
    if missing:
        print(f"  ✗ {latex!r}: error_detail mist velden {missing}")
        fail += 1
        continue

    if expected not in detail['message']:
        print(f"  ✗ {latex!r}: verwachtte '{expected}' in message, kreeg: {detail['message']!r}")
        fail += 1
        continue

    if want_snippet and not detail['snippet']:
        print(f"  ✗ {latex!r}: verwachtte snippet, kreeg none")
        fail += 1
        continue

    print(f"  ✓ {latex!r:<25} → '{detail['message'][:50]}...'")
    ok += 1

# Ook /api/export_json
print()
print("Integratie: parse-fouten → /api/export_json")
print("=" * 65)
resp = post('/api/export_json', {'latex': '1++', 'mathml': ''})
if resp.get('success'):
    print(f"  ✗ verwachtte fout, kreeg success")
    fail += 1
elif 'error_detail' not in resp:
    print(f"  ✗ geen error_detail in response")
    fail += 1
else:
    print(f"  ✓ /api/export_json geeft error_detail terug")
    ok += 1

print()
print(f"=== {ok} geslaagd, {fail} gefaald ===")
server.shutdown()
sys.exit(0 if fail == 0 else 1)
