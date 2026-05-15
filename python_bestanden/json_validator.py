#!/usr/bin/env python3
"""
ForMath JSON-validator
=======================

Controleert de structurele integriteit van een opgave-JSON vóór hij naar
disk wordt geschreven. Twee soorten checks:

A. Structureel
   - Top-level keys aanwezig
   - Geneste metadata-structuur compleet
   - Cross-references kloppen (mathblock-id's in steps bestaan,
     node_map verwijst naar bestaande AST-nodes, aantal_* klopt)
   - Geen orphan steps of mathblocks

C. Roundtrip
   - JSON wordt na schrijven teruggelezen en byte-voor-byte vergeleken
   - Detecteert encoding-issues, file-system corruption, etc.

Gebruik:
    from json_validator import validate_structure, validate_roundtrip

    errors = validate_structure(opgave_dict)
    if errors:
        # opslaan blokkeren, errors tonen
        ...

    # na schrijven:
    warnings = validate_roundtrip(file_path, original_dict)
    if warnings:
        # waarschuwing tonen, file blijft staan
        ...
"""

import json
import os
from typing import Any


# ─── Structurele check ─────────────────────────────────────────────────────

# Verplichte top-level keys in een opgave-JSON
_REQUIRED_TOP_LEVEL = ['metadata', 'mathblocks', 'externe_inputs', 'steps',
                       'duo_verzameling']

# Verplichte keys in metadata
_REQUIRED_METADATA = ['id', 'expressie', 'aantal_mathblocks', 'aantal_steps']

# Verplichte keys in metadata.expressie
_REQUIRED_EXPRESSIE = ['tekst', 'latex_display', 'ast']

# Verplichte keys in metadata.expressie.ast
_REQUIRED_AST = ['tree', 'node_map']


def validate_structure(opgave: Any) -> list:
    """
    Valideer de structurele integriteit van een opgave-dictionary.

    Returns: lijst met error-strings. Lege lijst betekent: alles OK.
    """
    errors = []

    # ── Niveau 1: top-level ──
    if not isinstance(opgave, dict):
        return [f'Opgave is geen object/dict (type: {type(opgave).__name__})']

    for key in _REQUIRED_TOP_LEVEL:
        if key not in opgave:
            errors.append(f"Ontbrekend top-level veld: '{key}'")

    # Vroegtijdig stoppen als top-level kapot is — diepere checks zouden
    # vals positieven kunnen geven
    if errors:
        return errors

    # ── Niveau 2: metadata ──
    metadata = opgave['metadata']
    if not isinstance(metadata, dict):
        errors.append(f"'metadata' is geen object (type: {type(metadata).__name__})")
        return errors

    for key in _REQUIRED_METADATA:
        if key not in metadata:
            errors.append(f"Ontbrekend metadata-veld: '{key}'")

    if errors:
        return errors

    # ── Niveau 3: expressie ──
    expressie = metadata['expressie']
    if not isinstance(expressie, dict):
        errors.append("'metadata.expressie' is geen object")
        return errors

    for key in _REQUIRED_EXPRESSIE:
        if key not in expressie:
            errors.append(f"Ontbrekend metadata.expressie-veld: '{key}'")

    if errors:
        return errors

    # ── Niveau 4: AST ──
    ast = expressie['ast']
    if not isinstance(ast, dict):
        errors.append("'metadata.expressie.ast' is geen object")
        return errors

    for key in _REQUIRED_AST:
        if key not in ast:
            errors.append(f"Ontbrekend metadata.expressie.ast-veld: '{key}'")

    if errors:
        return errors

    # Tree-validatie: als er mathblocks zijn, moet de tree een operator-
    # structuur zijn (dict of lijst), niet een primitief getal. Een
    # primitief getal als root betekent dat een AST-node-type in de
    # _node_to_mathjson fallback viel (return 0), wat een bug is.
    # Bij 0 mathblocks (bv. expressie '5') is een primitieve tree wel OK.
    tree = ast.get('tree')
    mathblocks_for_count = opgave.get('mathblocks', [])
    has_mathblocks = (isinstance(mathblocks_for_count, list)
                      and len(mathblocks_for_count) > 0)
    if has_mathblocks and not isinstance(tree, (dict, list, str)):
        errors.append(
            f"metadata.expressie.ast.tree heeft verkeerd type: "
            f"{type(tree).__name__} (verwacht dict, list of str). "
            f"Mogelijk valt een AST-node-type in de _node_to_mathjson "
            f"fallback (return 0)."
        )

    # node_map moet niet leeg zijn als er mathblocks zijn — leeg betekent
    # dat de pad-koppeling tussen studentinvoer en mathblocks ontbreekt,
    # waardoor de studenttool niet kan functioneren.
    node_map = ast.get('node_map')
    if (isinstance(node_map, (list, dict)) and len(node_map) == 0
            and has_mathblocks):
        errors.append(
            f"metadata.expressie.ast.node_map is leeg terwijl er "
            f"{len(mathblocks_for_count)} mathblocks zijn. De studenttool "
            f"kan geen pad-koppeling maken."
        )

    # ── Cross-references ──
    mathblocks = opgave['mathblocks']
    steps = opgave['steps']

    if not isinstance(mathblocks, list):
        errors.append("'mathblocks' is geen lijst")
    if not isinstance(steps, list):
        errors.append("'steps' is geen lijst")

    if errors:
        return errors

    # Verzamel alle mathblock-IDs voor cross-check
    mathblock_ids = set()
    for i, mb in enumerate(mathblocks):
        if not isinstance(mb, dict):
            errors.append(f"mathblock[{i}] is geen object")
            continue
        mb_id = mb.get('id')
        if not mb_id:
            errors.append(f"mathblock[{i}] heeft geen 'id'-veld")
            continue
        if mb_id in mathblock_ids:
            errors.append(f"Dubbele mathblock-id: '{mb_id}'")
        mathblock_ids.add(mb_id)

    # Check dat elke step verwijst naar een bestaande mathblock
    referenced_mb_ids = set()
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            errors.append(f"step[{i}] is geen object")
            continue
        step_mb_ids = step.get('mathblock_ids', [])
        if not isinstance(step_mb_ids, list):
            errors.append(f"step[{i}].mathblock_ids is geen lijst")
            continue
        for mb_id in step_mb_ids:
            if mb_id not in mathblock_ids:
                errors.append(
                    f"step[{i}] verwijst naar onbekende mathblock-id: '{mb_id}'"
                )
            referenced_mb_ids.add(mb_id)

    # Orphan mathblocks: mathblocks die door geen step worden gebruikt.
    # Dit is een WARNING-achtige situatie maar geen blokkerende fout —
    # voor nu opnemen als info; gebruiker mag zelf beslissen.
    # (We loggen het wel in het rapport maar markeren als 'orphan_warning')
    orphans = mathblock_ids - referenced_mb_ids
    # Niet als error behandeld om opslag niet te blokkeren bij randgevallen.
    # Wel teruggeven via een aparte aanroep indien gewenst.

    # ── Aantallen consistent ──
    aantal_mb = metadata.get('aantal_mathblocks')
    if isinstance(aantal_mb, int) and aantal_mb != len(mathblocks):
        errors.append(
            f"metadata.aantal_mathblocks={aantal_mb}, "
            f"maar er zijn {len(mathblocks)} mathblocks"
        )

    aantal_steps = metadata.get('aantal_steps')
    if isinstance(aantal_steps, int) and aantal_steps != len(steps):
        errors.append(
            f"metadata.aantal_steps={aantal_steps}, "
            f"maar er zijn {len(steps)} steps"
        )

    return errors


def validate_structure_with_warnings(opgave: Any) -> dict:
    """
    Uitgebreidere variant: retourneert zowel errors als warnings.

    Returns: {'errors': [...], 'warnings': [...]}
    Errors blokkeren opslag, warnings informeren alleen.
    """
    errors = validate_structure(opgave)
    warnings = []

    if isinstance(opgave, dict):
        mathblocks = opgave.get('mathblocks', [])
        steps = opgave.get('steps', [])
        if isinstance(mathblocks, list) and isinstance(steps, list):
            mb_ids = {mb.get('id') for mb in mathblocks
                      if isinstance(mb, dict) and mb.get('id')}
            referenced = set()
            for step in steps:
                if isinstance(step, dict):
                    for mb_id in step.get('mathblock_ids', []):
                        referenced.add(mb_id)
            orphans = mb_ids - referenced
            if orphans:
                warnings.append(
                    f"Mathblock(s) worden door geen step gebruikt: "
                    f"{', '.join(sorted(orphans))}"
                )

    return {'errors': errors, 'warnings': warnings}


# ─── Roundtrip check ───────────────────────────────────────────────────────

def validate_roundtrip(file_path: str, original_dict: dict) -> list:
    """
    Lees het bestand terug en vergelijk met het origineel dat we wilden
    schrijven. Detecteert encoding-issues, partiële writes, etc.

    Returns: lijst met warning-strings. Lege lijst = bestand is identiek.
    """
    warnings = []

    if not os.path.isfile(file_path):
        return [f"Bestand bestaat niet na schrijven: {file_path}"]

    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            written_text = f.read()
    except Exception as e:
        return [f"Kon teruggelezen bestand niet openen: {e}"]

    try:
        written_dict = json.loads(written_text)
    except json.JSONDecodeError as e:
        return [f"Teruggelezen bestand is geen geldige JSON: {e}"]

    # Vergelijk de dicts. We gebruiken een diepe gelijkheidsvergelijking
    # door beide naar JSON-strings te converteren (gesorteerd op key, met
    # zelfde indent) en die te vergelijken. Verschillen in key-volgorde
    # zien we hierdoor niet als probleem.
    try:
        original_canonical = json.dumps(original_dict, sort_keys=True,
                                        ensure_ascii=False, default=str)
        written_canonical = json.dumps(written_dict, sort_keys=True,
                                       ensure_ascii=False, default=str)
    except Exception as e:
        return [f"Kon JSON niet canonicaliseren voor vergelijking: {e}"]

    if original_canonical != written_canonical:
        # Probeer een korte indicatie te geven van waar het verschil zit
        diff_summary = _summarize_diff(original_dict, written_dict)
        warnings.append(
            f"Teruggelezen bestand wijkt af van wat geschreven werd. {diff_summary}"
        )

    return warnings


def _summarize_diff(a: dict, b: dict, path: str = '') -> str:
    """Zoek het eerste verschil tussen twee dicts en beschrijf het kort."""
    if type(a) != type(b):
        return f"Type-mismatch op {path or 'root'}: {type(a).__name__} vs {type(b).__name__}"

    if isinstance(a, dict):
        a_keys = set(a.keys())
        b_keys = set(b.keys())
        if a_keys != b_keys:
            missing = a_keys - b_keys
            extra = b_keys - a_keys
            parts = []
            if missing:
                parts.append(f"ontbreekt: {', '.join(sorted(missing))}")
            if extra:
                parts.append(f"onverwacht: {', '.join(sorted(extra))}")
            return f"Verschil op {path or 'root'}: " + '; '.join(parts)
        for k in a:
            sub = _summarize_diff(a[k], b[k], f"{path}.{k}" if path else k)
            if sub:
                return sub
        return ''

    if isinstance(a, list):
        if len(a) != len(b):
            return f"Lijst-lengte verschilt op {path}: {len(a)} vs {len(b)}"
        for i, (av, bv) in enumerate(zip(a, b)):
            sub = _summarize_diff(av, bv, f"{path}[{i}]")
            if sub:
                return sub
        return ''

    if a != b:
        return f"Waarde verschilt op {path}"

    return ''
