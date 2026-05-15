#!/usr/bin/env python3
"""
ForMath Simplify Injector
==========================
Voegt SIMPLIFY_OP mathblocks toe aan de AST waar een bewerking een
vereenvoudigbare breuk als uitkomst heeft (GGD teller/noemer > 1).

De ruwe uitkomst van Python's Fraction is altijd al vereenvoudigd,
dus we gebruiken evaluate_raw() om de ruwe teller/noemer te zien
voordat Python vereenvoudigt.

Wordt aangeroepen NA manifold_converter en NA convert_matroesjka,
vóór tak_allocator en step_calculator.
"""

import copy
from typing import Dict, Any, Tuple, Optional

try:
    from ast_visualizer import evaluate_raw, evaluate
except ImportError:
    from .ast_visualizer import evaluate_raw, evaluate


def _ggd(a: int, b: int) -> int:
    """Grootste gemeenschappelijke deler via Euclides."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _is_vereenvoudigbaar(raw: Optional[Tuple[int, int]]) -> bool:
    """Check of een ruwe (teller, noemer) vereenvoudigbaar is.

    Skip irrationale benaderingen (zoals uitkomsten met π): bij extreem
    grote teller/noemer is vereenvoudigen niet zinvol.
    """
    if raw is None:
        return False
    teller, noemer = raw
    if noemer == 0:
        return False
    if noemer == 1:
        return False  # Geheel getal, niet vereenvoudigbaar als breuk
    # Drempel voor irrationale benaderingen: geen SIMPLIFY_OP injecteren
    if noemer > 10000 or abs(teller) > 100000:
        return False
    return _ggd(abs(teller), abs(noemer)) > 1


def _vereenvoudig(raw: Tuple[int, int]) -> Tuple[int, int]:
    """Deel teller en noemer door GGD."""
    teller, noemer = raw
    g = _ggd(abs(teller), abs(noemer))
    if g == 0:
        return raw
    return (teller // g, noemer // g)


def _wrap_with_simplify(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Pak een node in met SIMPLIFY_OP als zijn ruwe uitkomst vereenvoudigbaar is.
    Returns de ingewikkelde node (of de originele als niet vereenvoudigbaar).
    """
    raw = evaluate_raw(node)
    if not _is_vereenvoudigbaar(raw):
        return node

    teller_ruw, noemer_ruw = raw
    teller_verv, noemer_verv = _vereenvoudig(raw)
    ggd = _ggd(abs(teller_ruw), abs(noemer_ruw))

    return {
        'type': 'SIMPLIFY_OP',
        'source': node,
        'ruw': {
            'teller': teller_ruw,
            'noemer': noemer_ruw,
        },
        'vereenvoudigd': {
            'teller': teller_verv,
            'noemer': noemer_verv,
        },
        'ggd': ggd,
    }


def _inject_recursive(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Loop recursief door de AST en voeg SIMPLIFY_OP in na elke operatie-node
    waarvan de ruwe uitkomst vereenvoudigbaar is.
    
    Let op: we injecteren NA de node (dus de parent krijgt een SIMPLIFY_OP
    als kind in plaats van de originele node).
    """
    t = node.get('type')

    # Leaves: niets te doen
    if t in ('NUMBER', 'FRACTION', None):
        return node

    # Eerst kinderen behandelen (bottom-up)
    if t == 'BINARY_OP':
        node['left']  = _inject_recursive(node.get('left', {}))
        node['right'] = _inject_recursive(node.get('right', {}))

    elif t == 'MANIFOLD_OP':
        node['operands'] = [_inject_recursive(op) for op in node.get('operands', [])]

    elif t == 'POWER':
        node['base'] = _inject_recursive(node.get('base', {}))

    elif t == 'ROOT':
        node['radicand'] = _inject_recursive(node.get('radicand', {}))

    elif t == 'MATROESJKA_OP':
        shells = node.get('shells', [])
        for i, shell in enumerate(shells):
            if i == 0:
                shell['left'] = _inject_recursive(shell.get('left', {}))
            shell['right'] = _inject_recursive(shell.get('right', {}))

    elif t == 'SIMPLIFY_OP':
        # Zou eigenlijk niet moeten gebeuren (dubbele wrap), maar voor zekerheid
        node['source'] = _inject_recursive(node.get('source', {}))
        return node

    # Nu: als DEZE node een vereenvoudigbare uitkomst heeft, pak hem in
    return _wrap_with_simplify(node)


def inject_simplify_ops(ast: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Hoofdingang: voeg SIMPLIFY_OP mathblocks toe aan de AST.

    Args:
        ast: AST na manifold conversie en Matroesjka conversie

    Returns:
        (ast_met_simplify_ops, stats)
        stats bevat:
          - simplify_count: aantal ingevoegde SIMPLIFY_OP nodes
    """
    ast = copy.deepcopy(ast)
    ast = _inject_recursive(ast)
    stats = _count_simplify_ops(ast)
    return ast, stats


def _count_simplify_ops(node: Dict[str, Any]) -> Dict[str, int]:
    """Tel het aantal SIMPLIFY_OP nodes in de AST."""
    count = [0]

    def _count(n):
        t = n.get('type')
        if t == 'SIMPLIFY_OP':
            count[0] += 1
            _count(n.get('source', {}))
        elif t == 'BINARY_OP':
            _count(n.get('left', {}))
            _count(n.get('right', {}))
        elif t == 'MANIFOLD_OP':
            for op in n.get('operands', []):
                _count(op)
        elif t == 'POWER':
            _count(n.get('base', {}))
        elif t == 'ROOT':
            _count(n.get('radicand', {}))
        elif t == 'MATROESJKA_OP':
            shells = n.get('shells', [])
            for i, shell in enumerate(shells):
                if i == 0:
                    _count(shell.get('left', {}))
                _count(shell.get('right', {}))

    _count(node)
    return {'simplify_count': count[0]}


# ─── Efficiëntie-analyse ──────────────────────────────────────────────────────

def analyze_simplify_efficiency(simplify_node: Dict[str, Any],
                                parent_node: Optional[Dict[str, Any]] = None,
                                parent_op: Optional[str] = None) -> Dict[str, Any]:
    """
    Bepaal of het vereenvoudigen van deze tussenuitkomst efficiënt is.

    Heuristieken:
    - Als er geen parent is (dit is de einduitkomst): altijd aanbevolen
    - Als parent een optelling is met andere breuken: aanbevolen (kleinere KGV)
    - Als parent een vermenigvuldiging is: aanbevolen (kleinere tussenwaarden)
    - Als parent een deling is: aanbevolen
    - Als parent een macht is: aanbevolen (kleinere grondtal)
    - Als parent een wortel is: aanbevolen

    Returns:
        Dict met:
          - aanbevolen (bool)
          - reden (string)
          - score (float 0-1)
          - alternatieven (list van strings, optioneel)
    """
    if parent_node is None:
        return {
            'aanbevolen': True,
            'reden': 'einduitkomst: altijd vereenvoudigen',
            'score': 1.0,
        }

    pt = parent_node.get('type')

    if pt == 'BINARY_OP':
        op = parent_node.get('operator', '')
        if op == '+':
            return {
                'aanbevolen': True,
                'reden': 'volgende stap is optelling: kleinere breuken geven kleinere KGV',
                'score': 0.9,
            }
        if op == '×':
            return {
                'aanbevolen': True,
                'reden': 'volgende stap is vermenigvuldiging: vereenvoudigen voorkomt grote tussenwaarden',
                'score': 0.85,
                'alternatieven': ['kruiselings vereenvoudigen in één stap met volgende bewerking'],
            }
        if op == ':':
            return {
                'aanbevolen': True,
                'reden': 'volgende stap is deling: vereenvoudigen geeft kleinere uitkomst',
                'score': 0.8,
            }

    if pt == 'MANIFOLD_OP':
        op = parent_node.get('operator', '')
        if op == '+':
            return {
                'aanbevolen': True,
                'reden': 'volgende stap is optel-manifold: kleinere breuken maken KGV-berekening eenvoudiger',
                'score': 0.9,
            }
        if op == '×':
            return {
                'aanbevolen': True,
                'reden': 'volgende stap is vermenigvuldig-manifold: vereenvoudigen voorkomt grote tussenwaarden',
                'score': 0.85,
            }

    if pt == 'POWER':
        return {
            'aanbevolen': True,
            'reden': 'volgende stap is machtsverheffen: vereenvoudigen geeft kleiner grondtal',
            'score': 0.9,
        }

    if pt == 'ROOT':
        return {
            'aanbevolen': True,
            'reden': 'volgende stap is worteltrekken: vereenvoudigen vergemakkelijkt wortel',
            'score': 0.9,
        }

    if pt == 'MATROESJKA_OP':
        return {
            'aanbevolen': True,
            'reden': 'volgende stap is Matroesjka-keten: vereenvoudigen onderweg voorkomt oplopende complexiteit',
            'score': 0.85,
        }

    # Onbekend
    return {
        'aanbevolen': True,
        'reden': 'standaard: vereenvoudigen is meestal efficiënt',
        'score': 0.7,
    }


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import sys
    import os
    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from expression_parser import parse_expression
    from ast_normalizer import normalize_ast
    from manifold_detector import detect_manifolds, detect_matroesjka
    from manifold_converter import convert_to_manifolds, convert_matroesjka

    tests = [
        '3/4*8/9',         # → 24/36, vereenvoudigbaar
        '3/4*8/9+1/2',     # geneste vereenvoudiging
        '6/4',             # leaf-breuk
        '1/4+1/6',         # ruwe optelling → 10/24
        '(3/4)^2',         # 9/16, niet vereenvoudigbaar
        '2*(3+4*5)-6/2+7', # standaard testcase
    ]

    for expr in tests:
        print(f"\n=== {expr} ===")
        ast = parse_expression(expr)
        norm = normalize_ast(ast)
        ann, stats = detect_manifolds(norm)
        conv, _ = convert_to_manifolds(ann, stats)
        mat_ann, chains = detect_matroesjka(conv)
        conv, _ = convert_matroesjka(mat_ann, chains)

        injected, inj_stats = inject_simplify_ops(conv)
        print(f"SIMPLIFY_OPs toegevoegd: {inj_stats['simplify_count']}")
