#!/usr/bin/env python3
"""
ForMath JSON Exporter
=====================
Genereert een uitgebreide JSON beschrijving van een wiskundige opgave
op basis van de geconverteerde AST (na manifold conversie).

Output directory: ~/Desktop/formath_JSON/
"""

import json
import os
import sys
from datetime import date
from collections import defaultdict, OrderedDict

# Pipeline imports
PIPELINE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'python_bestanden')
if PIPELINE_DIR not in sys.path:
    sys.path.insert(0, PIPELINE_DIR)

from ast_visualizer import evaluate, format_result, compute_node_depth

# Dynamic OUTPUT_DIR: leest altijd de actuele waarde uit config.py
# Toegang via 'from json_exporter import OUTPUT_DIR' blijft werken, maar
# retourneert nu de actuele (mogelijk runtime-gewijzigde) directory.
def __getattr__(name):
    if name == 'OUTPUT_DIR':
        from config import get_output_dir
        return get_output_dir()
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def _current_output_dir():
    """Haal de actuele output ROOT directory op (live uit config).

    Dit is de root van de opgaven-opslag. Opgaven zelf staan in sub-folders
    daarvan (zie _current_write_dir).
    """
    from config import get_output_dir
    return get_output_dir()


# Default-sub-folder waarin nieuwe opgaven worden weggeschreven, indien
# er geen specifieke folder is gekozen. Hardcoded voor nu — later wordt
# dit een parameter vanuit de UI.
DEFAULT_WRITE_SUBFOLDER = 'Trial'


def _current_write_dir():
    """De directory waar een nieuwe opgave wordt weggeschreven.

    Dit is OUTPUT_DIR/Trial/ — niet OUTPUT_DIR zelf. De sub-folder wordt
    aangemaakt als hij nog niet bestaat.
    """
    root = _current_output_dir()
    write_dir = os.path.join(root, DEFAULT_WRITE_SUBFOLDER)
    os.makedirs(write_dir, exist_ok=True)
    return write_dir


# ─── Breuk-helpers ──────────────────────────────────────────────────────────

def _kgv(a: int, b: int) -> int:
    """Kleinste gemene veelvoud."""
    if a == 0 or b == 0:
        return 0
    return abs(a * b) // _ggd(a, b)


def _kgv_lijst(getallen):
    """KGV van een lijst van getallen."""
    if not getallen:
        return 1
    result = abs(getallen[0])
    for n in getallen[1:]:
        result = _kgv(result, abs(n))
    return result


def _verzamel_breuk_inputs(node):
    """
    Verzamel alle breuk-inputs (NUMBER met denominator > 1, of FRACTION) van een
    optel-operatie. Bij MANIFOLD_OP geeft dit alle operanden, bij BINARY_OP de
    twee operanden.

    Returns lijst van tuples (teller, noemer, label_string).
    """
    breuken = []
    operanden = []

    t = node.get('type')
    if t == 'BINARY_OP' and node.get('operator') == '+':
        operanden = [node.get('left', {}), node.get('right', {})]
    elif t == 'MANIFOLD_OP' and node.get('operator') == '+':
        operanden = node.get('operands', [])
    else:
        return breuken

    for op in operanden:
        ot = op.get('type')
        neg = op.get('is_negative', False)
        if ot == 'FRACTION':
            num = op.get('numerator', 0)
            den = op.get('denominator', 1)
            if neg:
                num = -num
            label = f"-{abs(num)}/{den}" if neg else f"{num}/{den}"
            breuken.append((num, den, label))
        elif ot == 'NUMBER':
            v = op.get('value', 0)
            if neg:
                v = -v
            # Geheel getal als breuk: v/1
            label = str(v)
            breuken.append((v, 1, label))
        else:
            # Operatie-node: gebruik de geëvalueerde uitkomst (als breuk)
            from ast_visualizer import evaluate
            val = evaluate(op)
            if val is not None:
                t_val = val.numerator
                n_val = val.denominator
                label = f"{t_val}/{n_val}" if n_val != 1 else str(t_val)
                breuken.append((t_val, n_val, label))

    return breuken


def _gelijknamig_maken_info(node):
    """
    Bouw gelijknamig_maken-info voor een optel-mathblock.

    Returns OrderedDict of None als er geen breuken zijn of geen gelijknamig
    maken nodig is.
    """
    breuken = _verzamel_breuk_inputs(node)
    if not breuken:
        return None

    # Tellers/noemers verzamelen
    noemers = [n for (_, n, _) in breuken]

    # Als alle noemers gelijk zijn (en er is minstens één breuk-noemer > 1),
    # is gelijknamig maken niet nodig
    unieke_noemers = set(noemers)
    aantal_breuken_echt = sum(1 for n in noemers if n > 1)

    info = OrderedDict()

    # Geen echte breuken: niet relevant
    if aantal_breuken_echt < 1:
        return None

    # Slechts één echte breuk: gelijknamig maken niet nodig
    # (gehele getallen kunnen we eenvoudig optellen bij de eind-breuk)
    if aantal_breuken_echt < 2:
        info['nodig'] = False
        info['reden'] = 'Slechts één breuk; gelijknamig maken niet nodig.'
        return info

    # Alle noemers gelijk: niet nodig
    if len(unieke_noemers) == 1:
        info['nodig'] = False
        info['reden'] = 'Alle noemers zijn al gelijk.'
        info['gemeenschappelijke_noemer'] = list(unieke_noemers)[0]
        return info

    # Wel nodig: bereken KGV
    kgv = _kgv_lijst([n for n in noemers if n > 1])
    breuken_gelijknamig = []
    for (t, n, _) in breuken:
        if n == 0:
            breuken_gelijknamig.append('?')
            continue
        factor = kgv // n if n > 0 else kgv
        nieuwe_teller = t * factor
        breuken_gelijknamig.append(f"{nieuwe_teller}/{kgv}")

    info['nodig'] = True
    info['kgv'] = kgv
    info['noemers'] = noemers
    info['breuken_origineel'] = [label for (_, _, label) in breuken]
    info['breuken_gelijknamig'] = breuken_gelijknamig
    info['efficientie'] = OrderedDict([
        ('aanbevolen_methode', 'KGV'),
        ('reden', f'Gebruik KGV ({kgv}) als gemeenschappelijke noemer; geeft kleinere getallen dan productnoemer.'),
        ('alternatief', 'Productnoemer (vermenigvuldig alle noemers) — werkt ook, maar geeft grotere tussenwaarden die nog vereenvoudigd moeten worden.'),
    ])

    return info


def _gemengd_getal_info_tussen(node, parent_node):
    """
    Bouw gemengd_getal-info voor een TUSSEN-uitkomst (niet einduitkomst).

    Returns OrderedDict of None.
    """
    val = evaluate(node)
    if val is None:
        return None
    if val.denominator == 1:
        return None
    if not _is_oneigenlijke_breuk(val):
        return None

    info = OrderedDict()
    info['mogelijk'] = True
    info['waarde'] = _naar_gemengd_getal(val)

    # Efficiëntie: hangt af van wat de parent is
    pt = parent_node.get('type') if parent_node else None
    eff = OrderedDict()

    if pt is None:
        eff['aanbevolen'] = True
        eff['reden'] = 'einduitkomst: gemengd getal is gewenste vorm'
    elif pt == 'BINARY_OP':
        op = parent_node.get('operator')
        if op == '+':
            eff['aanbevolen'] = False
            eff['reden'] = 'volgende stap is optelling; gemengd getal maakt gelijknamig maken lastiger'
        elif op == '×':
            eff['aanbevolen'] = False
            eff['reden'] = 'volgende stap is vermenigvuldiging; breuk-vorm is makkelijker te vermenigvuldigen'
        elif op == ':':
            eff['aanbevolen'] = False
            eff['reden'] = 'volgende stap is deling; breuk-vorm is makkelijker'
        else:
            eff['aanbevolen'] = False
            eff['reden'] = 'tussenresultaat: gemengd getal is meestal niet handig onderweg'
    elif pt == 'MANIFOLD_OP':
        op = parent_node.get('operator')
        if op == '+':
            eff['aanbevolen'] = False
            eff['reden'] = 'volgende stap is optel-manifold; breuk-vorm vereenvoudigt KGV-berekening'
        else:
            eff['aanbevolen'] = False
            eff['reden'] = 'volgende stap is vermenigvuldig-manifold; breuk-vorm is makkelijker'
    elif pt == 'POWER':
        eff['aanbevolen'] = False
        eff['reden'] = 'volgende stap is machtsverheffen; breuk-vorm is makkelijker te machten'
    elif pt == 'ROOT':
        eff['aanbevolen'] = False
        eff['reden'] = 'volgende stap is worteltrekken; breuk-vorm is makkelijker'
    elif pt == 'SIMPLIFY_OP':
        eff['aanbevolen'] = False
        eff['reden'] = 'volgende stap is vereenvoudigen; doe dat eerst, dan eventueel gemengd maken'
    elif pt == 'MATROESJKA_OP':
        eff['aanbevolen'] = False
        eff['reden'] = 'volgende stap is Matroesjka-bewerking; breuk-vorm is makkelijker'
    else:
        eff['aanbevolen'] = False
        eff['reden'] = 'tussenresultaat: doorgaans onhandig om gemengd te maken'

    info['efficientie'] = eff
    return info


def _is_oneigenlijke_breuk(val):
    """
    Een breuk is oneigenlijk als |teller| >= noemer (en het is geen geheel getal).
    val is een Fraction.
    """
    if val is None:
        return False
    if val.denominator == 1:
        return False  # Geen breuk
    return abs(val.numerator) >= val.denominator


def _naar_gemengd_getal(val):
    """
    Converteer een oneigenlijke breuk naar een gemengd getal.
    Returns string "a b/c" waarbij a het gehele deel is en b/c de rest.
    
    Voorbeelden:
        7/3   → "2 1/3"
        -7/3  → "-2 1/3"
        4/4   → "1" (geen breuk meer)
        8/4   → "2" (geen breuk meer)
    """
    if val is None or val.denominator == 1:
        return str(val.numerator) if val else '?'
    
    num = val.numerator
    den = val.denominator
    negatief = num < 0
    num = abs(num)
    
    geheel = num // den
    rest = num % den
    
    if rest == 0:
        # Geen breuk meer over
        return f"-{geheel}" if negatief else str(geheel)
    
    if geheel == 0:
        # Dit is eigenlijk geen oneigenlijke breuk, maar voor de zekerheid
        return f"-{rest}/{den}" if negatief else f"{rest}/{den}"
    
    teken = "-" if negatief else ""
    return f"{teken}{geheel} {rest}/{den}"


def _ggd(a, b):
    """Grootste gemeenschappelijke deler via Euclides."""
    a, b = abs(a), abs(b)
    while b:
        a, b = b, a % b
    return a


def _is_vereenvoudigbaar_ruw(teller, noemer):
    """
    Controleer of teller/noemer vereenvoudigd kan worden (GGD > 1).
    Werkt op ruwe teller/noemer paar, NIET op een Fraction (die is al vereenvoudigd).
    """
    if noemer == 0:
        return False
    return _ggd(teller, noemer) > 1


def _eindverwerking_info(val):
    """
    Bouw eindverwerking-info voor de einduitkomst van een opgave.
    
    Geval 1: oneigenlijke breuk → gemengd getal
    Geval 2: eigenlijke breuk, vereenvoudigbaar → GGD delen
    
    Let op: omdat Python's Fraction altijd al vereenvoudigd is, is geval 2
    op de EINDuitkomst van evaluate() nooit van toepassing — de Fraction
    is al maximaal vereenvoudigd. Geval 2 komt alleen voor bij
    tussenresultaten of ruwe teller/noemer paren.
    
    Returns OrderedDict of None als er geen eindverwerking nodig is.
    """
    if val is None:
        return None
    
    # Geheel getal — geen eindverwerking nodig
    if val.denominator == 1:
        return None
    
    # Eigenlijke breuk die al maximaal vereenvoudigd is — ook geen eindverwerking nodig
    # (Fraction is altijd al vereenvoudigd)
    if not _is_oneigenlijke_breuk(val):
        return None
    
    # Oneigenlijke breuk: geval 1
    info = OrderedDict()
    info['oneigenlijk'] = True
    info['gemengd_getal'] = _naar_gemengd_getal(val)
    info['vereenvoudigbaar'] = False  # Fraction is al vereenvoudigd
    info['ggd'] = 1
    
    return info


# ─── Hoofd-functie ──────────────────────────────────────────────────────────

def generate_formath_json(converted_ast, latex, mathml='',
                          latex_display=None, expression=None):
    """
    Genereer uitgebreide forMath JSON en sla op in OUTPUT_DIR.

    Args:
        converted_ast:  AST na manifold_converter
        latex:          ascii-math expressie (verwerkt door pipeline)
        mathml:         MathML representatie van de expressie
        latex_display:  LaTeX string van MathLive voor weergave in studenttool
                        (met \frac{}{}, : etc. correct genoteerd)
        expression:     platte expressie string na latex_to_expression()

    Returns:
        (json_dict, filepath)
    """
    # Fallbacks
    if latex_display is None:
        latex_display = latex
    if expression is None:
        expression = latex
    # output_dir = root van de opslag (voor zoeken naar bestaande IDs).
    # write_dir = sub-folder waar nieuwe opgaven naartoe geschreven worden
    #             (op dit moment 'Trial', zie DEFAULT_WRITE_SUBFOLDER).
    output_dir = _current_output_dir()
    write_dir  = _current_write_dir()
    os.makedirs(write_dir, exist_ok=True)

    # 1. Verzamel alle nodes via depth-first traversal
    all_nodes = []
    _traverse(converted_ast, all_nodes)

    # 2. Splits operatie-nodes en externe inputs
    op_nodes = [n for n in all_nodes if n['is_operation']]
    ext_nodes = [n for n in all_nodes if not n['is_operation']]

    # 3. Ken block IDs toe via spatial layout (zelfde volgorde als SVG)
    _assign_block_ids_spatial(converted_ast, op_nodes)

    # 4. Node lookup voor relaties
    node_lookup = {n['py_id']: n for n in all_nodes}

    # 5. Bouw secties
    mathblocks = _build_mathblocks(op_nodes, node_lookup)
    externe_inputs = _build_externals(ext_nodes, node_lookup)
    steps = _build_steps(op_nodes)
    duo = _build_duo(op_nodes, node_lookup, converted_ast)
    bewerkingen = _count_operations(op_nodes)

    # 6. Genereer ID en metadata
    opgave_id = _generate_id()
    max_step = max(n['step'] for n in op_nodes) if op_nodes else 0

    # Expressie reconstructie
    from ast_normalizer import ast_to_string
    try:
        expressie_str = ast_to_string(converted_ast)
    except Exception:
        expressie_str = ''

    # 7. Bouw MathJSON AST met node_map
    ast_tree, ast_node_map = _build_mathjson_ast(converted_ast, op_nodes, node_lookup)

    result = OrderedDict([
        ('metadata', OrderedDict([
            ('id', opgave_id),
            ('auteur', 'H.N.Lensing'),
            ('expressie', OrderedDict([
                ('tekst', expression),
                ('latex_display', latex_display),
                ('mathml', mathml),
                ('ast', OrderedDict([
                    ('tree', ast_tree),
                    ('node_map', ast_node_map),
                ])),
            ])),
            ('aantal_mathblocks', len(op_nodes)),
            ('bewerkingen', bewerkingen),
            ('aantal_steps', max_step),
            ('niveau', 'Hoog'),
        ])),
        ('mathblocks', mathblocks),
        ('externe_inputs', externe_inputs),
        ('steps', steps),
        ('duo_verzameling', duo),
    ])

    # Opslaan (in de write_dir, niet in de root output_dir)
    filename = f"opgave_{opgave_id}.json"
    filepath = os.path.join(write_dir, filename)
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(result, f, indent=2, ensure_ascii=False)

    return result, filepath


# ─── AST Traversal ──────────────────────────────────────────────────────────

def _traverse(node, result, order_counter=None):
    """Depth-first traversal, verzamelt info over elke node."""
    if order_counter is None:
        order_counter = [0]

    t = node.get('type')
    is_op = t in ('BINARY_OP', 'MANIFOLD_OP', 'POWER', 'ROOT', 'MATROESJKA_OP', 'SIMPLIFY_OP', 'MIXED_NUMBER_OP')

    info = {
        'py_id': id(node),
        'node': node,
        'type': t,
        'is_operation': is_op,
        'step': compute_node_depth(node),
        'order': order_counter[0],
        'block_id': None,
        'children_py_ids': [],
    }
    order_counter[0] += 1
    result.append(info)

    # Recursie naar kinderen
    if t == 'BINARY_OP':
        for child in [node.get('left'), node.get('right')]:
            if child:
                info['children_py_ids'].append(id(child))
                _traverse(child, result, order_counter)
    elif t == 'MANIFOLD_OP':
        for operand in node.get('operands', []):
            info['children_py_ids'].append(id(operand))
            _traverse(operand, result, order_counter)
    elif t == 'POWER':
        base = node.get('base')
        if base:
            info['children_py_ids'].append(id(base))
            _traverse(base, result, order_counter)
    elif t == 'ROOT':
        radicand = node.get('radicand')
        if radicand:
            info['children_py_ids'].append(id(radicand))
            _traverse(radicand, result, order_counter)
    elif t == 'MATROESJKA_OP':
        for i, shell in enumerate(node.get('shells', [])):
            if i == 0:
                left = shell.get('left')
                if left:
                    info['children_py_ids'].append(id(left))
                    _traverse(left, result, order_counter)
            right = shell.get('right')
            if right:
                info['children_py_ids'].append(id(right))
                _traverse(right, result, order_counter)
    elif t == 'SIMPLIFY_OP':
        source = node.get('source')
        if source:
            info['children_py_ids'].append(id(source))
            _traverse(source, result, order_counter)
    elif t == 'MIXED_NUMBER_OP':
        source = node.get('source')
        if source:
            info['children_py_ids'].append(id(source))
            _traverse(source, result, order_counter)


# ─── Block ID toewijzing ────────────────────────────────────────────────────

def _assign_block_ids_spatial(converted_ast, op_nodes):
    """
    Ken block IDs toe op basis van spatial layout (x-positie),
    exact dezelfde volgorde als de SVG visualizer.
    Werkt ook de step-waarde bij zodat deze overeenkomt met het block ID.
    """
    from ast_visualizer import compute_layout, assign_block_ids, compute_node_depth

    # Bereken layout en block IDs via de visualizer
    max_depth = compute_node_depth(converted_ast)
    layout_root, _ = compute_layout(converted_ast)
    block_ids = assign_block_ids(layout_root, max_depth)  # dict: id(node) → "A1"

    # Koppel block IDs aan op_nodes via py_id (= id(node))
    for n in op_nodes:
        bid = block_ids.get(n['py_id'])
        if bid:
            n['block_id'] = bid
            # Extraheer step uit block ID (bijv. "A2" → 2, "B12" → 12)
            import re as _re
            m = _re.search(r'(\d+)$', bid)
            if m:
                n['step'] = int(m.group(1))
        else:
            # Fallback: zou niet moeten voorkomen
            n['block_id'] = f"?{n['step']}"


# ─── Operatie info ──────────────────────────────────────────────────────────

def _get_operation_info(node):
    """Geeft operatie symbool en beschrijving voor een operatie-node."""
    t = node.get('type')
    neg = node.get('is_negative', False)

    if t == 'BINARY_OP':
        op = node.get('operator', '?')
        descriptions = {'+': 'optelling', '×': 'vermenigvuldiging', ':': 'deling'}
        symbool = f"-({op})" if neg else op
        return OrderedDict([
            ('symbool', symbool),
            ('beschrijving', descriptions.get(op, op)),
        ])

    elif t == 'MANIFOLD_OP':
        op = node.get('operator', '?')
        n = node.get('operand_count', len(node.get('operands', [])))
        descriptions = {'+': 'optel-manifold', '×': 'vermenigvuldig-manifold'}
        symbool = f"-M{op}({n})" if neg else f"M{op}({n})"
        return OrderedDict([
            ('symbool', symbool),
            ('beschrijving', descriptions.get(op, f'{op}-manifold')),
            ('aantal_operanden', n),
        ])

    elif t == 'POWER':
        exp = node.get('exponent', {})
        exp_val = exp.get('value', '?') if exp.get('type') == 'NUMBER' else '?'
        symbool = f"^{exp_val}"
        if neg:
            symbool = f"-({symbool})"
        return OrderedDict([
            ('symbool', symbool),
            ('beschrijving', 'machtsverheffen'),
            ('exponent', exp_val),
        ])

    elif t == 'ROOT':
        idx = node.get('index', {})
        idx_val = idx.get('value', '?') if idx.get('type') == 'NUMBER' else '?'
        symbool = "√" if str(idx_val) == "2" else f"√{idx_val}"
        if neg:
            symbool = f"-({symbool})"
        return OrderedDict([
            ('symbool', symbool),
            ('beschrijving', 'worteltrekken'),
            ('index', idx_val),
        ])

    elif t == 'MATROESJKA_OP':
        n_shells = node.get('shell_count', len(node.get('shells', [])))
        # Operators in de keten samenvatten
        ops = [s['operator'] for s in node.get('shells', [])]
        ops_str = ':'.join(o if o == ':' else 'x' for o in ops)
        symbool = f"-Mtr({n_shells})" if neg else f"Mtr({n_shells})"
        return OrderedDict([
            ('symbool', symbool),
            ('beschrijving', 'matroesjka-manifold'),
            ('aantal_schillen', n_shells),
            ('operatoren', ops),
        ])

    elif t == 'SIMPLIFY_OP':
        # Vereenvoudigen: breuk delen door GGD
        ggd_val = node.get('ggd', '?')
        return OrderedDict([
            ('symbool', '÷GGD'),
            ('beschrijving', 'vereenvoudigen'),
            ('ggd', ggd_val),
        ])

    elif t == 'MIXED_NUMBER_OP':
        # Gemengd getal: oneigenlijke breuk omzetten naar geheel + breuk
        gm = node.get('gemengd', {}) or {}
        return OrderedDict([
            ('symbool', 'GG'),
            ('beschrijving', 'gemengd getal'),
            ('geheel', gm.get('geheel', 0)),
            ('teller', gm.get('teller', 0)),
            ('noemer', gm.get('noemer', 1)),
        ])

    return OrderedDict([('symbool', '?'), ('beschrijving', 'onbekend')])


def _format_node_value(node):
    """Formatteer de waarde van een leaf node."""
    t = node.get('type')
    neg = node.get('is_negative', False)

    if t == 'NUMBER':
        v = node.get('value', 0)
        return f"-{v}" if neg else str(v)
    elif t == 'FRACTION':
        num = node.get('numerator', 0)
        den = node.get('denominator', 1)
        f = f"{num}/{den}"
        return f"-{f}" if neg else f
    return '?'


# ─── Mathblocks lijst ───────────────────────────────────────────────────────

def _build_mathblocks(op_nodes, node_lookup):
    """Bouw de geordende mathblocks lijst."""
    mathblocks = []

    # Bepaal welke nodes de 'source' zijn van een SIMPLIFY_OP.
    # Deze nodes krijgen hun RUWE uitkomst als output (i.p.v. de
    # automatisch vereenvoudigde Fraction).
    _simplify_source_ids = set()
    for n in op_nodes:
        if n['node'].get('type') == 'SIMPLIFY_OP':
            src = n['node'].get('source')
            if src is not None:
                _simplify_source_ids.add(id(src))

    # Parent lookup: voor elke operatie-node welk node is de parent
    _parent_lookup = {}
    for n in op_nodes:
        for child_pyid in n['children_py_ids']:
            _parent_lookup[child_pyid] = n

    # Bepaal welk mathblock de root is (hoogste stap, laagste order)
    # Dat is de einduitkomst van de opgave
    sorted_ops = sorted(op_nodes, key=lambda x: (x['step'], x['order']))
    root_mathblock = sorted_ops[-1] if sorted_ops else None

    for n in sorted_ops:
        node = n['node']

        # Inputs
        inputs = []
        for child_py_id in n['children_py_ids']:
            child_info = node_lookup.get(child_py_id)
            if child_info is None:
                continue

            if child_info['is_operation']:
                input_entry = OrderedDict([
                    ('type', 'mathblock'),
                    ('id', child_info['block_id']),
                ])
                if child_info['node'].get('is_negative'):
                    input_entry['is_negative'] = True
            else:
                input_entry = OrderedDict([
                    ('type', 'extern'),
                    ('waarde', _format_node_value(child_info['node'])),
                ])
            inputs.append(input_entry)

        # Output
        # Bij een SIMPLIFY_OP geven we de vereenvoudigde uitkomst als output,
        # en bij de source van een SIMPLIFY_OP geven we de RUWE uitkomst.
        # Bij MIXED_NUMBER_OP geven we het gemengde getal als output-string.
        # Bij andere nodes gebruiken we de normale evaluate().
        t_node = node.get('type')
        if t_node == 'SIMPLIFY_OP':
            verv = node.get('vereenvoudigd', {})
            vt, vn = verv.get('teller'), verv.get('noemer')
            if vn == 1:
                output_str = str(vt)
            else:
                output_str = f"{vt}/{vn}"
        elif t_node == 'MIXED_NUMBER_OP':
            gm = node.get('gemengd', {}) or {}
            geheel = gm.get('geheel', 0)
            mt = gm.get('teller', 0)
            mn = gm.get('noemer', 1)
            if mt == 0:
                output_str = str(geheel)
            else:
                output_str = f"{geheel}+{abs(mt)}/{mn}"
        elif n['py_id'] in _simplify_source_ids:
            # Deze node is de source van een SIMPLIFY_OP: toon ruwe output
            from ast_visualizer import evaluate_raw
            raw = evaluate_raw(node)
            if raw is not None:
                rt, rn = raw
                if rn == 1:
                    output_str = str(rt)
                else:
                    output_str = f"{rt}/{rn}"
            else:
                output_val = evaluate(node)
                output_str = format_result(output_val) if output_val is not None else '?'
        else:
            output_val = evaluate(node)
            output_str = format_result(output_val) if output_val is not None else '?'

        mb = OrderedDict([
            ('id', n['block_id']),
            ('step', n['step']),
            ('operatie', _get_operation_info(node)),
            ('input', inputs),
            ('output', output_str),
        ])

        # SIMPLIFY_OP krijgt een 'vereenvoudiging' veld met details
        if t_node == 'SIMPLIFY_OP':
            ruw = node.get('ruw', {})
            verv = node.get('vereenvoudigd', {})
            mb['vereenvoudiging'] = OrderedDict([
                ('van', f"{ruw.get('teller')}/{ruw.get('noemer')}"),
                ('naar', f"{verv.get('teller')}/{verv.get('noemer')}"),
                ('ggd', node.get('ggd', 1)),
            ])

        # MIXED_NUMBER_OP krijgt een 'gemengd_getal' veld met details
        if t_node == 'MIXED_NUMBER_OP':
            ruw = node.get('ruw', {})
            gm = node.get('gemengd', {}) or {}
            mt = gm.get('teller', 0)
            mn = gm.get('noemer', 1)
            geheel = gm.get('geheel', 0)
            mb['gemengd_getal'] = OrderedDict([
                ('van', f"{ruw.get('teller')}/{ruw.get('noemer')}"),
                ('naar', f"{geheel}" if mt == 0 else f"{geheel}+{abs(mt)}/{mn}"),
                ('geheel', geheel),
                ('teller', mt),
                ('noemer', mn),
            ])

            # Efficiëntie-aanbeveling
            from simplify_injector import analyze_simplify_efficiency
            parent = _parent_lookup.get(id(node))
            parent_node_obj = parent['node'] if parent else None
            eff = analyze_simplify_efficiency(node, parent_node_obj)
            mb['efficientie'] = OrderedDict([
                ('aanbevolen', eff.get('aanbevolen', True)),
                ('reden', eff.get('reden', '')),
                ('score', eff.get('score', 0.7)),
            ])
            if 'alternatieven' in eff:
                mb['efficientie']['alternatieven'] = eff['alternatieven']

        if node.get('is_negative'):
            mb['is_negative'] = True

        # Gelijknamig maken (bij optellingen met breuken)
        t_check = node.get('type')
        is_optelling = (
            (t_check == 'BINARY_OP' and node.get('operator') == '+') or
            (t_check == 'MANIFOLD_OP' and node.get('operator') == '+')
        )
        if is_optelling:
            gn_info = _gelijknamig_maken_info(node)
            if gn_info is not None:
                mb['gelijknamig_maken'] = gn_info

        # Hints en feedback (Type 1 + 2 + placeholder Type 3)
        from hints_generator import generate_hints
        mb['hints'] = generate_hints(node, is_root=(n is root_mathblock))

        # Gemengd getal voor TUSSENUITKOMSTEN met oneigenlijke breuk.
        # Regels:
        # - NIET op het laatste mathblock (root); daarvoor gebruiken we 'eindverwerking'.
        # - NIET als de parent een SIMPLIFY_OP is; de "echte" uitkomst komt pas
        #   NA de vereenvoudiging, en het gemengd_getal veld komt dan op de SIMPLIFY_OP.
        # - De efficientie-aanbeveling gebruikt altijd de directe parent als
        #   "volgende stap".
        if n is not root_mathblock:
            parent = _parent_lookup.get(id(node))
            parent_node_obj = parent['node'] if parent else None

            # Niet genereren als parent een SIMPLIFY_OP of MIXED_NUMBER_OP is
            # (die krijgen zelf relevante velden)
            skip = (
                parent_node_obj is not None
                and parent_node_obj.get('type') in ('SIMPLIFY_OP', 'MIXED_NUMBER_OP')
            )
            if not skip:
                gg_info = _gemengd_getal_info_tussen(node, parent_node_obj)
                if gg_info is not None:
                    mb['gemengd_getal'] = gg_info

        # Eindverwerking: alleen voor het LAATSTE mathblock (root van de AST)
        # Dit is de einduitkomst van de opgave
        if n is root_mathblock:
            final_val = evaluate(node)
            if final_val is not None:
                eindverwerking = _eindverwerking_info(final_val)
                if eindverwerking is not None:
                    mb['eindverwerking'] = eindverwerking

        mathblocks.append(mb)

    return mathblocks


# ─── Externe inputs lijst ───────────────────────────────────────────────────

def _build_externals(ext_nodes, node_lookup):
    """Bouw de externe inputs lijst met verwijzingen naar mathblocks."""
    externals = []

    for n in ext_nodes:
        node = n['node']
        waarde = _format_node_value(node)

        # Vind welk(e) mathblock(s) deze input gebruiken
        parent_blocks = []
        for other in node_lookup.values():
            if n['py_id'] in other.get('children_py_ids', []):
                if other.get('block_id'):
                    parent_blocks.append(other['block_id'])

        externals.append(OrderedDict([
            ('waarde', waarde),
            ('mathblock_ids', parent_blocks),
        ]))

    return externals


# ─── Steps lijst ────────────────────────────────────────────────────────────

def _build_steps(op_nodes):
    """Bouw de steps lijst met mathblock IDs per step."""
    by_step = defaultdict(list)
    for n in op_nodes:
        by_step[n['step']].append(n)

    max_step = max(by_step.keys()) if by_step else 0
    steps = []
    for s in range(1, max_step + 1):
        block_ids = [n['block_id'] for n in sorted(by_step.get(s, []), key=lambda x: x['order'])]
        steps.append(OrderedDict([
            ('step', s),
            ('mathblocks', block_ids),
        ]))

    return steps


# ─── Expressie rendering per step ──────────────────────────────────────────

def _render_expression(node, computed_ids, _top_level=True):
    """
    Render de AST als leesbare expressie string.
    Nodes waarvan id(node) in computed_ids zit, worden vervangen door hun uitkomst.
    _top_level: True voor de root-aanroep (geen buitenste haakjes)
    """
    py_id = id(node)
    neg = node.get('is_negative', False)

    # Als deze node al berekend is → toon de uitkomst als getal
    if py_id in computed_ids:
        val = evaluate(node)
        result_str = format_result(val) if val is not None else '?'
        return result_str

    t = node.get('type')

    # Leaf nodes
    if t == 'NUMBER':
        v = str(node['value'])
        return f"-{v}" if neg else v

    if t == 'FRACTION':
        frac = f"{node['numerator']}/{node['denominator']}"
        return f"-{frac}" if neg else frac

    # POWER — base tussen haakjes als het zelf een operatie is
    if t == 'POWER':
        base_node = node.get('base', {})
        base_str = _render_expression(base_node, computed_ids, _top_level=False)
        base_t = base_node.get('type')
        # Haakjes rond base alleen als het een POWER is (disambiguatie a^b^c)
        # BINARY_OP en MANIFOLD_OP hebben al hun eigen haakjes
        if base_t == 'POWER' and id(base_node) not in computed_ids:
            base_str = f"({base_str})"
        exp = node.get('exponent', {})
        exp_val = exp.get('value', '?') if exp.get('type') == 'NUMBER' else '?'
        inner = f"{base_str}^{exp_val}"
        return f"-({inner})" if neg else inner

    # ROOT — wortel met radicand als kind
    if t == 'ROOT':
        radicand_node = node.get('radicand', {})
        radicand_str = _render_expression(radicand_node, computed_ids, _top_level=False)
        idx = node.get('index', {})
        idx_val = idx.get('value', '?') if idx.get('type') == 'NUMBER' else '?'
        if str(idx_val) == '2':
            inner = f"√({radicand_str})"
        else:
            inner = f"√{idx_val}({radicand_str})"
        return f"-({inner})" if neg else inner

    # BINARY_OP
    if t == 'BINARY_OP':
        op = node.get('operator', '+')
        left_str = _render_expression(node.get('left', {}), computed_ids, _top_level=False)
        right_node = node.get('right', {})
        right_str = _render_expression(right_node, computed_ids, _top_level=False)

        # Als right negatief is en operator is +, dan left+(-right) → left-right
        right_neg = right_node.get('is_negative', False) and id(right_node) not in computed_ids
        if right_neg and op == '+':
            inner = f"{left_str}{right_str}"
        else:
            inner = f"{left_str}{op}{right_str}"

        if neg:
            return f"-({inner})"
        return inner if _top_level else f"({inner})"

    # MANIFOLD_OP
    if t == 'MANIFOLD_OP':
        op_sym = node.get('operator', '+')
        parts = []
        for operand in node.get('operands', []):
            part = _render_expression(operand, computed_ids, _top_level=False)
            parts.append(part)

        # Join met operator, rekening houdend met negatieve operanden
        if op_sym == '+':
            result_parts = [parts[0]]
            for i, operand in enumerate(node.get('operands', [])[1:], 1):
                op_neg = operand.get('is_negative', False) and id(operand) not in computed_ids
                if op_neg:
                    result_parts.append(parts[i])  # al met - prefix
                else:
                    result_parts.append(f"+{parts[i]}")
            inner = ''.join(result_parts)
        else:
            inner = f"{op_sym}".join(parts)

        if neg:
            return f"-({inner})"
        return inner if _top_level else f"({inner})"

    return '?'


# ─── DUO verzameling ────────────────────────────────────────────────────────

def _build_duo(op_nodes, node_lookup, converted_ast=None):
    """
    Bouw de DUO verzameling per step.

    Per step N:
    - Hoog (prioriteit): mathblocks die in deze step thuishoren
    - Laag (prioriteit): mathblocks uit hogere steps die DIRECT uitgevoerd
      kunnen worden omdat al hun operatie-inputs bij step ≤ N horen.
      Blokken die afhankelijk zijn van ANDERE laag-blokken worden NIET
      opgenomen — die blijven geblokkeerd.
    - input_expressie: expressie aan het begin van deze step
      (alleen hoog-blocks van vorige steps als berekend)
    - output_high: expressie na uitvoering van alleen High bewerkingen
    - output_high_low: expressie na uitvoering van High + Low bewerkingen
    """
    by_step = defaultdict(list)
    for n in op_nodes:
        by_step[n['step']].append(n)

    # Lookup: block_id → py_id en py_id → info
    bid_to_pyid = {n['block_id']: n['py_id'] for n in op_nodes}
    pyid_to_info = {n['py_id']: n for n in op_nodes}

    max_step = max(by_step.keys()) if by_step else 0
    duo = []

    # Running set: ALLEEN hoog-blocks (de "officiële" berekeningsvolgorde)
    # Laag-blocks worden NIET meegenomen naar de volgende step
    hoog_computed = set()

    for step in range(1, max_step + 1):
        hoog_bids = [n['block_id'] for n in sorted(by_step.get(step, []), key=lambda x: x['order'])]

        # ── Stap 1: Zoek kandidaat-laag-blocks ──
        # Een block is kandidaat als AL zijn operatie-kinderen step < N hebben
        # (strikt kleiner dan: inputs moeten in EERDERE steps berekend zijn,
        #  niet in de huidige step — anders is het block nog niet vrij)
        laag_candidates = []
        for n in op_nodes:
            if n['step'] <= step:
                continue

            all_available = True
            for child_py_id in n['children_py_ids']:
                child = node_lookup.get(child_py_id)
                if child and child['is_operation']:
                    if child['step'] >= step:
                        all_available = False
                        break

            if all_available:
                laag_candidates.append(n)

        # ── Stap 2: Filter — blokkeer blocks die afhankelijk zijn van
        #    andere laag-kandidaten (voorkomen van "ketens") ──
        laag_pyids = {n['py_id'] for n in laag_candidates}
        laag_bids = []
        for n in laag_candidates:
            depends_on_laag = False
            for child_py_id in n['children_py_ids']:
                if child_py_id in laag_pyids:
                    depends_on_laag = True
                    break
            if not depends_on_laag:
                laag_bids.append(n['block_id'])

        laag_bids = sorted(laag_bids)

        # ── Expressie rendering ──
        entry = OrderedDict([
            ('step', step),
            ('hoog', hoog_bids),
            ('laag', laag_bids),
        ])

        if converted_ast is not None:
            # Input: expressie vóór deze step
            # Alleen hoog-blocks van vorige steps zijn berekend
            input_expr = _render_expression(converted_ast, hoog_computed)

            # Na High: voeg hoog-blocks van DEZE step toe
            for bid in hoog_bids:
                pyid = bid_to_pyid.get(bid)
                if pyid:
                    hoog_computed.add(pyid)
            output_high = _render_expression(converted_ast, hoog_computed)

            # Na High+Low: TIJDELIJK laag-blocks toevoegen
            # (niet persistent — wordt niet meegenomen naar volgende step)
            temp_computed = set(hoog_computed)
            for bid in laag_bids:
                pyid = bid_to_pyid.get(bid)
                if pyid:
                    temp_computed.add(pyid)
            output_high_low = _render_expression(converted_ast, temp_computed)

            entry['input_expressie'] = input_expr
            entry['output_high'] = output_high
            entry['output_high_low'] = output_high_low

        duo.append(entry)

    return duo


# ─── Bewerkingen tellen ─────────────────────────────────────────────────────

def _count_operations(op_nodes):
    """Tel het aantal bewerkingen per soort mathblock."""
    counts = defaultdict(int)

    for n in op_nodes:
        node = n['node']
        t = node.get('type')

        if t == 'BINARY_OP':
            op = node.get('operator', '?')
            if op == '+':
                counts['optelling'] += 1
            elif op == '×':
                counts['vermenigvuldiging'] += 1
            elif op == ':':
                counts['deling'] += 1
        elif t == 'MANIFOLD_OP':
            op = node.get('operator', '?')
            if op == '+':
                counts['optel_manifold'] += 1
            elif op == '×':
                counts['vermenigvuldig_manifold'] += 1
        elif t == 'POWER':
            counts['machtsverheffen'] += 1
        elif t == 'ROOT':
            counts['worteltrekken'] += 1
        elif t == 'MATROESJKA_OP':
            counts['matroesjka_manifold'] += 1
        elif t == 'SIMPLIFY_OP':
            counts['vereenvoudigen'] += 1
        elif t == 'MIXED_NUMBER_OP':
            counts['gemengd_getal'] += 1

    return OrderedDict([
        ('optelling', counts.get('optelling', 0)),
        ('vermenigvuldiging', counts.get('vermenigvuldiging', 0)),
        ('deling', counts.get('deling', 0)),
        ('machtsverheffen', counts.get('machtsverheffen', 0)),
        ('worteltrekken', counts.get('worteltrekken', 0)),
        ('optel_manifold', counts.get('optel_manifold', 0)),
        ('vermenigvuldig_manifold', counts.get('vermenigvuldig_manifold', 0)),
        ('matroesjka_manifold', counts.get('matroesjka_manifold', 0)),
        ('vereenvoudigen', counts.get('vereenvoudigen', 0)),
        ('gemengd_getal', counts.get('gemengd_getal', 0)),
    ])


# ─── MathJSON AST generatie ────────────────────────────────────────────────

def _build_mathjson_ast(converted_ast, op_nodes, node_lookup):
    """
    Bouw een MathJSON AST (niet-vereenvoudigd) vanuit de interne AST,
    plus een node_map die elk pad koppelt aan een mathblock_id.

    Returns:
        (tree, node_map) waar:
        - tree: MathJSON structuur (geneste arrays/waarden)
        - node_map: lijst van {path, mathblock_id, type, waarde?}
    """
    # Lookup: py_id → block_id
    pyid_to_bid = {}
    for n in op_nodes:
        pyid_to_bid[n['py_id']] = n['block_id']

    # Lookup: py_id → node_info (voor externe inputs → parent block)
    pyid_to_info = {n['py_id']: n for n in node_lookup.values()}

    node_map = []
    tree = _node_to_mathjson(converted_ast, [], pyid_to_bid, pyid_to_info, node_map)

    return tree, node_map


def _node_to_mathjson(node, path, pyid_to_bid, pyid_to_info, node_map):
    """
    Converteer een interne AST node recursief naar MathJSON formaat.
    Registreert elke node in de node_map met pad en mathblock_id.

    Args:
        node: interne AST node dict
        path: huidig pad als lijst van indices
        pyid_to_bid: dict py_id → block_id (voor operatie-nodes)
        pyid_to_info: dict py_id → node info
        node_map: output lijst voor pad→mathblock mapping
    """
    t = node.get('type')
    neg = node.get('is_negative', False)
    py_id = id(node)
    block_id = pyid_to_bid.get(py_id)

    # ── Leaf: NUMBER ──
    if t == 'NUMBER':
        val = node.get('value', 0)
        if neg:
            val = -abs(val)
        # Registreer in node_map
        _register_leaf(path, py_id, val, pyid_to_info, node_map)
        return val

    # ── Leaf: FRACTION ──
    if t == 'FRACTION':
        num = node.get('numerator', 0)
        den = node.get('denominator', 1)
        if neg:
            num = -abs(num)
        result = ["Rational", num, den]
        _register_leaf(path, py_id, f"{num}/{den}", pyid_to_info, node_map)
        return result

    # ── BINARY_OP ──
    if t == 'BINARY_OP':
        op = node.get('operator', '+')
        left = node.get('left')
        right = node.get('right')

        left_mj = _node_to_mathjson(left, path + [0], pyid_to_bid, pyid_to_info, node_map) if left else 0
        right_mj = _node_to_mathjson(right, path + [1], pyid_to_bid, pyid_to_info, node_map) if right else 0

        if op == '+':
            inner = ["Add", left_mj, right_mj]
        elif op == '×' or op == '*':
            inner = ["Multiply", left_mj, right_mj]
        elif op == ':' or op == '/':
            inner = ["Divide", left_mj, right_mj]
        else:
            inner = ["Add", left_mj, right_mj]

        # Registreer operatie in node_map
        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))

        if neg:
            return ["Negate", inner]
        return inner

    # ── MANIFOLD_OP ──
    if t == 'MANIFOLD_OP':
        op = node.get('operator', '+')
        operands = node.get('operands', [])

        children_mj = []
        for i, operand in enumerate(operands):
            child_mj = _node_to_mathjson(operand, path + [i], pyid_to_bid, pyid_to_info, node_map)
            children_mj.append(child_mj)

        if op == '+':
            inner = ["Add"] + children_mj
        elif op == '×' or op == '*':
            inner = ["Multiply"] + children_mj
        else:
            inner = ["Add"] + children_mj

        # Registreer operatie in node_map
        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))

        if neg:
            return ["Negate", inner]
        return inner

    # ── POWER ──
    if t == 'POWER':
        base = node.get('base')
        exp = node.get('exponent', {})
        exp_val = exp.get('value', 2) if exp.get('type') == 'NUMBER' else 2

        base_mj = _node_to_mathjson(base, path + [0], pyid_to_bid, pyid_to_info, node_map) if base else 0

        inner = ["Power", base_mj, exp_val]

        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))

        if neg:
            return ["Negate", inner]
        return inner

    # ── ROOT ──
    if t == 'ROOT':
        radicand = node.get('radicand')
        idx = node.get('index', {})
        idx_val = idx.get('value', 2) if idx.get('type') == 'NUMBER' else 2

        radicand_mj = _node_to_mathjson(radicand, path + [0], pyid_to_bid, pyid_to_info, node_map) if radicand else 0

        if idx_val == 2:
            inner = ["Sqrt", radicand_mj]
        else:
            inner = ["Root", radicand_mj, idx_val]

        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))

        if neg:
            return ["Negate", inner]
        return inner

    # ── SIMPLIFY_OP ──
    # Vereenvoudig-wrapper. Hij voegt geen nieuwe operator toe aan de
    # MathJSON-boom — alleen een mathblock_id-koppeling in de node_map
    # zodat de studenttool weet op welk pad een vereenvoudig-stap zit.
    # We dalen recursief af in 'source' en retourneren diens MathJSON.
    if t == 'SIMPLIFY_OP':
        source = node.get('source')
        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))
        if source is None:
            return 0
        # Source krijgt HETZELFDE pad — SIMPLIFY_OP is doorzichtig.
        return _node_to_mathjson(source, path, pyid_to_bid,
                                 pyid_to_info, node_map)

    # ── MIXED_NUMBER_OP ──
    # Idem aan SIMPLIFY_OP: een wrapper rond 'source'.
    if t == 'MIXED_NUMBER_OP':
        source = node.get('source')
        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))
        if source is None:
            return 0
        return _node_to_mathjson(source, path, pyid_to_bid,
                                 pyid_to_info, node_map)

    # ── UNARY_OP ──
    # Bv. unaire min: '-(a+b)'. We wikkelen 'Negate' om de operand.
    if t == 'UNARY_OP':
        operand = node.get('operand')
        op = node.get('operator', '-')
        if operand is None:
            return 0
        operand_mj = _node_to_mathjson(operand, path + [0], pyid_to_bid,
                                       pyid_to_info, node_map)
        if op == '-':
            inner = ["Negate", operand_mj]
        else:
            # Onbekende unaire operator — laat als-is met operator-naam
            inner = [op, operand_mj]
        if block_id:
            node_map.append(OrderedDict([
                ('path', list(path)),
                ('mathblock_id', block_id),
                ('type', 'operation'),
            ]))
        if neg:
            return ["Negate", inner]
        return inner

    # Fallback — onbekend node-type. Print uitgebreide diagnose zodat we
    # kunnen zien WELKE types in de boom voorkomen die _node_to_mathjson
    # niet ondersteunt.
    print(f"[BUG][_node_to_mathjson] Onbekend node-type: {t!r}  path={path}  "
          f"node-keys={list(node.keys()) if isinstance(node, dict) else type(node).__name__}")
    return 0


def _register_leaf(path, py_id, waarde, pyid_to_info, node_map):
    """
    Registreer een leaf node (NUMBER of FRACTION) in de node_map.
    Zoekt het parent mathblock via pyid_to_info.
    """
    # Zoek welk mathblock deze leaf als input heeft
    parent_bid = None
    for info in pyid_to_info.values():
        if py_id in info.get('children_py_ids', []):
            if info.get('block_id'):
                parent_bid = info['block_id']
                break

    if parent_bid:
        node_map.append(OrderedDict([
            ('path', list(path)),
            ('mathblock_id', parent_bid),
            ('type', 'input'),
            ('waarde', str(waarde)),
        ]))


# ─── ID generatie ───────────────────────────────────────────────────────────

def _generate_id():
    """Genereer ID: YYYYMMDD_NNN (volgnummer per dag).

    Scant de hele opgaven-boom (alle sub-folders) zodat IDs uniek blijven
    ook wanneer opgaven verspreid over folders staan.
    """
    today = date.today()
    date_str = today.strftime('%Y%m%d')

    existing = []
    try:
        from folder_manager import list_all_opgaven
        root = _current_output_dir()
        for opg in list_all_opgaven(root):
            fname = os.path.basename(opg['path'])
            if fname.startswith(f'opgave_{date_str}_') and fname.endswith('.json'):
                try:
                    seq = int(fname.split('_')[2].split('.')[0])
                    existing.append(seq)
                except (IndexError, ValueError):
                    pass
    except ImportError:
        # Fallback: oude platte scan op de root (zonder folder_manager).
        output_dir = _current_output_dir()
        if os.path.exists(output_dir):
            for f in os.listdir(output_dir):
                if f.startswith(f'opgave_{date_str}_') and f.endswith('.json'):
                    try:
                        seq = int(f.split('_')[2].split('.')[0])
                        existing.append(seq)
                    except (IndexError, ValueError):
                        pass

    next_seq = max(existing) + 1 if existing else 1
    return f"{date_str}_{next_seq:03d}"
