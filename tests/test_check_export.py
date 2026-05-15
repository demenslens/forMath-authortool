"""
Integratie-test voor /api/check_export — het endpoint dat iteratie 3
gebruikt om vóór export te checken of de expressie al eerder geëxporteerd is.

Tests:
1. Lege output-dir → duplicates is lege lijst
2. Na export → duplicates bevat de filename
3. Andere expressie → geen duplicates
4. Response bevat expression, output_dir, duplicates
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

TMP = tempfile.mkdtemp(prefix='formath_check_test_')
json_exporter.OUTPUT_DIR = TMP

s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
server = HTTPServer(('127.0.0.1', port), ForMathHandler)
threading.Thread(target=server.serve_forever, daemon=True).start()
time.sleep(0.3)


def post(path, body):
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('POST', path, body=json.dumps(body),
                 headers={'Content-Type': 'application/json'})
    return json.loads(conn.getresponse().read())


ok = fail = 0

def check(label, condition, detail=''):
    global ok, fail
    if condition:
        print(f"  ✓ {label}")
        ok += 1
    else:
        print(f"  ✗ {label}{(': ' + detail) if detail else ''}")
        fail += 1


print("check_export integratie")
print("=" * 50)

# Test 1: lege dir
r = post('/api/check_export', {'latex': r'\frac{1}{2}+\frac{1}{3}'})
check('lege dir → success=true', r.get('success') is True)
check('lege dir → duplicates=[]',  r.get('duplicates') == [])
check('response heeft expression-veld', 'expression' in r)
check('response heeft output_dir-veld',  'output_dir' in r)

# Test 2: na export
r = post('/api/export_json', {'latex': r'\frac{1}{2}+\frac{1}{3}', 'mathml': ''})
check('export succeeds', r.get('success') is True)
fname = r.get('filename', '')

r = post('/api/check_export', {'latex': r'\frac{1}{2}+\frac{1}{3}'})
check('na export → duplicates bevat filename',
      fname in r.get('duplicates', []),
      f"duplicates={r.get('duplicates')}")

# Test 3: andere expressie, geen match
r = post('/api/check_export', {'latex': r'2+2'})
check('andere expressie → geen duplicates', r.get('duplicates') == [])

# Test 4: lege input
r = post('/api/check_export', {'latex': ''})
check('lege input → success=false', r.get('success') is False)

print()
print(f"=== {ok} geslaagd, {fail} gefaald ===")
server.shutdown()
sys.exit(0 if fail == 0 else 1)
