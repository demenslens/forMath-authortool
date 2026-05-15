"""
Inspecteer een geexporteerde ForMath JSON en toon wat het werkblad ziet.

Gebruik:
    python3 tests/inspect_export.py ~/Desktop/formath_JSON/opgave_XXX.json
"""
import json
import sys
import os


def main(argv):
    if len(argv) < 2:
        print("Gebruik: python3 tests/inspect_export.py <pad/naar/opgave.json>")
        return 1

    path = argv[1]
    if not os.path.exists(path):
        print(f"Bestand bestaat niet: {path}")
        return 1

    with open(path, encoding='utf-8') as f:
        d = json.load(f)

    print(f"Bestand: {path}")
    print(f"Grootte: {os.path.getsize(path)} bytes")
    print(f"Laatst gewijzigd: {os.path.getmtime(path)}")
    print()

    expr = d.get('metadata', {}).get('expressie', {})
    print("metadata.expressie-velden:")
    for key in ('latex', 'latex_display', 'tekst', 'mathml'):
        val = expr.get(key, '<ONTBREEKT>')
        print(f"  {key:<14} = {val!r}")

    print()
    print("Werkblad leest uit het veld 'latex'. Bevat dat \\left(?")
    latex = expr.get('latex', '')
    if r'\left(' in latex:
        count = latex.count(r'\left(')
        print(f"  ✓ Ja, {count}× \\left( gevonden.")
    else:
        print("  ✗ Nee — geen \\left( in het latex-veld.")
        print("    Dit JSON-bestand is vermoedelijk gegenereerd vóór de haakjes-fix.")
        print("    Genereer opnieuw via de Invoertool.")

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
