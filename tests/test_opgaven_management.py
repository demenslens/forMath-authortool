"""
Integratie-tests voor opgavenbeheer (iteratie 5).

Endpoints gedekt:
- GET  /api/list_opgaven         — lijst van opgaven met metadata
- GET  /api/load_opgave?id=...   — volledige JSON + SVG
- POST /api/delete_opgave        — verwijder JSON + SVG
- POST /api/export_json          — met overwrite_id

Plus security: path-traversal bescherming op id-parameters.
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
json_exporter.OUTPUT_DIR = tempfile.mkdtemp(prefix='formath_mgmt_')

s = socket.socket(); s.bind(('127.0.0.1', 0)); port = s.getsockname()[1]; s.close()
srv = HTTPServer(('127.0.0.1', port), ForMathHandler)
threading.Thread(target=srv.serve_forever, daemon=True).start()
time.sleep(0.3)


def req(method, path, body=None):
    conn = HTTPConnection('127.0.0.1', port, timeout=5)
    headers = {}
    payload = None
    if body is not None:
        payload = json.dumps(body)
        headers['Content-Type'] = 'application/json'
    conn.request(method, path, body=payload, headers=headers)
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


# ─── list_opgaven op lege dir ──────────────────────────────────────
print("list_opgaven (leeg)")
r = req('GET', '/api/list_opgaven')
check('success=true', r.get('success') is True)
check('opgaven is lege lijst', r.get('opgaven') == [])
check('output_dir aanwezig', 'output_dir' in r)

# ─── Export wat opgaven ─────────────────────────────────────────────
print("\nExport 3 opgaven voor verdere tests")
r1 = req('POST', '/api/export_json', {'latex': '1/2+1/3'})
r2 = req('POST', '/api/export_json', {'latex': '(3+5)*2'})
r3 = req('POST', '/api/export_json', {'latex': r'\sqrt{9}+\frac{1}{4}',
                                       'randvoorwaarden': {'vereenvoudig_uitkomst': True}})
for i, r in enumerate([r1, r2, r3], 1):
    check(f'export {i} geslaagd', r.get('success') is True)

# ─── list_opgaven na export ────────────────────────────────────────
print("\nlist_opgaven (3 opgaven)")
r = req('GET', '/api/list_opgaven')
check('aantal = 3', len(r.get('opgaven', [])) == 3,
      f"kreeg {len(r.get('opgaven', []))}")
ids = [o['id'] for o in r['opgaven']]
check('alle items hebben id', all(bool(i) for i in ids))
check('alle items hebben tekst',
      all(bool(o.get('tekst')) for o in r['opgaven']))
check('has_svg veld is aanwezig',
      all('has_svg' in o for o in r['opgaven']))
check('items hebben aantal_mathblocks',
      all('aantal_mathblocks' in o for o in r['opgaven']))

# ─── load_opgave op bestaand ID ─────────────────────────────────────
print("\nload_opgave")
target = ids[0]
r = req('GET', f'/api/load_opgave?id={target}')
check('success=true', r.get('success') is True)
check('opgave-object aanwezig', isinstance(r.get('opgave'), dict))
check('metadata bevat id', r['opgave']['metadata'].get('id') == target)
check('svg is string',  isinstance(r.get('svg'), str))
check('svg is niet leeg', len(r.get('svg', '')) > 100)

# ─── load_opgave op onbestaand ID ──────────────────────────────────
print("\nload_opgave (onbestaand)")
r = req('GET', '/api/load_opgave?id=99999999_999')
check('success=false', r.get('success') is False)
check('error-bericht aanwezig', bool(r.get('error')))

# ─── Path-traversal bescherming ────────────────────────────────────
print("\nSecurity: path-traversal bescherming")
r = req('GET', '/api/load_opgave?id=../etc/passwd')
check('load blokkeert traversal', r.get('success') is False)
r = req('POST', '/api/delete_opgave', {'id': '../../../etc/passwd'})
check('delete blokkeert traversal', r.get('success') is False)
r = req('POST', '/api/export_json', {'latex': '1+1', 'overwrite_id': '../evil'})
check('export blokkeert traversal in overwrite_id',
      r.get('success') is False)

# ─── overwrite_id flow ─────────────────────────────────────────────
print("\nOverwrite bestaande opgave")
# Onthoud originele inhoud
orig = req('GET', f'/api/load_opgave?id={target}')
orig_tekst = orig['opgave']['metadata']['expressie']['tekst']

# Overschrijf met andere expressie
r = req('POST', '/api/export_json', {
    'latex': '7+8',
    'overwrite_id': target,
})
check('overwrite-export success', r.get('success') is True)
check('filename bevat zelfde id', target in r.get('filename', ''))

# Lees opnieuw: moet nu '7+8' zijn
r = req('GET', f'/api/load_opgave?id={target}')
new_tekst = r['opgave']['metadata']['expressie']['tekst']
check('expressie na overwrite is 7+8', new_tekst == '7+8',
      f"kreeg {new_tekst!r}")
check('tekst verschilt van origineel', new_tekst != orig_tekst)

# Lijst heeft nog 3 opgaven (geen nieuwe)
r = req('GET', '/api/list_opgaven')
check('lijst heeft nog 3 opgaven na overwrite', len(r['opgaven']) == 3)

# ─── delete_opgave ──────────────────────────────────────────────────
print("\nDelete opgave")
r = req('POST', '/api/delete_opgave', {'id': target})
check('delete success', r.get('success') is True)
check('removed bevat JSON', any('.json' in f for f in r.get('removed', [])))
check('removed bevat SVG',  any('.svg' in f  for f in r.get('removed', [])))

# Nu gone
r = req('GET', f'/api/load_opgave?id={target}')
check('na delete: load faalt', r.get('success') is False)

r = req('GET', '/api/list_opgaven')
check('lijst heeft nog 2 opgaven', len(r['opgaven']) == 2,
      f"kreeg {len(r['opgaven'])}")

# ─── delete onbestaand ─────────────────────────────────────────────
print("\nDelete onbestaand")
r = req('POST', '/api/delete_opgave', {'id': 'nope_123'})
check('delete faalt op onbestaand', r.get('success') is False)

print()
print(f"=== {ok} geslaagd, {fail} gefaald ===")
srv.shutdown()
sys.exit(0 if fail == 0 else 1)
