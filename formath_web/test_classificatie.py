"""
Test de classificatie-validatielogica zonder de server te starten.
Simuleert het stuk uit _handle_export_json dat de classificatie verwerkt.
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classificatie_validator import (
    validate_classificatie, is_available, status_message
)

print("=" * 60)
print("TEST: classificatie_validator")
print("=" * 60)
print(status_message())
print(f"Validatie actief: {is_available()}")
print()

# Test cases
cases = [
    # (label, blok, verwacht: None=geldig of substring van foutmelding)
    ("Geen classificatie (None)", None, None),
    ("Lege classificatie", {}, None),
    ("Volledig geldig", {
        "domein": "algebra",
        "onderwerp": "breuken",
        "subonderwerp": "optellen_aftrekken",
        "type": "procedureel",
        "niveau_rtti": "T1",
        "moeilijkheid": 2,
        "leerjaar": [2, 3],
        "stroom": ["havo", "vwo"],
        "referentieniveau": "2F",
        "tags": ["kgv"],
    }, None),
    ("Minimaal: alleen domein", {"domein": "algebra"}, None),
    ("Onbekend extra veld (forward compat)", {
        "domein": "algebra",
        "nieuw_veld_uit_toekomst": "iets"
    }, None),
    ("Ongeldig domein", {"domein": "scheikunde"}, "domein"),
    ("Ongeldig RTTI", {"niveau_rtti": "T3"}, "niveau_rtti"),
    ("Moeilijkheid buiten range", {"moeilijkheid": 7}, "moeilijkheid"),
    ("Leerjaar als string i.p.v. array", {"leerjaar": "2"}, "leerjaar"),
    ("Tag met spaties (pattern)", {"tags": ["mijn tag"]}, "tags"),
    ("Geen dict maar string", "algebra",
     "moet een object zijn"),
]

passed = 0
failed = 0
for label, blok, expected in cases:
    actual = validate_classificatie(blok)
    if expected is None:
        ok = actual is None
    else:
        ok = actual is not None and expected.lower() in actual.lower()
    status = "OK" if ok else "FAIL"
    print(f"[{status}] {label}")
    if not ok:
        print(f"       verwacht: {expected!r}")
        print(f"       gekregen: {actual!r}")
    if ok:
        passed += 1
    else:
        failed += 1

print()
print(f"Resultaat: {passed} geslaagd, {failed} mislukt")

# Simuleer ook de _handle_export_json metadata-merge logica
print()
print("=" * 60)
print("TEST: metadata-merge (simulatie van server.py-logica)")
print("=" * 60)

def simulate_merge(request_data, base_result):
    """Bootst de relevante regels uit _handle_export_json na."""
    randvoorwaarden    = request_data.get('randvoorwaarden', {}) or {}
    opdracht           = request_data.get('opdracht', '') or ''
    classificatie      = request_data.get('classificatie', None)

    err = validate_classificatie(classificatie)
    if err:
        return {'success': False, 'error': f'Classificatie ongeldig: {err}'}

    if 'metadata' in base_result:
        base_result['metadata']['randvoorwaarden'] = randvoorwaarden
        base_result['metadata']['opdracht'] = opdracht
        if classificatie:
            base_result['metadata']['classificatie'] = classificatie

    return {'success': True, 'result': base_result}


# Scenario A: oude client (geen classificatie meegestuurd)
req_a = {
    'opdracht': 'vereenvoudig',
    'randvoorwaarden': {'vereenvoudig_uitkomst': True},
    # GEEN classificatie key
}
base = {
    'metadata': {
        'expressie': {'tekst': '1/2+1/3', 'latex': '...'},
        'aantal_mathblocks': 3,
        'aantal_steps': 2,
    },
    'mathblocks': [{'id': 'mb_1', 'klasse': 'B2'}]
}
out_a = simulate_merge(req_a, dict(metadata=dict(base['metadata']), mathblocks=base['mathblocks']))
assert out_a['success'], out_a
md_a = out_a['result']['metadata']
assert 'classificatie' not in md_a, "Oude client mag geen classificatie krijgen"
assert md_a['opdracht'] == 'vereenvoudig'
assert md_a['randvoorwaarden']['vereenvoudig_uitkomst'] is True
assert md_a['aantal_mathblocks'] == 3
assert md_a['aantal_steps'] == 2
assert md_a['expressie']['tekst'] == '1/2+1/3'
print("[OK] Scenario A — oude client zonder classificatie: alle bestaande velden intact, geen classificatie toegevoegd")

# Scenario B: nieuwe client met geldige classificatie
req_b = {
    'opdracht': 'vereenvoudig',
    'randvoorwaarden': {'vereenvoudig_uitkomst': True},
    'classificatie': {
        'domein': 'algebra',
        'onderwerp': 'breuken',
        'niveau_rtti': 'T1',
        'moeilijkheid': 2,
        'leerjaar': [2, 3],
        'stroom': ['havo'],
    }
}
out_b = simulate_merge(req_b, dict(metadata=dict(base['metadata']), mathblocks=base['mathblocks']))
assert out_b['success'], out_b
md_b = out_b['result']['metadata']
assert md_b['classificatie']['domein'] == 'algebra'
assert md_b['classificatie']['niveau_rtti'] == 'T1'
assert md_b['opdracht'] == 'vereenvoudig'
assert md_b['aantal_mathblocks'] == 3
print("[OK] Scenario B — nieuwe client met classificatie: alles correct opgeslagen")

# Scenario C: client met ongeldige classificatie (foute RTTI-waarde)
req_c = {
    'opdracht': 'vereenvoudig',
    'classificatie': {'niveau_rtti': 'T9'}
}
out_c = simulate_merge(req_c, dict(metadata=dict(base['metadata'])))
assert not out_c['success'], "Ongeldige classificatie moet 400-style fout geven"
assert 'Classificatie ongeldig' in out_c['error']
print("[OK] Scenario C — ongeldige classificatie wordt geweigerd met duidelijke fout")

# Scenario D: lege classificatie ({}) wordt niet weggeschreven
req_d = {
    'opdracht': 'vereenvoudig',
    'classificatie': {}
}
out_d = simulate_merge(req_d, dict(metadata=dict(base['metadata'])))
assert out_d['success']
assert 'classificatie' not in out_d['result']['metadata'], (
    "Lege classificatie moet niet als veld worden toegevoegd"
)
print("[OK] Scenario D — lege classificatie wordt overgeslagen (geen leeg veld in output)")

print()
print("Alle scenario's geslaagd.")
