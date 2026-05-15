"""
End-to-end integratie-test voor iteratie 4 (inspector).

Bevestigt dat inspector-velden correct door de HTTP-API lopen en
in de geëxporteerde JSON terechtkomen.

Flow:
  1. POST /api/process           → mathblocks-summary terug
  2. POST /api/export_json       → met randvoorwaarden + mathblock_klasses
  3. Open het geschreven JSON    → verifieer metadata.randvoorwaarden
                                   en per-mathblock klasse + kgv
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
json_exporter.OUTPUT_DIR = tempfile.mkdtemp(prefix='formath_insp_')

s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
srv = HTTPServer(('127.0.0.1', port), ForMathHandler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.3)


def post(path, body):
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    conn.request('POST', path, body=json.dumps(body),
                 headers={'Content-Type': 'application/json'})
    return json.loads(conn.getresponse().read())


ok = fail = 0

def check(label, cond, detail=''):
    global ok, fail
    if cond:
        print(f"  ✓ {label}")
        ok += 1
    else:
        print(f"  ✗ {label}{(' — ' + detail) if detail else ''}")
        fail += 1


print("E2E inspector-flow")
print("=" * 60)

# 1. Process
r = post('/api/process', {'latex': r'\frac{1}{2}+\frac{1}{3}'})
check('process success', r.get('success') is True)
check('mathblocks-veld aanwezig', 'mathblocks' in r)
mbs = r.get('mathblocks', [])
check('exact 1 mathblock voor 1/2+1/3', len(mbs) == 1, f"kreeg {len(mbs)}")
if mbs:
    mb = mbs[0]
    check('mathblock heeft id', 'id' in mb)
    check('mathblock heeft symbool', mb.get('symbool', ''))
    check('heeft_breuken is True', mb.get('heeft_breuken') is True)
    check('input_preview bevat breuken',
          mb.get('input_preview') == ['1/2', '1/3'],
          f"kreeg {mb.get('input_preview')}")
    mb_id = mb['id']
else:
    mb_id = None

# 2. Export met inspector-velden
print()
r = post('/api/export_json', {
    'latex': r'\frac{1}{2}+\frac{1}{3}',
    'randvoorwaarden': {'vereenvoudig_uitkomst': True},
    'mathblock_klasses': {mb_id: 'B2'} if mb_id else {},
})
check('export success', r.get('success') is True)
fp = r.get('filepath')
check('filepath teruggegeven', bool(fp))

# 3. Lees het geschreven bestand en verifieer
if fp and os.path.exists(fp):
    with open(fp, encoding='utf-8') as f:
        d = json.load(f)

    rv = d.get('metadata', {}).get('randvoorwaarden', {})
    check('metadata.randvoorwaarden.vereenvoudig_uitkomst=True',
          rv.get('vereenvoudig_uitkomst') is True,
          f"kreeg {rv}")

    if mb_id:
        mb = d['mathblocks'][0]
        check(f'mathblock {mb_id} heeft klasse B2',
              mb.get('klasse') == 'B2',
              f"kreeg {mb.get('klasse')}")
        check(f'mathblock {mb_id} heeft kgv=6',
              mb.get('kgv') == 6,
              f"kreeg {mb.get('kgv')}")

# 4. Export zonder inspector-velden — default-gedrag (geen klasse, rv=false)
print()
r = post('/api/export_json', {'latex': '1+1'})
check('export zonder inspector-velden', r.get('success') is True)
if r.get('filepath'):
    with open(r['filepath'], encoding='utf-8') as f:
        d = json.load(f)
    rv = d.get('metadata', {}).get('randvoorwaarden', {})
    check('default vereenvoudig_uitkomst=false',
          rv.get('vereenvoudig_uitkomst') is False)
    mbs = d.get('mathblocks', [])
    check('geen klasse-velden zonder input',
          all('klasse' not in mb for mb in mbs))

# 5. Export met onbekende klasse — exporter negeert stil, validator geeft geen klasse-veld
print()
r = post('/api/export_json', {
    'latex': '1+1',
    'mathblock_klasses': {'A1': 'Z9'},
})
if r.get('filepath'):
    with open(r['filepath'], encoding='utf-8') as f:
        d = json.load(f)
    check('onbekende klasse wordt niet geëxporteerd',
          all('klasse' not in mb for mb in d.get('mathblocks', [])))

# 6. Opdracht-veld (iteratie 6)
print()
# 6a. Default is 'reken_uit' als niks meesturen
r = post('/api/export_json', {'latex': '2+3'})
if r.get('filepath'):
    with open(r['filepath'], encoding='utf-8') as f:
        d = json.load(f)
    check('opdracht-default is reken_uit',
          d['metadata'].get('opdracht') == 'reken_uit')

# 6b. Expliciete 'vereenvoudig'
r = post('/api/export_json', {'latex': r'\frac{4}{6}', 'opdracht': 'vereenvoudig'})
if r.get('filepath'):
    with open(r['filepath'], encoding='utf-8') as f:
        d = json.load(f)
    check('opdracht=vereenvoudig komt door in JSON',
          d['metadata'].get('opdracht') == 'vereenvoudig')

# 6c. Onbekende waarde valt terug op default
r = post('/api/export_json', {'latex': '1+1', 'opdracht': 'raar'})
if r.get('filepath'):
    with open(r['filepath'], encoding='utf-8') as f:
        d = json.load(f)
    check('onbekende opdracht → fallback reken_uit',
          d['metadata'].get('opdracht') == 'reken_uit')

print()
print(f"=== {ok} geslaagd, {fail} gefaald ===")
srv.shutdown()
sys.exit(0 if fail == 0 else 1)
