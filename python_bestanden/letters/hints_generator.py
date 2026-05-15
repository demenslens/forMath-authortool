#!/usr/bin/env python3
"""
ForMath Hints Generator
========================
Genereert structurele hints en feedback per mathblock (Type 1 en Type 2).

Type 1 — Structureel: wat gebeurt er in deze stap, hoe, en waar moet je op letten
Type 2 — Strategisch: efficiëntie-aanbevelingen (al in vereenvoudig-blocks)
Type 3 — Didactisch: placeholder velden voor latere AI/auteur invulling

De hints worden toegevoegd aan elk mathblock in de JSON output.

Aanpasbare teksten
------------------
Alle teksten zijn opgeslagen in hints_templates.json (in dezelfde directory).
Auteurs/scholen kunnen dat bestand met de hand aanpassen om de standaardteksten
te wijzigen, zonder Python-code te raken.

Bij missende of corrupte templates valt de generator terug op een set
ingebouwde defaults zodat de tool altijd blijft werken.
"""

import json
import os
from collections import OrderedDict
from typing import Dict, Any, Optional


# ─── Templates laden ──────────────────────────────────────────────────────────

_TEMPLATES_FILE = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    'hints_templates.json'
)
_templates_cache: Optional[Dict[str, Any]] = None


# Ingebouwde fallback-templates - alleen actief als hints_templates.json
# ontbreekt of corrupt is. Hierdoor blijft de tool werken zelfs zonder
# extern bestand.
_FALLBACK_TEMPLATES = {
    "binary_op": {
        "+": {"wat": "Tel de twee getallen bij elkaar op.",
              "hoe_zonder_breuk": "Voeg de twee getallen samen tot één som.",
              "hoe_met_breuk": "Maak de noemers gelijknamig en tel de tellers op.",
              "let_op_met_breuk": "Vergeet niet de noemers gelijk te maken."},
        "×": {"wat": "Vermenigvuldig de twee getallen met elkaar.",
              "hoe_zonder_breuk": "Bereken het product.",
              "hoe_met_breuk": "Vermenigvuldig tellers en noemers afzonderlijk.",
              "let_op_met_breuk": ""},
        ":": {"wat": "Deel het eerste getal door het tweede.",
              "hoe_zonder_breuk": "Deel teller door noemer.",
              "hoe_met_breuk": "Vermenigvuldig met het omgekeerde van de tweede breuk.",
              "let_op_met_breuk": ""},
        "let_op_negatief": "Het minteken vóór deze bewerking werkt op het hele resultaat."
    },
    "manifold_op": {
        "+": {"wat": "Tel deze {n} getallen bij elkaar op.",
              "hoe_zonder_breuk": "De volgorde van optellen is vrij.",
              "hoe_met_breuk": "Maak alle breuken gelijknamig met het KGV.",
              "let_op_met_breuk": ""},
        "×": {"wat": "Vermenigvuldig deze {n} factoren.",
              "hoe_zonder_breuk": "De volgorde is vrij.",
              "hoe_met_breuk": "Vermenigvuldig alle tellers en alle noemers.",
              "let_op_met_breuk": ""},
        "let_op_negatief": "Het minteken werkt op het hele resultaat."
    },
    "power": {"wat": "Verhef tot de macht {exp}.",
              "hoe": "Vermenigvuldig {exp} keer met zichzelf.",
              "let_op_negatief_even": "Negatief grondtal met even exponent geeft positief resultaat.",
              "let_op_negatief_oneven": "Negatief grondtal met oneven exponent geeft negatief resultaat.",
              "let_op_breuk": "Verhef teller en noemer apart tot de macht {exp}.",
              "let_op_negatief": "Het minteken werkt op het hele resultaat."},
    "root": {
        "vierkantswortel": {"wat": "Trek de vierkantswortel.",
                            "hoe": "Zoek het getal dat met zichzelf het radicand geeft."},
        "machtswortel": {"wat": "Trek de {idx}-de machtswortel.",
                         "hoe": "Zoek het getal dat tot de macht {idx} het radicand geeft."},
        "let_op_breuk": "Bij een breuk: trek wortel uit teller en noemer apart."
    },
    "simplify_op": {"wat": "Vereenvoudig de breuk.",
                    "hoe": "Deel teller en noemer door GGD = {ggd}.",
                    "let_op": "Volledig vereenvoudigd als GGD = 1.",
                    "voorbeeld": "{rt}/{rn} = {vt}/{vn}."},
    "mixed_number_op": {"wat": "Schrijf de oneigenlijke breuk als gemengd getal.",
                        "hoe": "Deel teller door noemer; quotiënt is het hele getal, rest is de nieuwe teller.",
                        "let_op": "Alleen zinvol als teller >= noemer.",
                        "voorbeeld_zonder_rest": "{rt}/{rn} = {int_geh}.",
                        "voorbeeld_met_rest": "{rt}/{rn} = {int_geh} {abs_mt}/{mn}."},
    "matroesjka_op": {"wat": "Werk de keten van {n} bewerkingen af.",
                      "hoe": "Reken van binnen naar buiten.",
                      "let_op": "De volgorde bij : en × is belangrijk."},
    "feedback": {"bij_correct_root": "Dit is het goede antwoord, de opgave is klaar.",
                 "bij_correct_tussen": "Correct, ga door.",
                 "bij_fout_algemeen": "Klopt nog niet. Controleer je berekening."}
}


def _load_templates() -> Dict[str, Any]:
    """Lees hints_templates.json met caching en fallback bij missend/corrupt bestand."""
    global _templates_cache
    if _templates_cache is not None:
        return _templates_cache

    if os.path.exists(_TEMPLATES_FILE):
        try:
            with open(_TEMPLATES_FILE, 'r', encoding='utf-8') as f:
                tpl = json.load(f)
            # Sleutels die met _ beginnen zijn meta-data en hoeven niet
            tpl = {k: v for k, v in tpl.items() if not k.startswith('_')}
            _templates_cache = tpl
            return tpl
        except (json.JSONDecodeError, IOError) as e:
            print(f"[WAARSCHUWING] Kan hints_templates.json niet lezen: {e}")
            print(f"[WAARSCHUWING] Terugvallen op ingebouwde defaults.")

    _templates_cache = _FALLBACK_TEMPLATES
    return _FALLBACK_TEMPLATES


def reload_templates() -> Dict[str, Any]:
    """Forceer herladen van templates (handig na handmatig bewerken)."""
    global _templates_cache
    _templates_cache = None
    return _load_templates()


def _fmt(s: str, **kwargs) -> str:
    """Format een template-string met keyword arguments. Gemiste placeholders blijven staan."""
    if not s:
        return s
    try:
        return s.format(**kwargs)
    except (KeyError, IndexError):
        # Als de template een placeholder gebruikt die we niet hebben, geef
        # de string ongewijzigd terug (beter dan crashen).
        return s


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _has_fraction_input(node: Dict[str, Any]) -> bool:
    """Check of een operatie-node minstens één breuk-input heeft (recursief)."""
    t = node.get('type')
    if t == 'FRACTION':
        return True
    if t == 'NUMBER':
        return False
    if t == 'BINARY_OP':
        return _has_fraction_input(node.get('left', {})) or _has_fraction_input(node.get('right', {}))
    if t == 'MANIFOLD_OP':
        return any(_has_fraction_input(op) for op in node.get('operands', []))
    if t == 'POWER':
        return _has_fraction_input(node.get('base', {}))
    if t == 'SIMPLIFY_OP':
        return True
    return False


# ─── Hint-generators per type ─────────────────────────────────────────────────

def _generate_binary_op_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor binaire operaties (+, ×, :)."""
    tpl = _load_templates().get('binary_op', {})
    op = node.get('operator', '?')
    neg = node.get('is_negative', False)
    left = node.get('left', {})
    right = node.get('right', {})
    has_fraction = _has_fraction_input(left) or _has_fraction_input(right)

    op_tpl = tpl.get(op, {})
    if not op_tpl:
        return {}

    hints = {'wat': op_tpl.get('wat', '')}

    if has_fraction:
        hints['hoe'] = op_tpl.get('hoe_met_breuk', '')
        let_op = op_tpl.get('let_op_met_breuk', '')
        if let_op:
            hints['let_op'] = let_op
    else:
        hints['hoe'] = op_tpl.get('hoe_zonder_breuk', '')

    if neg:
        bestaand = hints.get('let_op', '')
        extra = tpl.get('let_op_negatief', '')
        if extra:
            hints['let_op'] = f"{bestaand} {extra}".strip()

    return hints


def _generate_manifold_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor MANIFOLD_OP."""
    tpl = _load_templates().get('manifold_op', {})
    op = node.get('operator', '?')
    n = node.get('operand_count', len(node.get('operands', [])))
    neg = node.get('is_negative', False)
    has_fraction = any(_has_fraction_input(o) for o in node.get('operands', []))

    op_tpl = tpl.get(op, {})
    if not op_tpl:
        return {}

    hints = {'wat': _fmt(op_tpl.get('wat', ''), n=n)}

    if has_fraction:
        hints['hoe'] = _fmt(op_tpl.get('hoe_met_breuk', ''), n=n)
        let_op = _fmt(op_tpl.get('let_op_met_breuk', ''), n=n)
        if let_op:
            hints['let_op'] = let_op
    else:
        hints['hoe'] = _fmt(op_tpl.get('hoe_zonder_breuk', ''), n=n)

    if neg:
        bestaand = hints.get('let_op', '')
        extra = tpl.get('let_op_negatief', '')
        if extra:
            hints['let_op'] = f"{bestaand} {extra}".strip()

    return hints


def _generate_power_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor POWER."""
    tpl = _load_templates().get('power', {})
    exp = node.get('exponent', {}).get('value', '?')
    base = node.get('base', {})
    neg = node.get('is_negative', False)

    hints = {
        'wat': _fmt(tpl.get('wat', ''), exp=exp),
        'hoe': _fmt(tpl.get('hoe', ''), exp=exp),
    }

    let_op = []
    if base.get('type') in ('NUMBER', 'FRACTION') and base.get('is_negative'):
        try:
            exp_int = int(exp)
            if exp_int % 2 == 0:
                let_op.append(tpl.get('let_op_negatief_even', ''))
            else:
                let_op.append(tpl.get('let_op_negatief_oneven', ''))
        except (ValueError, TypeError):
            pass

    if base.get('type') == 'FRACTION' or _has_fraction_input(base):
        let_op.append(_fmt(tpl.get('let_op_breuk', ''), exp=exp))

    if neg:
        let_op.append(tpl.get('let_op_negatief', ''))

    let_op = [s for s in let_op if s]
    if let_op:
        hints['let_op'] = ' '.join(let_op)

    return hints


def _generate_root_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor ROOT."""
    tpl = _load_templates().get('root', {})
    idx = node.get('index', {}).get('value', 2)

    if str(idx) == '2':
        sub = tpl.get('vierkantswortel', {})
    else:
        sub = tpl.get('machtswortel', {})

    hints = {
        'wat': _fmt(sub.get('wat', ''), idx=idx),
        'hoe': _fmt(sub.get('hoe', ''), idx=idx),
    }

    radicand = node.get('radicand', {})
    if radicand.get('type') == 'FRACTION':
        let_op = tpl.get('let_op_breuk', '')
        if let_op:
            hints['let_op'] = let_op

    return hints


def _generate_simplify_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor SIMPLIFY_OP."""
    tpl = _load_templates().get('simplify_op', {})
    ggd = node.get('ggd', '?')
    ruw = node.get('ruw', {})
    verv = node.get('vereenvoudigd', {})

    hints = {
        'wat': tpl.get('wat', ''),
        'hoe': _fmt(tpl.get('hoe', ''), ggd=ggd),
        'let_op': tpl.get('let_op', ''),
    }

    if ruw and verv:
        rt, rn = ruw.get('teller'), ruw.get('noemer')
        vt, vn = verv.get('teller'), verv.get('noemer')
        vb = tpl.get('voorbeeld', '')
        if vb:
            hints['voorbeeld'] = _fmt(vb, rt=rt, rn=rn, vt=vt, vn=vn, ggd=ggd)

    return hints


def _generate_mixed_number_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor MIXED_NUMBER_OP."""
    tpl = _load_templates().get('mixed_number_op', {})
    ruw = node.get('ruw', {})
    gm = node.get('gemengd', {})

    rt = ruw.get('teller', '?')
    rn = ruw.get('noemer', '?')
    geheel = gm.get('geheel', '?')
    mt = gm.get('teller', '?')
    mn = gm.get('noemer', '?')

    hints = {
        'wat': tpl.get('wat', ''),
        'hoe': tpl.get('hoe', ''),
        'let_op': tpl.get('let_op', ''),
    }

    if rt != '?' and rn != '?':
        try:
            abs_rt = abs(int(rt))
            int_rn = int(rn)
            int_geh = int(geheel)
            abs_mt = abs(int(mt)) if mt != 0 else 0

            if abs_mt == 0:
                vb = tpl.get('voorbeeld_zonder_rest', '')
            else:
                vb = tpl.get('voorbeeld_met_rest', '')

            if vb:
                hints['voorbeeld'] = _fmt(
                    vb,
                    rt=rt, rn=rn, abs_rt=abs_rt, int_rn=int_rn,
                    int_geh=int_geh, abs_mt=abs_mt, mn=mn
                )
        except (TypeError, ValueError):
            pass

    return hints


def _generate_matroesjka_hints(node: Dict[str, Any]) -> Dict[str, str]:
    """Hints voor MATROESJKA_OP."""
    tpl = _load_templates().get('matroesjka_op', {})
    n = node.get('shell_count', len(node.get('shells', [])))
    return {
        'wat': _fmt(tpl.get('wat', ''), n=n),
        'hoe': tpl.get('hoe', ''),
        'let_op': tpl.get('let_op', ''),
    }


def _generate_feedback(node: Dict[str, Any], is_root: bool = False) -> Dict[str, Any]:
    """Standaard feedback voor goed/fout."""
    tpl = _load_templates().get('feedback', {})

    if is_root:
        bij_correct = tpl.get('bij_correct_root', 'Dit is het goede antwoord op het gevraagde.')
    else:
        bij_correct = tpl.get('bij_correct_tussen', 'Correct, ga door.')

    return OrderedDict([
        ('bij_correct', bij_correct),
        ('bij_fout_algemeen', tpl.get('bij_fout_algemeen', 'Klopt nog niet.')),
        ('veelvoorkomende_fouten', []),
    ])


def _generate_didactisch_placeholder() -> Dict[str, str]:
    """Lege placeholder voor Type 3 didactische hints."""
    return OrderedDict([
        ('didactische_uitleg', ''),
        ('voorbeeld', ''),
        ('verwijzing_lesstof', ''),
    ])


# ─── Hoofdingang ──────────────────────────────────────────────────────────────

def generate_hints(node: Dict[str, Any], is_root: bool = False) -> Dict[str, Any]:
    """
    Genereer hints en feedback voor een mathblock.

    Args:
        node: De AST node (BINARY_OP, MANIFOLD_OP, POWER, ROOT, SIMPLIFY_OP,
              MIXED_NUMBER_OP, MATROESJKA_OP)
        is_root: True als dit het hoogste mathblock van de opgave is.

    Returns:
        OrderedDict met:
          - structureel: dict met 'wat', 'hoe', 'let_op' (Type 1)
          - feedback: dict met 'bij_correct', 'bij_fout_algemeen', 'veelvoorkomende_fouten'
          - didactisch: lege placeholder (Type 3)
    """
    t = node.get('type')

    if t == 'BINARY_OP':
        structureel = _generate_binary_op_hints(node)
    elif t == 'MANIFOLD_OP':
        structureel = _generate_manifold_hints(node)
    elif t == 'POWER':
        structureel = _generate_power_hints(node)
    elif t == 'ROOT':
        structureel = _generate_root_hints(node)
    elif t == 'SIMPLIFY_OP':
        structureel = _generate_simplify_hints(node)
    elif t == 'MIXED_NUMBER_OP':
        structureel = _generate_mixed_number_hints(node)
    elif t == 'MATROESJKA_OP':
        structureel = _generate_matroesjka_hints(node)
    else:
        structureel = {}

    return OrderedDict([
        ('structureel', OrderedDict([
            ('wat', structureel.get('wat', '')),
            ('hoe', structureel.get('hoe', '')),
            ('let_op', structureel.get('let_op', '')),
        ] + (
            [('voorbeeld', structureel['voorbeeld'])] if 'voorbeeld' in structureel else []
        ))),
        ('feedback', _generate_feedback(node, is_root=is_root)),
        ('didactisch', _generate_didactisch_placeholder()),
    ])


# ─── CLI test ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    test_nodes = [
        {'type': 'BINARY_OP', 'operator': '+',
         'left': {'type': 'NUMBER', 'value': 3},
         'right': {'type': 'NUMBER', 'value': 4}},
        {'type': 'BINARY_OP', 'operator': '×',
         'left': {'type': 'FRACTION', 'numerator': 3, 'denominator': 4},
         'right': {'type': 'FRACTION', 'numerator': 8, 'denominator': 9}},
        {'type': 'POWER', 'base': {'type': 'NUMBER', 'value': -3, 'is_negative': True},
         'exponent': {'type': 'NUMBER', 'value': 2}},
        {'type': 'SIMPLIFY_OP', 'ggd': 12,
         'ruw': {'teller': 24, 'noemer': 36},
         'vereenvoudigd': {'teller': 2, 'noemer': 3}},
        {'type': 'MIXED_NUMBER_OP',
         'ruw': {'teller': 35, 'noemer': 12},
         'gemengd': {'geheel': 2, 'teller': 11, 'noemer': 12}},
        {'type': 'MATROESJKA_OP', 'shell_count': 5, 'shells': [{}]*5},
    ]

    print(f"Templates geladen uit: {_TEMPLATES_FILE}")
    print(f"Bestaat: {os.path.exists(_TEMPLATES_FILE)}\n")

    for n in test_nodes:
        print(f"=== {n['type']} ===")
        h = generate_hints(n, is_root=(n['type'] == 'MIXED_NUMBER_OP'))
        print(json.dumps(h, indent=2, ensure_ascii=False))
        print()
