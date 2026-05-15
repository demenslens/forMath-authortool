#!/usr/bin/env python3
"""
ForMath Mixed Number Injector
==============================
Voegt een MIXED_NUMBER_OP toe BOVENOP de root mathblock als die een oneigenlijke
breuk als einduitkomst heeft (|teller| > noemer en noemer != 1).

Dit is consistent met onze afspraak:
- Op tussenuitkomsten gebeurt GEEN omrekening naar gemengd getal
- Alleen bij de einduitkomst wordt de oneigenlijke breuk omgezet naar gemengd getal,
  en dat is een aparte stap die de leerling expliciet moet zetten

De MIXED_NUMBER_OP node heeft:
- source: de underlying root node (de oneigenlijke breuk)
- ruw: {teller, noemer} — de oneigenlijke breuk
- gemengd: {geheel, teller, noemer} — het gemengde getal (b.v. 2 11/12)

Wordt aangeroepen NA inject_simplify_ops, vóór tak_allocator en step_calculator.
"""

import copy
from typing import Dict, Any, Tuple, Optional

try:
    from ast_visualizer import evaluate
except ImportError:
    from .ast_visualizer import evaluate


def _to_int_pair(value) -> Optional[Tuple[int, int]]:
    """Converteer een Fraction-achtige waarde naar (teller, noemer)."""
    if value is None:
        return None
    try:
        from fractions import Fraction
        if isinstance(value, Fraction):
            return (value.numerator, value.denominator)
        if isinstance(value, int):
            return (value, 1)
        # Float of iets anders: niet ondersteund
        return None
    except Exception:
        return None


def _is_oneigenlijke_breuk(pair: Optional[Tuple[int, int]]) -> bool:
    """
    Check of een (teller, noemer) een oneigenlijke breuk is.
    Definitie: noemer != 1 (geen geheel getal) en |teller| >= noemer.

    Skip irrationale benaderingen (zoals uitkomsten met π): als de noemer
    extreem groot is, is het geen "echte" oneigenlijke breuk maar een
    decimale benadering — daar slaat het MIXED_NUMBER_OP geen brug.
    """
    if pair is None:
        return False
    teller, noemer = pair
    if noemer == 0 or noemer == 1:
        return False
    # Drempel: bij irrationale benaderingen (π, etc.) is de noemer enorm.
    # In zo'n geval geen MIXED_NUMBER_OP injecteren.
    if noemer > 10000 or abs(teller) > 100000:
        return False
    return abs(teller) >= noemer


def _naar_gemengd_getal(teller: int, noemer: int) -> Tuple[int, int, int]:
    """
    Zet een oneigenlijke breuk om naar (geheel, rest_teller, noemer).
    Werkt ook voor negatieve breuken: het hele getal krijgt het teken,
    rest_teller is positief.

    Voorbeelden:
        35/12 → (2, 11, 12)
        -35/12 → (-2, 11, 12)
        7/3 → (2, 1, 3)
    """
    sign = -1 if teller < 0 else 1
    abs_t = abs(teller)
    geheel = abs_t // noemer
    rest = abs_t - geheel * noemer
    return (sign * geheel, rest, noemer)


def _wrap_with_mixed_number(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pak de root node in met MIXED_NUMBER_OP als zijn uitkomst een oneigenlijke
    breuk is.
    """
    val = evaluate(node)
    pair = _to_int_pair(val)
    if not _is_oneigenlijke_breuk(pair):
        return node

    teller, noemer = pair
    geheel, rest_teller, gemengd_noemer = _naar_gemengd_getal(teller, noemer)

    return {
        'type': 'MIXED_NUMBER_OP',
        'source': node,
        'ruw': {
            'teller': teller,
            'noemer': noemer,
        },
        'gemengd': {
            'geheel': geheel,
            'teller': rest_teller,
            'noemer': gemengd_noemer,
        },
    }


def inject_mixed_number(ast: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, int]]:
    """
    Hoofdingang: voeg een MIXED_NUMBER_OP toe BOVENOP de root als die een
    oneigenlijke breuk als einduitkomst heeft.

    Args:
        ast: AST na simplify_injector

    Returns:
        (ast_met_mixed_number, stats)
        stats bevat:
          - mixed_number_count: 0 of 1
    """
    ast = copy.deepcopy(ast)

    # Alleen wrap de root, niet recursief
    new_root = _wrap_with_mixed_number(ast)
    count = 1 if new_root is not ast else 0

    return new_root, {'mixed_number_count': count}


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from expression_parser import parse_expression
    from ast_normalizer import normalize_ast
    from manifold_detector import detect_manifolds, detect_matroesjka
    from manifold_converter import convert_to_manifolds, convert_matroesjka
    from simplify_injector import inject_simplify_ops

    tests = [
        '(1/3+1/4):1/5',   # → 35/12, oneigenlijk → 2 11/12
        '7/3',              # leaf, geen wrap (alleen op operatie-root)
        '1/2+1/4',          # → 3/4, geen oneigenlijk
        '3/2+1',            # → 5/2, oneigenlijk → 2 1/2
        '1/2*1/3',          # → 1/6, geen oneigenlijk
    ]

    for expr in tests:
        print(f"\n=== {expr} ===")
        ast = parse_expression(expr)
        norm = normalize_ast(ast)
        ann, stats = detect_manifolds(norm)
        conv, _ = convert_to_manifolds(ann, stats)
        mat_ann, chains = detect_matroesjka(conv)
        conv, _ = convert_matroesjka(mat_ann, chains)
        conv, _ = inject_simplify_ops(conv)
        wrapped, inj_stats = inject_mixed_number(conv)
        print(f"  mixed_number_count: {inj_stats['mixed_number_count']}")
        print(f"  root type na wrap: {wrapped.get('type')}")
        if wrapped.get('type') == 'MIXED_NUMBER_OP':
            print(f"  ruw: {wrapped['ruw']}, gemengd: {wrapped['gemengd']}")
