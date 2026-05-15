"""
Round-trip test: draai de volledige pipeline op een set voorbeeld-expressies
en valideer dat de geëxporteerde JSON voldoet aan het werkblad-formaat.

Dekking:
- Alle 11 originele voorbeelden uit _archief/voorbeeld_outputs/
- Plus extra edge-cases (negatieve haakjes, geneste breuken, machten, wortels)

Draaien:
    python3 tests/test_round_trip.py

Exit 0 bij succes, 1 bij één of meer falers.
"""
from __future__ import annotations

import os
import sys
import tempfile
import traceback

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'python_bestanden'))
sys.path.insert(0, os.path.join(ROOT, 'formath_web'))
sys.path.insert(0, HERE)

# Pipeline-imports
from server import latex_to_expression, ast_to_latex_display
from expression_parser import parse_expression
from ast_normalizer import normalize_ast
from manifold_detector import detect_manifolds, detect_matroesjka
from manifold_converter import convert_to_manifolds, convert_matroesjka
import json_exporter
from formath_validator import validate_opgave


# Testcases. LaTeX of platte expressie; beide worden door latex_to_expression geaccepteerd
# (platte expressies blijven ongewijzigd door de converter).
#
# NOTE: 311_002 gebruikte punt-als-vermenigvuldiging ('2.(9+3)'). De parser
# ondersteunt die notatie niet. INSTALLATIE.txt is gecorrigeerd om dit
# duidelijk te maken. De test case is vervangen door een equivalente met '*'.
TEST_CASES = [
    # 11 originelen uit _archief/voorbeeld_outputs/ (met 311_002 gecorrigeerd)
    ('311_001', '1/9-(3/2+5/6)+2/3+[1/9-(1/2+5/9-1/6)+5/3]'),
    ('311_002', '2*(9+3)-4+10'),                      # was '2.(9+3)-4+10' — punt niet ondersteund
    ('311_003', '-1+[1/2-(1/3-1/2+1/5)]+2'),
    ('311_004', '(1/2+1/3)-1/4'),
    ('311_005', '4 - [2 + (1 - 2/3) - (-4 + 1/5)] + [7 - (6 + 1/15) - 2/5]'),
    ('311_006', '1 +[(10:2)*6 +(15:3)-3]:(4*2) - [(3*5):5+2]'),
    ('311_007', '[(3^2)*(12-9)^3]:(9-6)^3:(-3)*[(-6)^2]:3^4+(-2)^3'),
    ('311_008', r'\sqrt{9}+\sqrt{16}+\sqrt{25}'),
    ('311_009', '2*(3+4*5)-6/2+7'),
    ('311_010', '1+[(10:2)*6+(15:3)-3]:(4*2)-[(3*5):5+2]'),
    ('311_011', '2*(3+4*5)-6/2+7'),
    # extra edge-cases
    ('edge_01', '1/2+1/3'),
    ('edge_02', r'\frac{1}{2}+\frac{1}{3}'),
    ('edge_03', '3^2+5'),
    ('edge_04', r'\sqrt[3]{27}'),
    ('edge_05', '(1+2)*(3+4)+5'),
    ('edge_06', '(1/4)^3:(3/4)^2'),                   # gebruikers-bugrapport: haakjes om breukbase
]


def run_pipeline(latex_or_expr: str):
    """Volledige pipeline: input → converted AST + latex_display + expression."""
    expr = latex_to_expression(latex_or_expr)
    ast = parse_expression(expr)
    norm = normalize_ast(ast)
    ann, stats = detect_manifolds(norm)
    conv, _ = convert_to_manifolds(ann, stats)
    mat_ann, chains = detect_matroesjka(conv)
    conv, _ = convert_matroesjka(mat_ann, chains)
    display = ast_to_latex_display(conv)
    return conv, display, expr


def main() -> int:
    tmp_dir = tempfile.mkdtemp(prefix='formath_roundtrip_')
    json_exporter.OUTPUT_DIR = tmp_dir

    print(f"Round-trip test — {len(TEST_CASES)} expressies")
    print(f"Output naar: {tmp_dir}")
    print("=" * 70)

    n_pass = 0
    n_fail = 0
    n_warn = 0

    # We moeten unieke IDs genereren — anders overschrijft de exporter
    # (zijn counter werkt per datum, niet per test-run).
    for label, src in TEST_CASES:
        try:
            conv, display, expr = run_pipeline(src)
            result_json, _ = json_exporter.generate_formath_json(
                conv, latex=src, mathml='',
                latex_display=display, expression=expr,
            )
        except Exception as e:
            print(f"  ✗ {label:<10} PIPELINE CRASH: {type(e).__name__}: {e}")
            traceback.print_exc()
            n_fail += 1
            continue

        validation = validate_opgave(result_json)
        if validation.ok and not validation.warnings:
            print(f"  ✓ {label:<10} {src[:50]}")
            n_pass += 1
        elif validation.ok:
            print(f"  ~ {label:<10} {src[:50]}  ({len(validation.warnings)} warning(s))")
            for w in validation.warnings:
                print(f"      ⚠ {w}")
            n_pass += 1
            n_warn += 1
        else:
            print(f"  ✗ {label:<10} {src[:50]}")
            for err in validation.errors[:5]:
                print(f"      ✗ {err}")
            if len(validation.errors) > 5:
                print(f"      ... (+{len(validation.errors) - 5} meer)")
            n_fail += 1

    print("=" * 70)
    print(f"Resultaat: {n_pass} geslaagd ({n_warn} met warning), {n_fail} gefaald")

    return 0 if n_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
