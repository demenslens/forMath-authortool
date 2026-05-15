#!/usr/bin/env python3
"""
AST Visualizer - Staande boom weergave na manifold_converter
=============================================================

Visualiseert de AST(CLR) als een staande boom:
- Root bovenaan
- Leaves onderaan
- Kleur per node type
- Manifold nodes met vork-stijl weergave
"""

import xml.etree.ElementTree as ET
import sys
import os

sys.path.insert(0, os.path.dirname(__file__))

from expression_parser import parse_expression
from ast_normalizer import normalize_ast
from manifold_detector import detect_manifolds
from manifold_converter import convert_to_manifolds


# ─── Kleuren en stijl ────────────────────────────────────────────────────────

COLORS = {
    "BINARY_OP":    {"fill": "#D0E8FF", "stroke": "#2176AE", "text": "#0D3B66"},
    "MANIFOLD_OP":  {"fill": "#FFE8C0", "stroke": "#E07B00", "text": "#6B3A00"},
    "MATROESJKA_OP":{"fill": "#F9E0D9", "stroke": "#B8552D", "text": "#5A2815"},
    "SIMPLIFY_OP":  {"fill": "#E0F5E0", "stroke": "#2E7D32", "text": "#1B5E20"},
    "MIXED_NUMBER_OP":{"fill": "#EDE7F6", "stroke": "#5E35B1", "text": "#311B92"},  # paars
    "UNARY_OP":     {"fill": "#E8F5E9", "stroke": "#388E3C", "text": "#1B5E20"},  # groen
    "NUMBER":       {"fill": "#FFFFFF", "stroke": "#000000", "text": "#000000"},  # wit + zwart
    "FRACTION":     {"fill": "#FFFFFF", "stroke": "#000000", "text": "#000000"},  # wit + zwart
    "PARAMETER":    {"fill": "#FFFFFF", "stroke": "#000000", "text": "#000000"},  # wit + zwart (zoals NUMBER)
    "NEG_NUMBER":   {"fill": "#FDECEA", "stroke": "#C62828", "text": "#7F0000"},
    "NEG_FRACTION": {"fill": "#FDECEA", "stroke": "#C62828", "text": "#7F0000"},
    "NEG_OP":       {"fill": "#F3E5F5", "stroke": "#7B1FA2", "text": "#4A148C"},
}

# Rode rand voor mathBlocks die is_negative=True hebben (gecombineerd met unary)
NEG_MATHBLOCK_STROKE = "#C62828"

NODE_W = 90
NODE_H = 40
MANIFOLD_W = 90         # zelfde breedte als andere blocks
MANIFOLD_EXTRA_H = 16   # extra hoogte per extra operand boven 2
H_GAP = 24              # horizontale gap tussen nodes
V_GAP = 100             # verticale gap tussen levels
MARGIN = 40


# ─── Node label ──────────────────────────────────────────────────────────────

def node_label(node):
    t = node.get("type")
    neg = node.get("is_negative", False)
    if t == "NUMBER":
        v = str(node["value"])
        return f"-{v}" if neg else v
    if t == "FRACTION":
        f = f"{node['numerator']}/{node['denominator']}"
        return f"-{f}" if neg else f
    if t == "PARAMETER":
        n = node["name"]
        return f"-{n}" if neg else n
    if t == "BINARY_OP":
        op = node["operator"]
        return f"-({op})" if neg else op
    if t == "MANIFOLD_OP":
        op = node["operator"]
        n = node.get("operand_count", len(node.get("operands", [])))
        return f"-M{op}({n})" if neg else f"M{op}({n})"
    if t == "POWER":
        exp = node.get("exponent", {}).get("value", "?")
        return f"^{exp}"
    if t == "ROOT":
        idx = node.get("index", {}).get("value", 2)
        # Toon als "^1/2", "^1/3", "^1/4", etc. — exponent-notatie van wortel.
        return f"^1/{idx}"
    if t == "UNARY_OP":
        op = node.get("operator", "?")
        return f"-{op}" if neg else op
    if t == "SIMPLIFY_OP":
        # Hoofdlabel: alleen het deelteken centraal in het mathblock.
        # De GGD-waarde komt apart rechtsonder via draw_nodes().
        return "÷"
    if t == "MIXED_NUMBER_OP":
        # Hoofdlabel: gemengd getal "G+T/N" (in plaats van afkorting "GG").
        gm = node.get("gemengd", {}) or {}
        geheel = gm.get("geheel", 0)
        mt = gm.get("teller", 0)
        mn = gm.get("noemer", 1)
        if mt == 0:
            return str(geheel)
        # Toon als "G+T/N" (b.v. "2+11/12") — de plus maakt de optelling expliciet
        return f"{geheel}+{abs(mt)}/{mn}"
    if t == "MATROESJKA_OP":
        n = node.get("shell_count", len(node.get("shells", [])))
        return f"Mtr({n})"
    return t


def color_key(node):
    """Geeft de kleur-key voor de VULKLEUR van de node.
    Negatief heeft geen invloed op vulkleur — alleen op de rand (via stroke override).
    """
    t = node.get("type")
    if t in COLORS:
        return t
    return "BINARY_OP"


def node_width(node):
    """Breedte van een node bepalen op basis van type."""
    if node.get("type") == "MANIFOLD_OP":
        return MANIFOLD_W
    return NODE_W


# ─── Uitkomst berekening ─────────────────────────────────────────────────────

def evaluate(node):
    """
    Bereken de numerieke uitkomst van een node als Fraction voor exacte weergave.
    Geeft None terug als het niet berekenbaar is.
    """
    from fractions import Fraction
    t = node.get("type")
    neg = node.get("is_negative", False)

    try:
        if t == "NUMBER":
            val = Fraction(node["value"])
            return -val if neg else val

        if t == "FRACTION":
            val = Fraction(node["numerator"], node["denominator"])
            return -val if neg else val

        if t == "PARAMETER":
            # Een parameter heeft geen rationale waarde — voor letterrekenen
            # zal in een latere ronde een symbolische evaluator worden
            # toegevoegd. Tot dan: None propageert correct door de bestaande
            # pipeline (net zoals bij sqrt(2)).
            return None

        if t == "BINARY_OP":
            left = evaluate(node.get("left"))
            right = evaluate(node.get("right"))
            if left is None or right is None:
                return None
            op = node["operator"]
            if op == "+":
                result = left + right
            elif op == "×":
                result = left * right
            elif op == ":":
                if right == 0:
                    return None
                result = left / right
            else:
                return None
            return -result if neg else result

        if t == "POWER":
            base_val = evaluate(node.get("base", {}))
            exp_val = evaluate(node.get("exponent", {}))
            if base_val is None or exp_val is None:
                return None
            # Exponent moet een geheel getal zijn voor exacte berekening
            if exp_val.denominator != 1:
                return None
            exp_int = int(exp_val)
            if exp_int >= 0:
                result = base_val ** exp_int
            else:
                result = Fraction(1) / (base_val ** (-exp_int))
            return -result if neg else result

        if t == "ROOT":
            radicand_val = evaluate(node.get("radicand", {}))
            idx_val = evaluate(node.get("index", {}))
            if radicand_val is None or idx_val is None:
                return None
            if idx_val.denominator != 1:
                return None
            idx_int = int(idx_val)
            # Exacte wortel: controleer of radicand een perfecte n-de macht is
            # Alleen mogelijk voor positieve gehele getallen
            if radicand_val < 0 and idx_int % 2 == 0:
                return None  # Geen reële wortel van negatief getal
            # Probeer exacte wortel te berekenen
            from fractions import Fraction
            import math
            neg_radicand = radicand_val < 0
            abs_val = abs(radicand_val)
            # Werkt alleen voor Fraction met teller en noemer als perfecte machten
            num = abs_val.numerator
            den = abs_val.denominator
            num_root = round(num ** (1/idx_int))
            den_root = round(den ** (1/idx_int))
            if num_root ** idx_int == num and den_root ** idx_int == den:
                result = Fraction(num_root, den_root)
                if neg_radicand:
                    result = -result
                return -result if neg else result
            # Geen exacte wortel — als het radicand een grote breuk is (typisch
            # voor irrationale benaderingen zoals √π), bereken de wortel als
            # float en geef terug als Fraction (groot, wordt later afgerond).
            if den > 10000 or abs(num) > 100000:
                f = float(abs_val)
                root_f = f ** (1/idx_int)
                if neg_radicand:
                    root_f = -root_f
                # Cap: round to 10 decimal places om precision-noise te beperken
                result = Fraction(round(root_f, 10)).limit_denominator(10**10)
                return -result if neg else result
            return None  # Geen exacte wortel

        if t == "MANIFOLD_OP":
            op = node["operator"]
            total = None
            for operand in node.get("operands", []):
                val = evaluate(operand)
                if val is None:
                    return None
                if total is None:
                    total = val
                elif op == "×":
                    total = total * val
                else:
                    total = total + val
            if total is None:
                return None
            return -total if neg else total

        if t == "MATROESJKA_OP":
            shells = node.get("shells", [])
            if not shells:
                return None
            # Schil 1: left op right (twee initiële inputs)
            s0 = shells[0]
            left_val = evaluate(s0.get("left", {}))
            right_val = evaluate(s0.get("right", {}))
            if left_val is None or right_val is None:
                return None
            op0 = s0["operator"]
            result = left_val * right_val if op0 == "×" else (
                left_val / right_val if right_val != 0 else None)
            if result is None:
                return None
            # Schillen 2..n: result op right
            for shell in shells[1:]:
                right_val = evaluate(shell.get("right", {}))
                if right_val is None:
                    return None
                op = shell["operator"]
                if op == "×":
                    result = result * right_val
                elif op == ":":
                    if right_val == 0:
                        return None
                    result = result / right_val
            return -result if neg else result

        if t == "SIMPLIFY_OP":
            # Een SIMPLIFY_OP heeft één input (de bron-node) en geeft
            # de vereenvoudigde waarde terug. Omdat Fraction altijd al
            # vereenvoudigd is, is dit gelijk aan evaluate(source).
            source = node.get("source")
            if source is None:
                return None
            src_val = evaluate(source)
            if src_val is None:
                return None
            return -src_val if neg else src_val

        if t == "MIXED_NUMBER_OP":
            # MIXED_NUMBER_OP wikkelt de root in en heeft de oneigenlijke breuk
            # als source. De gemengd-getal-vorm is alleen visualisatie; de
            # numerieke waarde blijft hetzelfde.
            source = node.get("source")
            if source is None:
                return None
            src_val = evaluate(source)
            if src_val is None:
                return None
            return -src_val if neg else src_val

    except Exception:
        return None

    return None


def evaluate_raw(node):
    """
    Bereken de RUWE uitkomst van een node als tuple (teller, noemer).
    Geen automatische vereenvoudiging — de teller en noemer zijn zoals ze
    ontstaan uit directe arithmetiek op de inputs.

    Dit is nodig om te detecteren of een tussenuitkomst vereenvoudigbaar is.
    evaluate() gebruikt Fraction, die automatisch vereenvoudigt —
    evaluate_raw() behoudt de ruwe vorm.

    Returns:
        Tuple (teller, noemer) of None als niet berekenbaar.
        Teken zit in de teller.

    Voorbeelden:
        NUMBER(5)                       → (5, 1)
        FRACTION(3, 5)                  → (3, 5)
        BINARY_OP(× , 3/4, 8/9)        → (24, 36)   [NIET vereenvoudigd]
        BINARY_OP(: , 6, 4)            → (6, 4)    [NIET vereenvoudigd]
        BINARY_OP(+, 1/4, 1/6)         → (10, 24)  [via kruiselings: 6/24 + 4/24]
    """
    from fractions import Fraction
    t = node.get("type")
    neg = node.get("is_negative", False)

    try:
        if t == "NUMBER":
            v = node["value"]
            if neg:
                v = -v
            return (v, 1)

        if t == "PARAMETER":
            # Geen rationale (teller, noemer) representatie voor parameters.
            return None

        if t == "FRACTION":
            num = node["numerator"]
            den = node["denominator"]
            if neg:
                num = -num
            return (num, den)

        if t == "BINARY_OP":
            left = evaluate_raw(node.get("left"))
            right = evaluate_raw(node.get("right"))
            if left is None or right is None:
                return None
            ln, ld = left
            rn, rd = right
            op = node["operator"]

            if op == "×":
                # Kruiselings niets, gewoon teller * teller en noemer * noemer
                res = (ln * rn, ld * rd)
            elif op == ":":
                # a/b : c/d = a*d / b*c
                if rn == 0:
                    return None
                # Houd teken op de teller
                res_num = ln * rd
                res_den = ld * rn
                if res_den < 0:
                    res_num = -res_num
                    res_den = -res_den
                res = (res_num, res_den)
            elif op == "+":
                # a/b + c/d = (a*d + c*b) / (b*d) — RUWE optelling via productnoemer
                res_num = ln * rd + rn * ld
                res_den = ld * rd
                res = (res_num, res_den)
            else:
                return None

            if neg:
                res = (-res[0], res[1])
            return res

        if t == "POWER":
            base = evaluate_raw(node.get("base", {}))
            exp_val = evaluate(node.get("exponent", {}))
            if base is None or exp_val is None:
                return None
            if exp_val.denominator != 1:
                return None
            exp_int = int(exp_val)
            bn, bd = base
            if exp_int >= 0:
                res = (bn ** exp_int, bd ** exp_int)
            else:
                if bn == 0:
                    return None
                e = -exp_int
                res = (bd ** e, bn ** e)
                if res[1] < 0:
                    res = (-res[0], -res[1])
            if neg:
                res = (-res[0], res[1])
            return res

        if t == "MANIFOLD_OP":
            op = node["operator"]
            ops = node.get("operands", [])
            if not ops:
                return None
            total = evaluate_raw(ops[0])
            if total is None:
                return None
            for operand in ops[1:]:
                v = evaluate_raw(operand)
                if v is None:
                    return None
                ln, ld = total
                rn, rd = v
                if op == "×":
                    total = (ln * rn, ld * rd)
                else:  # +
                    total = (ln * rd + rn * ld, ld * rd)
            if neg:
                total = (-total[0], total[1])
            return total

        if t == "SIMPLIFY_OP":
            # SIMPLIFY_OP geeft de vereenvoudigde waarde terug als (teller, noemer)
            verv = node.get("vereenvoudigd")
            if verv is not None:
                return (verv.get("teller"), verv.get("noemer"))
            # Fallback: evaluate_raw van source
            return evaluate_raw(node.get("source", {}))

        if t == "MIXED_NUMBER_OP":
            # De numerieke waarde blijft de oneigenlijke breuk
            ruw = node.get("ruw")
            if ruw is not None:
                return (ruw.get("teller"), ruw.get("noemer"))
            return evaluate_raw(node.get("source", {}))

        # MATROESJKA_OP, ROOT: gebruik evaluate() als fallback
        val = evaluate(node)
        if val is None:
            return None
        return (val.numerator, val.denominator)

    except Exception:
        return None


def format_result(val):
    """Formatteer Fraction als leesbare string.

    Als de breuk een grote teller/noemer heeft (typisch bij irrationale
    benaderingen zoals π), tonen we 5 decimalen i.p.v. de letterlijke breuk.
    Drempel: noemer > 1000 én geen 'mooie' breuk.
    """
    if val is None:
        return ""
    from fractions import Fraction
    # Geheel getal
    if val.denominator == 1:
        return str(val.numerator)
    # Als de breuk gigantisch is, is het waarschijnlijk een irrationale
    # benadering (zoals π). Toon dan als float met 5 decimalen.
    if val.denominator > 10000 or abs(val.numerator) > 100000:
        f = float(val)
        # Afkappen naar 5 decimalen, maar trim trailing zeros voor leesbaarheid
        rounded = round(f, 5)
        if rounded == int(rounded):
            return str(int(rounded))
        return f"{rounded:.5f}".rstrip('0').rstrip('.')
    # Breuk: toon als a/b
    return f"{val.numerator}/{val.denominator}"


# ─── Step berekening ─────────────────────────────────────────────────────────

def is_wrapper_node(node):
    """
    Een wrapper-node is een negatief haakjesblok (is_negative=True én _bracketed=True).
    Wrappers zijn transparant voor stap-nummering (tellen niet als extra niveau),
    maar compute_node_depth telt ze wel voor correcte max_depth berekening.
    """
    return bool(node.get('is_negative') and node.get('_bracketed'))


def compute_node_depth(node):
    """Berekent de maximale diepte van een node (0 = leaf, N = root)."""
    t = node.get('type')
    if t in ('NUMBER', 'FRACTION', 'PARAMETER'):
        return 0
    if t == 'POWER':
        base_depth = compute_node_depth(node.get('base', {}))
        return 1 + base_depth
    if t == 'BINARY_OP':
        return 1 + max(compute_node_depth(node.get('left', {})), compute_node_depth(node.get('right', {})))
    if t == 'MANIFOLD_OP':
        ops = node.get('operands', [])
        if not ops: return 1
        return 1 + max(compute_node_depth(op) for op in ops)
    if t == 'MATROESJKA_OP':
        shells = node.get('shells', [])
        if not shells: return 1
        # Diepte = aantal schillen (elke schil is één niveau)
        # Plus de diepte van de inhoud van schil 1
        s0_left_depth = compute_node_depth(shells[0].get('left', {}))
        return len(shells) + s0_left_depth
    if t == 'SIMPLIFY_OP':
        # SIMPLIFY_OP is één stap bovenop zijn source
        source = node.get('source', {})
        return 1 + compute_node_depth(source)
    if t == 'MIXED_NUMBER_OP':
        # MIXED_NUMBER_OP is één stap bovenop zijn source
        source = node.get('source', {})
        return 1 + compute_node_depth(source)
    return 0


# ─── Expressie reconstructie voor bracketed nodes ────────────────────────────

def node_to_expr(node):
    """Reconstrueer een compacte expressiestring van een node (voor labels)."""
    t = node.get('type')
    neg = node.get('is_negative', False)
    prefix = '-' if neg else ''

    if t == 'NUMBER':
        return f"{prefix}{node['value']}"
    if t == 'FRACTION':
        return f"{prefix}{node['numerator']}/{node['denominator']}"
    if t == 'PARAMETER':
        return f"{prefix}{node['name']}"
    if t == 'BINARY_OP':
        op = node.get('operator', '+')
        left = node_to_expr(node.get('left', {}))
        right = node_to_expr(node.get('right', {}))
        # right heeft al zijn eigen prefix via is_negative
        inner = f"{left}{op}{right}" if not node.get('right', {}).get('is_negative') else f"{left}{right}"
        return f"{prefix}({inner})" if neg else f"({inner})"
    if t == 'MANIFOLD_OP':
        ops = node.get('operands', [])
        parts = []
        for op in ops:
            parts.append(node_to_expr(op))
        inner = '+'.join(parts)
        return f"{prefix}({inner})" if neg else f"({inner})"
    return '?'


# ─── MathBlock ID toewijzing ─────────────────────────────────────────────────

def assign_block_ids(layout_root, max_depth):
    """
    Wijs aan elke operatie-node een block ID toe: letter + stap-nummer.

    Stap-bepaling: top-down vanuit de root (root = max_depth).
    - Niet-wrapper: stap = incoming_step, kinderen krijgen incoming_step - 1
    - Wrapper (is_negative + _bracketed): stap = incoming_step (transparant voor
      eigen stap), kinderen krijgen ook incoming_step - 1

    Volgorde binnen een stap: x-positie in de layout (links → rechts).
    Geeft dict terug: id(node_dict) → block_id string
    """
    from collections import defaultdict

    # Stap 1: bereken stap per node (top-down)
    node_steps = {}

    def assign_steps(node, incoming_step):
        t = node.get('type')
        if t in ('NUMBER', 'FRACTION', 'PARAMETER', None): return
        node_steps[id(node)] = incoming_step
        child_step = incoming_step - 1
        if t == 'BINARY_OP':
            assign_steps(node.get('left', {}), child_step)
            assign_steps(node.get('right', {}), child_step)
        elif t == 'MANIFOLD_OP':
            for op in node.get('operands', []):
                assign_steps(op, child_step)
        elif t == 'POWER':
            assign_steps(node.get('base', {}), child_step)
        elif t == 'MATROESJKA_OP':
            # Elke schil is één stap dieper; schil 1 left is het diepst
            shells = node.get('shells', [])
            for i, shell in enumerate(shells):
                shell_step = incoming_step - (len(shells) - i)
                if i == 0:
                    assign_steps(shell.get('left', {}), shell_step - 1)
                assign_steps(shell.get('right', {}), shell_step - 1)
        elif t == 'SIMPLIFY_OP':
            # SIMPLIFY_OP heeft één child: source
            assign_steps(node.get('source', {}), child_step)
        elif t == 'MIXED_NUMBER_OP':
            # MIXED_NUMBER_OP heeft één child: source
            assign_steps(node.get('source', {}), child_step)

    assign_steps(layout_root['node'], max_depth)

    # Stap 2: bouw map id(node) → x-positie uit de layout
    x_pos = {}

    def collect_x(info):
        x_pos[id(info['node'])] = info['x']
        for child in info['children']:
            collect_x(child)

    collect_x(layout_root)

    # Stap 3: verzamel alle operatie-nodes
    all_nodes = []

    def collect_nodes(node):
        t = node.get('type')
        if t in ('NUMBER', 'FRACTION', 'PARAMETER'): return
        all_nodes.append(node)
        if t == 'BINARY_OP':
            collect_nodes(node.get('left', {}))
            collect_nodes(node.get('right', {}))
        elif t == 'MANIFOLD_OP':
            for op in node.get('operands', []):
                collect_nodes(op)
        elif t == 'POWER':
            collect_nodes(node.get('base', {}))
        elif t == 'MATROESJKA_OP':
            shells = node.get('shells', [])
            for i, shell in enumerate(shells):
                if i == 0:
                    collect_nodes(shell.get('left', {}))
                collect_nodes(shell.get('right', {}))
        elif t == 'SIMPLIFY_OP':
            collect_nodes(node.get('source', {}))
        elif t == 'MIXED_NUMBER_OP':
            collect_nodes(node.get('source', {}))

    collect_nodes(layout_root['node'])

    # Stap 4: groepeer per stap en sorteer op x-positie
    by_step = defaultdict(list)
    for node in all_nodes:
        step = node_steps.get(id(node), 0)
        by_step[step].append(node)

    for step in by_step:
        by_step[step].sort(key=lambda n: x_pos.get(id(n), 0))

    # Stap 5: letters toewijzen
    letters = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'
    block_ids = {}
    for step in sorted(by_step.keys()):
        for i, node in enumerate(by_step[step]):
            letter = letters[i] if i < len(letters) else f"N{i}"
            block_ids[id(node)] = f"{letter}{step}"

    return block_ids

# ─── Layout berekening ───────────────────────────────────────────────────────

def compute_layout(node, depth=0, x_offset=0, max_depth=None, parent_depth=None):
    """
    Recursief layout berekenen.
    Geeft terug: (layout_info_dict, total_width)
    layout_info_dict bevat 'x', 'y', 'children', 'node'

    De y-positie van interne nodes wordt bepaald door hun eigen DIEPTE
    (compute_node_depth), zodat operatie-nodes altijd correct boven elkaar staan.

    Leaves (NUMBER/FRACTION/NEG_*) krijgen een y-positie EÉN STAP onder hun parent,
    in plaats van op de gemeenschappelijke leaf-lijn. Dat voorkomt dat verbindings-
    lijnen door andere mathblocks heen lopen.
    """
    children_data = []

    # Bij eerste aanroep: bereken max_depth van de hele boom
    if max_depth is None:
        max_depth = compute_node_depth(node)

    t = node.get("type")

    if t == "BINARY_OP":
        child_nodes = [node.get("left"), node.get("right")]
        child_nodes = [c for c in child_nodes if c is not None]
    elif t == "MANIFOLD_OP":
        child_nodes = node.get("operands", [])
    elif t == "POWER":
        # Toon base als kind; exponent staat als superscript in het label
        child_nodes = [node.get("base")]
        child_nodes = [c for c in child_nodes if c is not None]
    elif t == "SIMPLIFY_OP":
        # SIMPLIFY_OP heeft één kind: de source
        child_nodes = [node.get("source")]
        child_nodes = [c for c in child_nodes if c is not None]
    elif t == "MIXED_NUMBER_OP":
        # MIXED_NUMBER_OP heeft één kind: de source
        child_nodes = [node.get("source")]
        child_nodes = [c for c in child_nodes if c is not None]
    elif t == "MATROESJKA_OP":
        # Matroesjka: gebruik alle rechter operanden + de linker van schil 1 als kinderen
        shells = node.get("shells", [])
        child_nodes = []
        if shells:
            # Schil 1 linker is eerste kind
            if shells[0].get("left"):
                child_nodes.append(shells[0]["left"])
            # Alle rechter operanden
            for shell in shells:
                if shell.get("right"):
                    child_nodes.append(shell["right"])
    else:
        child_nodes = []

    # Y-positie: depth-vanaf-root (top-down).
    # Alle nodes (operatie en leaf) staan op `depth * step_h`. Root op y=0,
    # kinderen op y=step_h, kleinkinderen op y=2*step_h, etc. (SVG y telt
    # naar beneden, dus grotere depth = lager in beeld.)
    # Dit is consistent met assign_block_ids, waar de step van een node ook
    # top-down vanuit de root wordt bepaald (kind = ouder - 1).
    #
    # Vóór 2026-05-08 werd hier compute_node_depth(node) gebruikt — de
    # bottom-up subtree-hoogte. Dat geeft inconsistente y-coördinaten voor
    # asymmetrische bomen: een korte tak (bv. 1+2 in (1+2)+((3×4)+5)) kreeg
    # een lagere y dan zijn block-ID-step suggereerde, waardoor het mathblock
    # visueel op een verkeerde rij belandde.
    is_leaf = (t in ("NUMBER", "FRACTION", "PARAMETER", "NEG_NUMBER", "NEG_FRACTION", "NEG_OP"))
    y_pos = depth * (NODE_H + V_GAP)

    if not child_nodes:
        # Leaf node
        w = node_width(node)
        info = {
            "node": node,
            "x": x_offset + w / 2,
            "y": y_pos,
            "children": [],
            "width": w,
        }
        return info, w

    # Recursief children berekenen
    # parent_depth-parameter blijft bestaan voor backward-compat; we geven nu
    # de top-down depth door (was: compute_node_depth, bottom-up).
    cursor = x_offset
    for child in child_nodes:
        child_info, child_w = compute_layout(
            child, depth + 1, cursor, max_depth, parent_depth=depth)
        children_data.append(child_info)
        cursor += child_w + H_GAP

    total_w = cursor - x_offset - H_GAP

    # Parent gecentreerd boven children
    left_x = children_data[0]["x"]
    right_x = children_data[-1]["x"]
    parent_x = (left_x + right_x) / 2

    info = {
        "node": node,
        "x": parent_x,
        "y": y_pos,
        "children": children_data,
        "width": total_w,
    }
    return info, total_w


def find_bounds(info, min_x=float('inf'), max_x=float('-inf'),
                min_y=float('inf'), max_y=float('-inf')):
    x, y = info["x"], info["y"]
    w = node_width(info["node"])
    min_x = min(min_x, x - w / 2)
    max_x = max(max_x, x + w / 2)
    min_y = min(min_y, y)
    max_y = max(max_y, y + NODE_H)
    for c in info["children"]:
        min_x, max_x, min_y, max_y = find_bounds(c, min_x, max_x, min_y, max_y)
    return min_x, max_x, min_y, max_y


# ─── SVG tekenen ─────────────────────────────────────────────────────────────

def _collect_simplify_source_ids(node, result=None):
    """Verzamel py_id() van alle nodes die source zijn van een SIMPLIFY_OP."""
    if result is None:
        result = set()
    t = node.get('type')
    if t == 'SIMPLIFY_OP':
        src = node.get('source')
        if src is not None:
            result.add(id(src))
            _collect_simplify_source_ids(src, result)
    elif t == 'BINARY_OP':
        _collect_simplify_source_ids(node.get('left', {}), result)
        _collect_simplify_source_ids(node.get('right', {}), result)
    elif t == 'MANIFOLD_OP':
        for op in node.get('operands', []):
            _collect_simplify_source_ids(op, result)
    elif t == 'POWER':
        _collect_simplify_source_ids(node.get('base', {}), result)
    elif t == 'ROOT':
        _collect_simplify_source_ids(node.get('radicand', {}), result)
    elif t == 'MATROESJKA_OP':
        for i, shell in enumerate(node.get('shells', [])):
            if i == 0:
                _collect_simplify_source_ids(shell.get('left', {}), result)
            _collect_simplify_source_ids(shell.get('right', {}), result)
    return result


def draw_nodes(svg, info, dx, dy, block_ids=None, simplify_source_ids=None):
    """Teken alle nodes en verbindingslijnen recursief."""
    if block_ids is None:
        block_ids = {}
    if simplify_source_ids is None:
        simplify_source_ids = set()
    x = info["x"] + dx
    y = info["y"] + dy
    node = info["node"]
    t = node.get("type")
    w = node_width(node)
    neg = node.get("is_negative", False)

    # Hoogte: manifold iets groter naarmate meer operanden
    h = NODE_H
    if t == "MANIFOLD_OP":
        n = node.get("operand_count", len(node.get("operands", [])))
        h = NODE_H + max(0, n - 2) * MANIFOLD_EXTRA_H

    # Verbindingslijnen naar children (getekend vóór de node, dus onder de node)
    for child in info["children"]:
        cx = child["x"] + dx
        cy = child["y"] + dy
        ET.SubElement(svg, "line", {
            "x1": str(round(x, 1)),
            "y1": str(round(y + h, 1)),
            "x2": str(round(cx, 1)),
            "y2": str(round(cy, 1)),
            "stroke": "#999",
            "stroke-width": "1.5",
            "stroke-dasharray": "4,3" if neg else "none",
        })

    # Kleur bepalen
    ck = color_key(node)
    c = COLORS.get(ck, COLORS["BINARY_OP"])

    # Randkleur: rode rand voor ELKE node met is_negative=True
    stroke_color = NEG_MATHBLOCK_STROKE if neg else c["stroke"]
    stroke_width = "3" if neg else "2"

    rx = round(x - w / 2, 1)
    ry = round(y, 1)

    ET.SubElement(svg, "rect", {
        "x": str(rx), "y": str(ry),
        "width": str(w), "height": str(h),
        "rx": "3", "ry": "3",
        "fill": c["fill"],
        "stroke": stroke_color,
        "stroke-width": stroke_width,
    })

    # Hoofd-label: operator of waarde
    label = node_label(node)
    is_input_node = t in ("NUMBER", "FRACTION")
    if is_input_node or t == "MANIFOLD_OP":
        font_size = "13"
    else:
        font_size = "18"
    font_weight = "500"  # lichter dan voorheen (was 600/700)

    if t == "MIXED_NUMBER_OP":
        # Hoofdsymbool: hoofdletter "I" + "+" + gestapelde breuk met lege vakjes.
        # Geeft visueel aan: "geheel + breuk = gemengd getal".
        # Centraal in het mathblock geplaatst, vergelijkbare grootte als
        # de operator-tekens (+, ×, ÷) in andere mathblocks.
        center_y = y + h / 2 + 4  # iets onder midden geplaatst voor balans
        text_color = c["text"]

        # Layout: "I" + "+" + gestapelde breuk-symbool
        I_w = 6              # breedte ruimte voor de I
        plus_w = 7           # breedte ruimte voor het plus-teken
        frac_w = 6           # breedte van breuk-vakjes
        frac_h = 5           # hoogte per vakje
        bar_pad = 1          # breuklijn iets breder dan de vakjes
        total_w = I_w + plus_w + frac_w + 2 * bar_pad
        # Centreren rond x
        start_x = x - total_w / 2

        # Hoofdletter "I" (in serif voor herkenbaarheid)
        ET.SubElement(svg, "text", {
            "x": f"{start_x + I_w / 2:.1f}",
            "y": f"{center_y + 6:.1f}",
            "text-anchor": "middle",
            "font-family": "Times New Roman, serif",
            "font-size": "18",
            "font-weight": "500",
            "fill": text_color,
        }).text = "I"

        # "+" tussen I en breuk
        ET.SubElement(svg, "text", {
            "x": f"{start_x + I_w + plus_w / 2:.1f}",
            "y": f"{center_y + 5:.1f}",
            "text-anchor": "middle",
            "font-family": "JetBrains Mono, Consolas, monospace",
            "font-size": "13",
            "font-weight": "500",
            "fill": text_color,
        }).text = "+"

        # Breuk: gestapelde rechthoekjes met breuklijn
        frac_x = start_x + I_w + plus_w + bar_pad
        # Teller-vakje (boven)
        ET.SubElement(svg, "rect", {
            "x": f"{frac_x:.1f}",
            "y": f"{center_y - frac_h - 1:.1f}",
            "width": f"{frac_w}",
            "height": f"{frac_h}",
            "stroke": text_color,
            "stroke-width": "0.9",
            "fill": "none",
        })
        # Breuklijn
        ET.SubElement(svg, "line", {
            "x1": f"{frac_x - bar_pad:.1f}",
            "y1": f"{center_y:.1f}",
            "x2": f"{frac_x + frac_w + bar_pad:.1f}",
            "y2": f"{center_y:.1f}",
            "stroke": text_color,
            "stroke-width": "1.1",
        })
        # Noemer-vakje (onder)
        ET.SubElement(svg, "rect", {
            "x": f"{frac_x:.1f}",
            "y": f"{center_y + 1:.1f}",
            "width": f"{frac_w}",
            "height": f"{frac_h}",
            "stroke": text_color,
            "stroke-width": "0.9",
            "fill": "none",
        })
    else:
        # Speciaal pad voor irrationale NUMBER-blokken (π met afgeronde waarde):
        # Centraal alleen de afgeronde decimale waarde. Het symbolische label
        # "getal π" staat al bovenin als type-label.
        if t == "NUMBER" and node.get("is_irrational"):
            decimals = node.get("decimals", 2)
            value = node.get("value", 0)
            if isinstance(value, (int, float)):
                value_str = f"{value:.{decimals}f}" if decimals > 0 else str(int(value))
            else:
                value_str = str(value)
            ET.SubElement(svg, "text", {
                "x": str(round(x, 1)),
                "y": str(round(y + h / 2 + 7, 1)),
                "text-anchor": "middle",
                "font-family": "JetBrains Mono, Consolas, monospace",
                "font-size": "13",
                "font-weight": "500",
                "fill": c["text"],
            }).text = value_str
        else:
            ET.SubElement(svg, "text", {
                "x": str(round(x, 1)),
                "y": str(round(y + h / 2 + 7, 1)),
                "text-anchor": "middle",
                "font-family": "JetBrains Mono, Consolas, monospace",
                "font-size": font_size,
                "font-weight": font_weight,
                "fill": c["text"],
            }).text = label

    # SIMPLIFY_OP: GGD-waarde apart rechtsonder in de box (klein, gedempt)
    if t == "SIMPLIFY_OP":
        ggd_val = node.get("ggd")
        if ggd_val is not None:
            ET.SubElement(svg, "text", {
                "x": str(round(x + w / 2 - 4, 1)),
                "y": str(round(y + h - 4, 1)),
                "text-anchor": "end",
                "font-family": "JetBrains Mono, Consolas, monospace",
                "font-size": "9",
                "font-weight": "500",
                "fill": stroke_color,
                "opacity": "0.85",
            }).text = f"GGD={ggd_val}"

    # Type-label klein bovenaan (binnen de box)
    type_short = {
        "BINARY_OP":    "binair",
        "MANIFOLD_OP":  "manifold",
        "MATROESJKA_OP":"matroesjka",
        "SIMPLIFY_OP":  "vereenvoudig",
        "MIXED_NUMBER_OP": "gemengd getal",
        "UNARY_OP":     "unair",
        "NUMBER":       "getal",
        "FRACTION":     "breuk",
        "PARAMETER":    "parameter",
        "POWER":        "macht",
        "ROOT":         "wortel",
    }.get(t, t)

    # Voor irrationale NUMBER-blokken (zoals π): toon "getal π" als type-label
    # in plaats van alleen "getal".
    if t == "NUMBER" and node.get("is_irrational"):
        symbol = node.get("symbol", "π")
        type_short = f"getal {symbol}"

    ET.SubElement(svg, "text", {
        "x": str(round(x, 1)),
        "y": str(round(y + 11, 1)),
        "text-anchor": "middle",
        "font-family": "JetBrains Mono, Consolas, monospace",
        "font-size": "8",
        "fill": stroke_color,
        "opacity": "0.8",
    }).text = type_short

    # Block ID (A1, B2, ...) linksonder in de box voor operatie-nodes
    block_id = block_ids.get(id(node))
    if block_id:
        ET.SubElement(svg, "text", {
            "x": str(round(x - w / 2 + 5, 1)),
            "y": str(round(y + h - 5, 1)),
            "text-anchor": "start",
            "font-family": "JetBrains Mono, Consolas, monospace",
            "font-size": "11",
            "font-weight": "500",
            "fill": "#1a1a1a",
        }).text = block_id

    # Uitkomst boven de box (alleen voor operatie-nodes, niet voor externe inputs)
    if t not in ("NUMBER", "FRACTION"):
        # MIXED_NUMBER_OP: toon de gemengd-getal-vorm "geheel teller/noemer"
        if t == "MIXED_NUMBER_OP":
            gm = node.get("gemengd", {}) or {}
            geheel = gm.get("geheel", 0)
            mt = gm.get("teller", 0)
            mn = gm.get("noemer", 1)
            if mt == 0:
                result_str = str(geheel)
            else:
                result_str = f"{geheel}+{abs(mt)}/{mn}"
        # Source van SIMPLIFY_OP: toon ruwe uitkomst (niet vereenvoudigd)
        elif id(node) in simplify_source_ids:
            raw = evaluate_raw(node)
            if raw is not None:
                rt, rn = raw
                result_str = str(rt) if rn == 1 else f"{rt}/{rn}"
            else:
                result_str = format_result(evaluate(node))
        else:
            result_str = format_result(evaluate(node))
        if result_str:
            ET.SubElement(svg, "text", {
                "x": str(round(x, 1)),
                "y": str(round(y - 5, 1)),
                "text-anchor": "middle",
                "font-family": "JetBrains Mono, Consolas, monospace",
                "font-size": "11",
                "font-weight": "400",
                "fill": "#333",
            }).text = f"= {result_str}"

    # Recursief children tekenen
    for child in info["children"]:
        draw_nodes(svg, child, dx, dy, block_ids, simplify_source_ids)


def generate_ast_svg(ast, title="", expression=""):
    """Genereer SVG van AST na manifold converter."""

    layout, _ = compute_layout(ast)
    min_x, max_x, min_y, max_y = find_bounds(layout)

    STEP_LABEL_W = 80           # ruimte voor "step N" labels links
    CONTENT_GAP  = 40           # extra horizontale ruimte tussen step-labels en eerste blok
    svg_w = max_x - min_x + 2 * MARGIN + STEP_LABEL_W + CONTENT_GAP
    svg_h = max_y - min_y + 2 * MARGIN + 60  # 60 voor titel

    dx = MARGIN + STEP_LABEL_W + CONTENT_GAP - min_x
    dy = MARGIN + 60 - min_y  # 60 voor titel ruimte

    svg = ET.Element("svg", {
        "xmlns": "http://www.w3.org/2000/svg",
        "width": str(round(svg_w)),
        "height": str(round(svg_h)),
        "viewBox": f"0 0 {round(svg_w)} {round(svg_h)}",
    })

    # Achtergrond (wit)
    ET.SubElement(svg, "rect", {
        "width": "100%", "height": "100%",
        "fill": "#FFFFFF",
    })

    # Titel (bovenin)
    if title:
        ET.SubElement(svg, "text", {
            "x": str(MARGIN), "y": str(MARGIN + 10),
            "font-family": "JetBrains Mono, Consolas, monospace",
            "font-size": "15", "font-weight": "500", "fill": "#1a1a1a",
        }).text = title

    # (Tweede expressie-regel verwijderd — dubbel met titel)

    # Legenda weggelaten

    # ── Step-lijnen ───────────────────────────────────────────────────────────
    # Bepaal het totaal aantal steps (= max depth van de boom)
    max_depth = compute_node_depth(ast)   # max_depth steps, step 0 t/m max_depth

    # In compute_layout is depth=0 de ROOT (bovenaan) en neemt toe naar leaves.
    # Step 0 = leaves = onderaan = y_max; step max_depth = root = y_min.
    # Stap grootte in pixels:
    step_h = NODE_H + V_GAP

    # label_margin = STEP_LABEL_W (al gedefinieerd boven)
    label_margin = STEP_LABEL_W

    # y positie van een step (step 0 = onderaan = max layout depth):
    #   layout_depth van leaves = max_depth  (want root is depth 0)
    #   y in layout = layout_depth * step_h
    #   na transformatie: y_svg = y_layout + dy
    # Step nummer s hoort bij layout_depth = max_depth - s
    #   → y_center = (max_depth - s) * step_h + dy + NODE_H / 2

    for s in range(max_depth + 1):
        layout_depth = max_depth - s
        y_center = layout_depth * step_h + dy + NODE_H / 2
        y_line = round(y_center)

        # Grijze horizontale stippellijn over de volle breedte. Begint vlak
        # na het step-label en loopt door tot aan de rechterkant; ook door
        # de CONTENT_GAP-zone, zodat de visuele verbinding label → blok
        # ononderbroken is.
        ET.SubElement(svg, "line", {
            "x1": str(MARGIN + label_margin),
            "y1": str(y_line),
            "x2": str(round(svg_w - MARGIN)),
            "y2": str(y_line),
            "stroke": "#CCCCCC",
            "stroke-width": "1",
            "stroke-dasharray": "6,4",
        })

        # Label "step N" links op de lijn
        ET.SubElement(svg, "text", {
            "x": str(MARGIN + label_margin - 6),
            "y": str(y_line + 4),
            "text-anchor": "end",
            "font-family": "JetBrains Mono, Consolas, monospace",
            "font-size": "10",
            "font-weight": "500",
            "fill": "#333",
        }).text = f"step {s}"

    # Bereken block IDs en teken nodes
    block_ids = assign_block_ids(layout, max_depth)
    simplify_source_ids = _collect_simplify_source_ids(ast)
    draw_nodes(svg, layout, dx, dy, block_ids, simplify_source_ids)

    return ET.ElementTree(svg)


# ─── Main ────────────────────────────────────────────────────────────────────

def visualize(expression, output_path, title=""):
    ast = parse_expression(expression)
    normalized = normalize_ast(ast)
    annotated, _ = detect_manifolds(normalized)
    converted, _ = convert_to_manifolds(annotated, _)

    tree = generate_ast_svg(converted, title=title or f"AST: {expression}", expression=expression)
    ET.indent(tree, space="  ")
    tree.write(output_path, encoding="unicode", xml_declaration=False)
    print(f"✓ SVG opgeslagen: {output_path}")


if __name__ == "__main__":
    expressions = [
        ("2*(3+4*5)-6/2+7",                     "ast_013.svg",       "Opgave 13"),
        ("2+[1-(1/2-2/3+2)-1/2]-(1/4-1/3)",     "ast_nested.svg",    "Geneste expressie"),
        ("1/9-(3/2+5/6)+2/3+[1/9-(1/2+5/9-1/6)+5/3]", "ast_matryoshka.svg", "Matryoshka"),
    ]

    out_dir = os.path.join(os.path.dirname(__file__), "..", "examples")
    os.makedirs(out_dir, exist_ok=True)

    for expr, fname, title in expressions:
        path = os.path.join(out_dir, fname)
        visualize(expr, path, title)
