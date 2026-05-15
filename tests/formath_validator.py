"""
ForMath opgave-JSON validator.

Controleert of een door de Invoertool gegenereerde JSON voldoet aan het
formaat dat het werkblad verwacht, volgens `SPECIFICATIE_AST.md`:

- Top-level velden: metadata, mathblocks, externe_inputs, steps, duo_verzameling
- metadata.expressie bevat: latex, mathml, ast (met tree + node_map)
- ast.tree volgt MathJSON-vocabulaire (Add/Negate/Multiply/Divide/Rational/Power/Sqrt/Root)
- ast.node_map entries hebben: path (list[int]), mathblock_id (str), type ('operation'|'input')
  inputs hebben daarnaast een 'waarde'-veld

Gebruik:
    from formath_validator import validate_opgave
    result = validate_opgave(json_dict)
    if not result.ok:
        for err in result.errors:
            print(err)

Of vanaf command line:
    python3 -m tests.formath_validator path/to/opgave.json
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any


# MathJSON heads die we toestaan in ast.tree (conform SPECIFICATIE_AST.md)
ALLOWED_HEADS = {
    'Add', 'Negate', 'Multiply', 'Divide', 'Rational',
    'Power', 'Sqrt', 'Root',
}

# Toegestane klasse-waarden voor didactische categorie van een mathblock
ALLOWED_KLASSES = {'A1', 'B1', 'B2'}

# Toegestane waarden voor metadata.opdracht
ALLOWED_OPDRACHT = {'reken_uit', 'vereenvoudig'}

# Verplichte velden op top-level
REQUIRED_TOP = ['metadata', 'mathblocks', 'externe_inputs', 'steps', 'duo_verzameling']

# Verplichte velden in metadata
REQUIRED_METADATA = ['id', 'auteur', 'expressie', 'aantal_mathblocks',
                     'aantal_steps']

# Verplichte velden in metadata.expressie
REQUIRED_EXPRESSIE = ['latex', 'ast']  # mathml mag leeg maar moet aanwezig zijn


@dataclass
class ValidationResult:
    ok: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def add_error(self, msg: str) -> None:
        self.errors.append(msg)
        self.ok = False

    def add_warning(self, msg: str) -> None:
        self.warnings.append(msg)


def validate_opgave(data: dict) -> ValidationResult:
    """
    Valideer een opgave-JSON tegen het werkblad-formaat.

    Returns een ValidationResult met `ok`, `errors` en `warnings`.
    """
    result = ValidationResult(ok=True)

    # 1. Top-level structuur
    _check_top_level(data, result)
    if not result.ok:
        return result  # kan niet verder zonder basis-structuur

    # 2. metadata
    metadata = data.get('metadata', {})
    _check_metadata(metadata, result)

    # 3. metadata.expressie en ast
    expressie = metadata.get('expressie', {})
    _check_expressie(expressie, result)

    # 4. Consistentie: node_map verwijst naar bestaande mathblocks
    mathblocks = data.get('mathblocks', [])
    ast = expressie.get('ast', {})
    _check_node_map_refs(ast, mathblocks, result)

    # 5. Consistentie: elk mathblock is bereikbaar via node_map
    _check_all_mathblocks_mapped(ast, mathblocks, result)

    # 6. steps verwijzen naar bestaande mathblocks
    _check_steps_refs(data.get('steps', []), mathblocks, result)

    # 7. duo_verzameling consistentie
    _check_duo_refs(data.get('duo_verzameling', []), mathblocks, result)

    # 8. randvoorwaarden (optioneel) — als aanwezig, valideren
    _check_randvoorwaarden(metadata.get('randvoorwaarden'), result)

    # 9. klasse-velden op mathblocks (optioneel) — waarden en B2-consistentie
    _check_mathblock_klasses(mathblocks, result)

    # 10. opdracht (optioneel) — als aanwezig, geldig
    _check_opdracht(metadata.get('opdracht'), result)

    return result


# ─── Individuele checks ─────────────────────────────────────────────────────


def _check_top_level(data: dict, result: ValidationResult) -> None:
    if not isinstance(data, dict):
        result.add_error(f"Root moet een dict zijn, kreeg: {type(data).__name__}")
        return
    for key in REQUIRED_TOP:
        if key not in data:
            result.add_error(f"Ontbrekend top-level veld: '{key}'")

    # types van top-level lijstvelden
    for key in ['mathblocks', 'externe_inputs', 'steps', 'duo_verzameling']:
        if key in data and not isinstance(data[key], list):
            result.add_error(f"'{key}' moet een lijst zijn, kreeg: {type(data[key]).__name__}")


def _check_metadata(metadata: dict, result: ValidationResult) -> None:
    if not isinstance(metadata, dict):
        result.add_error("'metadata' moet een dict zijn")
        return
    for key in REQUIRED_METADATA:
        if key not in metadata:
            result.add_error(f"Ontbrekend veld metadata.{key}")

    # aantal_mathblocks moet matchen met len(mathblocks) — checken we apart
    aantal = metadata.get('aantal_mathblocks')
    if aantal is not None and not isinstance(aantal, int):
        result.add_error(f"metadata.aantal_mathblocks moet int zijn, kreeg: {type(aantal).__name__}")


def _check_expressie(expressie: dict, result: ValidationResult) -> None:
    if not isinstance(expressie, dict):
        result.add_error("'metadata.expressie' moet een dict zijn")
        return

    for key in REQUIRED_EXPRESSIE:
        if key not in expressie:
            result.add_error(f"Ontbrekend veld metadata.expressie.{key}")

    ast = expressie.get('ast')
    if ast is None:
        return  # al gemeld

    if not isinstance(ast, dict):
        result.add_error("metadata.expressie.ast moet een dict zijn")
        return

    if 'tree' not in ast:
        result.add_error("Ontbrekend veld metadata.expressie.ast.tree")
    else:
        _check_mathjson_tree(ast['tree'], path='tree', result=result)

    if 'node_map' not in ast:
        result.add_error("Ontbrekend veld metadata.expressie.ast.node_map")
    else:
        _check_node_map(ast['node_map'], result)


def _check_mathjson_tree(node: Any, path: str, result: ValidationResult) -> None:
    """Recursief: elke array-node is [head, ...operands] waar head in ALLOWED_HEADS."""
    if isinstance(node, (int, float)):
        return  # getal-leaf is OK
    if node is None:
        # None mag voorkomen als placeholder; is een signaal dat de tree-bouwer een
        # node overgeslagen heeft. We markeren als warning (werkblad kan crashen).
        result.add_warning(f"{path}: null-node in tree — bouwer heeft iets overgeslagen")
        return
    if not isinstance(node, list):
        result.add_error(f"{path}: verwacht array of getal, kreeg {type(node).__name__}: {node!r}")
        return
    if len(node) == 0:
        result.add_error(f"{path}: lege array is geen valide MathJSON-node")
        return

    head = node[0]
    if not isinstance(head, str):
        result.add_error(f"{path}: eerste element moet head-string zijn, kreeg {head!r}")
        return

    if head not in ALLOWED_HEADS:
        result.add_error(
            f"{path}: onbekende MathJSON-head '{head}'. "
            f"Toegestaan: {sorted(ALLOWED_HEADS)}"
        )
        return

    # Head-specifieke checks
    operands = node[1:]
    if head == 'Rational':
        if len(operands) != 2 or not all(isinstance(x, int) for x in operands):
            result.add_error(f"{path}: Rational verwacht 2 integers, kreeg {operands!r}")
        # Geen recursie nodig: teller en noemer zijn per definitie integers
        return

    if head == 'Negate':
        if len(operands) != 1:
            result.add_error(f"{path}: Negate verwacht 1 operand, kreeg er {len(operands)}")

    if head in ('Add', 'Multiply'):
        if len(operands) < 2:
            result.add_error(f"{path}: {head} verwacht ≥2 operanden, kreeg er {len(operands)}")

    if head == 'Divide':
        if len(operands) != 2:
            result.add_error(f"{path}: Divide verwacht 2 operanden, kreeg er {len(operands)}")

    if head == 'Power':
        if len(operands) != 2:
            result.add_error(f"{path}: Power verwacht 2 operanden (base, exponent), kreeg er {len(operands)}")

    if head == 'Sqrt':
        if len(operands) != 1:
            result.add_error(f"{path}: Sqrt verwacht 1 operand, kreeg er {len(operands)}")

    if head == 'Root':
        if len(operands) != 2:
            result.add_error(f"{path}: Root verwacht 2 operanden (radicand, index), kreeg er {len(operands)}")

    # Recurseer
    for i, child in enumerate(operands):
        _check_mathjson_tree(child, f"{path}[{i}]", result)


def _check_node_map(node_map: Any, result: ValidationResult) -> None:
    if not isinstance(node_map, list):
        result.add_error(f"ast.node_map moet een lijst zijn, kreeg {type(node_map).__name__}")
        return

    seen_paths: set[tuple] = set()
    for i, entry in enumerate(node_map):
        if not isinstance(entry, dict):
            result.add_error(f"node_map[{i}]: moet dict zijn, kreeg {type(entry).__name__}")
            continue

        # verplichte velden
        for key in ('path', 'mathblock_id', 'type'):
            if key not in entry:
                result.add_error(f"node_map[{i}]: ontbrekend veld '{key}'")

        path = entry.get('path')
        if path is not None:
            if not isinstance(path, list) or not all(isinstance(x, int) for x in path):
                result.add_error(f"node_map[{i}]: 'path' moet list[int] zijn, kreeg {path!r}")
            else:
                key = tuple(path)
                if key in seen_paths:
                    result.add_error(f"node_map[{i}]: dubbel pad {path}")
                seen_paths.add(key)

        t = entry.get('type')
        if t not in ('operation', 'input'):
            result.add_error(f"node_map[{i}]: 'type' moet 'operation' of 'input' zijn, kreeg {t!r}")

        if t == 'input' and 'waarde' not in entry:
            result.add_error(f"node_map[{i}]: input-entry mist 'waarde'")


def _check_node_map_refs(ast: dict, mathblocks: list, result: ValidationResult) -> None:
    if not isinstance(ast, dict):
        return
    node_map = ast.get('node_map')
    if not isinstance(node_map, list):
        return
    block_ids = {mb.get('id') for mb in mathblocks if isinstance(mb, dict)}
    for i, entry in enumerate(node_map):
        if not isinstance(entry, dict):
            continue
        bid = entry.get('mathblock_id')
        if bid is None:
            result.add_error(f"node_map[{i}]: 'mathblock_id' is null")
        elif bid not in block_ids:
            result.add_error(
                f"node_map[{i}]: mathblock_id '{bid}' bestaat niet in mathblocks"
            )


def _check_all_mathblocks_mapped(ast: dict, mathblocks: list, result: ValidationResult) -> None:
    if not isinstance(ast, dict):
        return
    node_map = ast.get('node_map', [])
    if not isinstance(node_map, list):
        return

    operation_bids = {
        e.get('mathblock_id')
        for e in node_map
        if isinstance(e, dict) and e.get('type') == 'operation'
    }
    block_ids = {mb.get('id') for mb in mathblocks if isinstance(mb, dict)}

    missing = block_ids - operation_bids
    if missing:
        result.add_warning(
            f"mathblocks zonder operation-entry in node_map: {sorted(missing)} "
            f"(cursor-tracking werkt dan niet voor die blocks)"
        )


def _check_steps_refs(steps: list, mathblocks: list, result: ValidationResult) -> None:
    block_ids = {mb.get('id') for mb in mathblocks if isinstance(mb, dict)}
    for i, step in enumerate(steps):
        if not isinstance(step, dict):
            continue
        for bid in step.get('mathblocks', []):
            if bid not in block_ids:
                result.add_error(
                    f"steps[{i}]: verwijst naar onbekende mathblock_id '{bid}'"
                )


def _check_duo_refs(duo: list, mathblocks: list, result: ValidationResult) -> None:
    block_ids = {mb.get('id') for mb in mathblocks if isinstance(mb, dict)}
    for i, entry in enumerate(duo):
        if not isinstance(entry, dict):
            continue
        for level in ('hoog', 'laag'):
            for bid in entry.get(level, []):
                if bid not in block_ids:
                    result.add_error(
                        f"duo_verzameling[{i}].{level}: onbekende mathblock_id '{bid}'"
                    )


def _check_randvoorwaarden(randvoorwaarden, result: ValidationResult) -> None:
    """
    metadata.randvoorwaarden is optioneel. Als aanwezig moet het een dict zijn
    met bekende sleutels en correcte types.
    """
    if randvoorwaarden is None:
        return
    if not isinstance(randvoorwaarden, dict):
        result.add_error(
            f"metadata.randvoorwaarden moet een dict zijn, "
            f"kreeg: {type(randvoorwaarden).__name__}"
        )
        return

    # vereenvoudig_uitkomst: optioneel, moet bool zijn
    if 'vereenvoudig_uitkomst' in randvoorwaarden:
        val = randvoorwaarden['vereenvoudig_uitkomst']
        if not isinstance(val, bool):
            result.add_error(
                f"metadata.randvoorwaarden.vereenvoudig_uitkomst moet bool zijn, "
                f"kreeg {type(val).__name__}: {val!r}"
            )

    # Onbekende sleutels → waarschuwing, geen fout (forward-compat)
    bekend = {'vereenvoudig_uitkomst'}
    onbekend = set(randvoorwaarden.keys()) - bekend
    if onbekend:
        result.add_warning(
            f"metadata.randvoorwaarden bevat onbekende sleutel(s): {sorted(onbekend)}"
        )


def _check_mathblock_klasses(mathblocks: list, result: ValidationResult) -> None:
    """
    Elk mathblock mag optioneel een 'klasse'-veld hebben met een van
    ALLOWED_KLASSES als waarde. Voor klasse 'B2' op een optel-mathblock
    verwachten we een 'kgv'-veld (positief integer).
    """
    for i, mb in enumerate(mathblocks):
        if not isinstance(mb, dict) or 'klasse' not in mb:
            continue
        klasse = mb['klasse']
        if klasse not in ALLOWED_KLASSES:
            result.add_error(
                f"mathblocks[{i}] ({mb.get('id','?')}): onbekende klasse '{klasse}'. "
                f"Toegestaan: {sorted(ALLOWED_KLASSES)}"
            )
            continue

        # B2 op een optelling: verwacht 'kgv' veld (niet strikt verplicht,
        # maar zeer aanbevolen — waarschuwing als het ontbreekt).
        if klasse == 'B2':
            op_symbool = mb.get('operatie', {}).get('symbool', '')
            is_sum = op_symbool == '+' or op_symbool.startswith('M+')
            if is_sum and 'kgv' not in mb:
                result.add_warning(
                    f"mathblocks[{i}] ({mb.get('id','?')}): klasse B2 op optelling "
                    f"zonder 'kgv'-veld"
                )
            if 'kgv' in mb:
                kgv = mb['kgv']
                if not isinstance(kgv, int) or kgv <= 0:
                    result.add_error(
                        f"mathblocks[{i}] ({mb.get('id','?')}): 'kgv' moet positieve "
                        f"int zijn, kreeg {kgv!r}"
                    )


def _check_opdracht(opdracht, result: ValidationResult) -> None:
    """metadata.opdracht is optioneel. Als aanwezig moet het een van
    ALLOWED_OPDRACHT zijn."""
    if opdracht is None:
        return
    if not isinstance(opdracht, str):
        result.add_error(
            f"metadata.opdracht moet string zijn, kreeg {type(opdracht).__name__}"
        )
        return
    if opdracht not in ALLOWED_OPDRACHT:
        result.add_error(
            f"metadata.opdracht heeft onbekende waarde '{opdracht}'. "
            f"Toegestaan: {sorted(ALLOWED_OPDRACHT)}"
        )


# ─── CLI ────────────────────────────────────────────────────────────────────


def _format_result(path: str, result: ValidationResult) -> str:
    lines = [f"{path}:"]
    if result.ok and not result.warnings:
        lines.append("  ✓ OK")
    else:
        if result.ok:
            lines.append("  ✓ valide (met waarschuwingen)")
        else:
            lines.append(f"  ✗ {len(result.errors)} fout(en)")
        for err in result.errors:
            lines.append(f"    ✗ {err}")
        for warn in result.warnings:
            lines.append(f"    ⚠ {warn}")
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if len(argv) < 2:
        print("Gebruik: python3 formath_validator.py <opgave.json> [opgave2.json ...]")
        return 2

    total_ok = 0
    total_fail = 0
    for path in argv[1:]:
        try:
            with open(path, encoding='utf-8') as f:
                data = json.load(f)
        except (OSError, json.JSONDecodeError) as e:
            print(f"{path}:\n  ✗ kan niet inlezen: {e}")
            total_fail += 1
            continue

        result = validate_opgave(data)
        print(_format_result(path, result))
        if result.ok:
            total_ok += 1
        else:
            total_fail += 1

    print(f"\n{total_ok} OK, {total_fail} gefaald")
    return 0 if total_fail == 0 else 1


if __name__ == '__main__':
    sys.exit(main(sys.argv))
