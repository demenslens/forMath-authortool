#!/usr/bin/env python3
"""
ForMath Opgave Validator v1
============================
Valideert een gegenereerd opgave-JSON-bestand op vier categorieën:

  1. Schema-integriteit  — alle verplichte velden aanwezig en juiste typen
  2. Interne consistentie — onderlinge verwijzingen kloppen
  3. Wiskundige correctheid — pipeline geeft hetzelfde resultaat als opgeslagen
  4. Randvoorwaarden — interne consistentie + match met inhoud

Locatie: dit script woont in tools/. Het verwacht dat de pipeline
(expression_parser.py, ast_normalizer.py, etc.) in de parent-directory
staat. Werkt vanaf elk werkpad.

Gebruik als CLI:
    python3 tools/validate_opgave.py opgave_001.json
    python3 tools/validate_opgave.py opgave_001.json --json
    python3 tools/validate_opgave.py *.json

Gebruik als module (vanuit pipeline-directory):
    from tools.validate_opgave import validate
    report = validate(json_dict)
    if report.is_ok():
        ...
"""

import argparse
import json
import os
import sys
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Dict, List, Optional, Tuple

# Maak de pipeline-modules importeerbaar. Dit script woont in tools/, dus
# de parent-directory bevat expression_parser.py et al. We voegen die toe
# aan sys.path zodat cat-3 (wiskundige correctheid) kan re-evalueren.
_PIPELINE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if _PIPELINE_DIR not in sys.path:
    sys.path.insert(0, _PIPELINE_DIR)


# ─── Severity & Issue ────────────────────────────────────────────────────────

ERROR = "error"      # blokkeert validatie (validation failed)
WARNING = "warning"  # rapporteer maar laat valideren slagen


@dataclass
class Issue:
    category: str          # "schema" | "consistency" | "math" | "randvoorwaarden"
    severity: str          # ERROR | WARNING
    code: str              # korte machine-leesbare code, bijv. "missing_field"
    message: str           # mens-leesbare uitleg
    location: str = ""     # waar in de JSON, bijv. "mathblocks[3].id"


@dataclass
class Report:
    issues: List[Issue] = field(default_factory=list)

    def add(self, category: str, severity: str, code: str,
            message: str, location: str = ""):
        self.issues.append(Issue(category, severity, code, message, location))

    def errors(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == ERROR]

    def warnings(self) -> List[Issue]:
        return [i for i in self.issues if i.severity == WARNING]

    def is_ok(self) -> bool:
        """True als er géén errors zijn (warnings tellen niet mee)."""
        return len(self.errors()) == 0

    def as_dict(self) -> Dict[str, Any]:
        return {
            "ok": self.is_ok(),
            "error_count": len(self.errors()),
            "warning_count": len(self.warnings()),
            "issues": [
                {
                    "category": i.category, "severity": i.severity,
                    "code": i.code, "message": i.message, "location": i.location
                }
                for i in self.issues
            ],
        }


# ─── Hoofdingang ─────────────────────────────────────────────────────────────

def validate(opgave: Dict[str, Any]) -> Report:
    """
    Valideer een opgave (dict, zoals geladen uit JSON).
    Retourneert een Report met alle gevonden issues.
    """
    report = Report()

    _check_schema(opgave, report)

    # Cat 2 t/m 4 alleen draaien als top-level schema klopt — anders crashen we
    # op KeyErrors. Een fundamentele schema-fout = stop hier.
    if any(i.code == "missing_top_level" for i in report.errors()):
        return report

    _check_internal_consistency(opgave, report)
    _check_math_correctness(opgave, report)
    _check_randvoorwaarden(opgave, report)

    return report


# ─── Cat 1: Schema-integriteit ───────────────────────────────────────────────

REQUIRED_TOP_LEVEL = ["metadata", "mathblocks", "externe_inputs",
                      "steps", "duo_verzameling"]

REQUIRED_METADATA = ["id", "expressie", "aantal_mathblocks",
                     "aantal_steps"]

REQUIRED_EXPRESSIE = ["tekst", "ast"]

REQUIRED_AST = ["tree", "node_map"]

REQUIRED_MATHBLOCK = ["id", "step", "operatie", "input", "output"]

REQUIRED_EXTERNE_INPUT = ["waarde", "mathblock_ids"]

REQUIRED_STEP = ["step", "mathblocks"]

REQUIRED_DUO = ["step", "hoog", "laag"]


def _check_schema(opgave: Dict[str, Any], r: Report) -> None:
    # Top-level
    for key in REQUIRED_TOP_LEVEL:
        if key not in opgave:
            r.add("schema", ERROR, "missing_top_level",
                  f"Verplicht top-level veld ontbreekt: '{key}'", key)

    if "metadata" in opgave and isinstance(opgave["metadata"], dict):
        meta = opgave["metadata"]
        for key in REQUIRED_METADATA:
            if key not in meta:
                r.add("schema", ERROR, "missing_metadata",
                      f"Verplicht metadata-veld ontbreekt: '{key}'",
                      f"metadata.{key}")

        # expressie
        if isinstance(meta.get("expressie"), dict):
            expr = meta["expressie"]
            for key in REQUIRED_EXPRESSIE:
                if key not in expr:
                    r.add("schema", ERROR, "missing_expressie",
                          f"Verplicht expressie-veld ontbreekt: '{key}'",
                          f"metadata.expressie.{key}")
            if isinstance(expr.get("ast"), dict):
                for key in REQUIRED_AST:
                    if key not in expr["ast"]:
                        r.add("schema", ERROR, "missing_ast",
                              f"Verplicht ast-veld ontbreekt: '{key}'",
                              f"metadata.expressie.ast.{key}")

    # mathblocks
    if isinstance(opgave.get("mathblocks"), list):
        for idx, mb in enumerate(opgave["mathblocks"]):
            if not isinstance(mb, dict):
                r.add("schema", ERROR, "bad_mathblock",
                      f"mathblocks[{idx}] is geen object", f"mathblocks[{idx}]")
                continue
            for key in REQUIRED_MATHBLOCK:
                if key not in mb:
                    r.add("schema", ERROR, "missing_mathblock_field",
                          f"Verplicht mathblock-veld ontbreekt: '{key}'",
                          f"mathblocks[{idx}].{key}")
            # Type-checks
            if "step" in mb and not isinstance(mb["step"], int):
                r.add("schema", ERROR, "bad_type",
                      f"mathblock 'step' moet int zijn, is {type(mb['step']).__name__}",
                      f"mathblocks[{idx}].step")
            if "input" in mb and not isinstance(mb["input"], list):
                r.add("schema", ERROR, "bad_type",
                      f"mathblock 'input' moet lijst zijn",
                      f"mathblocks[{idx}].input")

    # externe_inputs
    if isinstance(opgave.get("externe_inputs"), list):
        for idx, ext in enumerate(opgave["externe_inputs"]):
            if not isinstance(ext, dict):
                r.add("schema", ERROR, "bad_external",
                      f"externe_inputs[{idx}] is geen object",
                      f"externe_inputs[{idx}]")
                continue
            for key in REQUIRED_EXTERNE_INPUT:
                if key not in ext:
                    r.add("schema", ERROR, "missing_external_field",
                          f"Verplicht externe_inputs-veld ontbreekt: '{key}'",
                          f"externe_inputs[{idx}].{key}")

    # steps
    if isinstance(opgave.get("steps"), list):
        for idx, st in enumerate(opgave["steps"]):
            if not isinstance(st, dict):
                continue
            for key in REQUIRED_STEP:
                if key not in st:
                    r.add("schema", ERROR, "missing_step_field",
                          f"Verplicht step-veld ontbreekt: '{key}'",
                          f"steps[{idx}].{key}")

    # duo_verzameling
    if isinstance(opgave.get("duo_verzameling"), list):
        for idx, d in enumerate(opgave["duo_verzameling"]):
            if not isinstance(d, dict):
                continue
            for key in REQUIRED_DUO:
                if key not in d:
                    r.add("schema", ERROR, "missing_duo_field",
                          f"Verplicht duo-veld ontbreekt: '{key}'",
                          f"duo_verzameling[{idx}].{key}")


# ─── Cat 2: Interne consistentie ─────────────────────────────────────────────

def _check_internal_consistency(opgave: Dict[str, Any], r: Report) -> None:
    mathblocks = opgave.get("mathblocks", [])
    steps = opgave.get("steps", [])
    duo = opgave.get("duo_verzameling", [])
    externals = opgave.get("externe_inputs", [])
    meta = opgave.get("metadata", {})
    ast_node_map = (
        meta.get("expressie", {}).get("ast", {}).get("node_map", []) or []
    )

    # Verzamel alle bestaande mathblock IDs
    all_ids = [mb.get("id") for mb in mathblocks if isinstance(mb, dict)]
    ids_set = set(all_ids)

    # Check 2.1: Uniciteit van mathblock IDs
    seen = set()
    for idx, bid in enumerate(all_ids):
        if bid in seen:
            r.add("consistency", ERROR, "duplicate_mathblock_id",
                  f"Mathblock ID '{bid}' komt meerdere keren voor",
                  f"mathblocks[{idx}].id")
        seen.add(bid)

    # Check 2.2: aantal_mathblocks matcht len(mathblocks)
    declared = meta.get("aantal_mathblocks")
    if isinstance(declared, int) and declared != len(mathblocks):
        r.add("consistency", ERROR, "count_mismatch",
              f"metadata.aantal_mathblocks={declared} maar er zijn "
              f"{len(mathblocks)} mathblocks",
              "metadata.aantal_mathblocks")

    # Check 2.3: aantal_steps matcht max(step) over mathblocks
    if mathblocks:
        max_mb_step = max(
            (mb.get("step", 0) for mb in mathblocks if isinstance(mb, dict)),
            default=0
        )
        declared_steps = meta.get("aantal_steps")
        if isinstance(declared_steps, int) and declared_steps != max_mb_step:
            r.add("consistency", ERROR, "step_count_mismatch",
                  f"metadata.aantal_steps={declared_steps} maar hoogste "
                  f"mathblock-step={max_mb_step}",
                  "metadata.aantal_steps")

    # Check 2.4: Steps hebben opvolgende nummers (1, 2, 3, ...)
    if mathblocks:
        used_steps = sorted({mb.get("step") for mb in mathblocks
                             if isinstance(mb.get("step"), int)})
        if used_steps:
            expected = list(range(1, max(used_steps) + 1))
            missing = [s for s in expected if s not in used_steps]
            if missing:
                r.add("consistency", WARNING, "step_gap",
                      f"Step-nummers hebben gaten: ontbrekend {missing}",
                      "mathblocks")

    # Check 2.5: Elke ID in steps[].mathblocks bestaat
    for idx, st in enumerate(steps):
        if not isinstance(st, dict):
            continue
        for bid in st.get("mathblocks", []):
            if bid not in ids_set:
                r.add("consistency", ERROR, "unknown_mathblock_id_in_step",
                      f"Step {st.get('step')} verwijst naar onbekende mathblock '{bid}'",
                      f"steps[{idx}].mathblocks")

    # Check 2.6: Elke ID in duo (hoog/laag) bestaat
    for idx, d in enumerate(duo):
        if not isinstance(d, dict):
            continue
        for bucket in ("hoog", "laag"):
            for bid in d.get(bucket, []):
                if bid not in ids_set:
                    r.add("consistency", ERROR, "unknown_mathblock_id_in_duo",
                          f"DUO step {d.get('step')} {bucket} verwijst naar "
                          f"onbekende mathblock '{bid}'",
                          f"duo_verzameling[{idx}].{bucket}")

    # Check 2.7: DUO 'hoog' voor step N matcht steps[N-1].mathblocks
    steps_by_num = {
        st.get("step"): set(st.get("mathblocks", []))
        for st in steps if isinstance(st, dict)
    }
    for idx, d in enumerate(duo):
        if not isinstance(d, dict):
            continue
        step_n = d.get("step")
        hoog_set = set(d.get("hoog", []))
        if step_n in steps_by_num:
            if hoog_set != steps_by_num[step_n]:
                r.add("consistency", ERROR, "duo_hoog_mismatch",
                      f"DUO step {step_n} 'hoog' = {sorted(hoog_set)} "
                      f"maar steps[{step_n}].mathblocks = "
                      f"{sorted(steps_by_num[step_n])}",
                      f"duo_verzameling[{idx}].hoog")

    # Check 2.8: externe_inputs[].mathblock_ids verwijzen naar bestaande mathblocks
    for idx, ext in enumerate(externals):
        if not isinstance(ext, dict):
            continue
        for bid in ext.get("mathblock_ids", []):
            if bid not in ids_set:
                r.add("consistency", ERROR, "unknown_external_mathblock_id",
                      f"externe_input verwijst naar onbekende mathblock '{bid}'",
                      f"externe_inputs[{idx}].mathblock_ids")

    # Check 2.9: Mathblock-input verwijzingen naar andere mathblocks bestaan
    for idx, mb in enumerate(mathblocks):
        if not isinstance(mb, dict):
            continue
        for inp_idx, inp in enumerate(mb.get("input", [])):
            if not isinstance(inp, dict):
                continue
            if inp.get("type") == "mathblock":
                ref_id = inp.get("id")
                if ref_id not in ids_set:
                    r.add("consistency", ERROR, "unknown_input_mathblock_id",
                          f"Mathblock '{mb.get('id')}' input verwijst naar "
                          f"onbekende mathblock '{ref_id}'",
                          f"mathblocks[{idx}].input[{inp_idx}].id")

    # Check 2.10: Geen circulaire afhankelijkheden — een mathblock-input mag
    # alleen verwijzen naar een mathblock met *strikt lager* step-nummer
    step_by_id = {mb.get("id"): mb.get("step") for mb in mathblocks
                  if isinstance(mb, dict)}
    for idx, mb in enumerate(mathblocks):
        if not isinstance(mb, dict):
            continue
        my_step = mb.get("step")
        for inp_idx, inp in enumerate(mb.get("input", [])):
            if not isinstance(inp, dict):
                continue
            if inp.get("type") == "mathblock":
                ref_id = inp.get("id")
                ref_step = step_by_id.get(ref_id)
                if (isinstance(my_step, int) and isinstance(ref_step, int)
                        and ref_step >= my_step):
                    r.add("consistency", ERROR, "step_order_violation",
                          f"Mathblock '{mb.get('id')}' (step {my_step}) gebruikt "
                          f"output van '{ref_id}' (step {ref_step}) — "
                          f"input-step moet strikt lager zijn",
                          f"mathblocks[{idx}].input[{inp_idx}]")

    # Check 2.11: Elke mathblock heeft een operation-entry in node_map
    # (was bug 311_007)
    op_ids_in_map = {
        entry.get("mathblock_id")
        for entry in ast_node_map
        if isinstance(entry, dict) and entry.get("type") == "operation"
    }
    for idx, mb in enumerate(mathblocks):
        if not isinstance(mb, dict):
            continue
        bid = mb.get("id")
        if bid and bid not in op_ids_in_map:
            r.add("consistency", ERROR, "missing_operation_in_node_map",
                  f"Mathblock '{bid}' heeft geen operation-entry in "
                  f"metadata.expressie.ast.node_map",
                  f"mathblocks[{idx}].id")


# ─── Cat 3: Wiskundige correctheid ───────────────────────────────────────────

def _check_math_correctness(opgave: Dict[str, Any], r: Report) -> None:
    """
    Vergelijk de uitkomst die door re-evaluatie van de expressie wordt verkregen
    met de output van het laatste mathblock.

    Voor deze check moeten we de pipeline kunnen importeren. Als dat faalt
    (bijv. validator wordt vanaf een andere directory gedraaid), rapporteren
    we dat als WARNING en slaan we de cat-3 checks over.
    """
    try:
        from expression_parser import parse_expression
        from ast_normalizer import normalize_ast
        from manifold_detector import detect_manifolds, detect_matroesjka
        from manifold_converter import convert_to_manifolds, convert_matroesjka
        from simplify_injector import inject_simplify_ops
        from mixed_number_injector import inject_mixed_number
        from ast_visualizer import evaluate
    except ImportError as e:
        r.add("math", WARNING, "pipeline_unavailable",
              f"Kan pipeline niet importeren ({e}); cat-3 checks overgeslagen",
              "")
        return

    meta = opgave.get("metadata", {})
    expressie_tekst = meta.get("expressie", {}).get("tekst")
    if not expressie_tekst:
        r.add("math", ERROR, "no_expression_text",
              "Geen metadata.expressie.tekst om opnieuw te evalueren", "")
        return

    # Re-parse en re-evalueer
    try:
        ast = parse_expression(expressie_tekst)
        normalized = normalize_ast(ast)
        annotated, det_stats = detect_manifolds(normalized)
        converted, _ = convert_to_manifolds(annotated, det_stats)
        mat_ann, mat_chains = detect_matroesjka(converted)
        converted, _ = convert_matroesjka(mat_ann, mat_chains)
        converted, _ = inject_simplify_ops(converted)
        converted, _ = inject_mixed_number(converted)
        recomputed_val = evaluate(converted)
    except Exception as e:
        r.add("math", ERROR, "pipeline_evaluation_failed",
              f"Re-evaluatie van expressie mislukt: {e}", "")
        return

    if recomputed_val is None:
        r.add("math", WARNING, "evaluation_returned_none",
              "Re-evaluatie gaf geen resultaat (None)", "")
        return

    # Haal opgeslagen output van laatste mathblock
    mathblocks = opgave.get("mathblocks", [])
    if not mathblocks:
        return  # geen mathblocks om mee te vergelijken (al gevangen in cat 1)

    # 'Laatste' = mathblock met hoogste step
    last_mb = max((mb for mb in mathblocks if isinstance(mb, dict)),
                  key=lambda m: m.get("step", 0), default=None)
    if last_mb is None:
        return

    stored_output = last_mb.get("output", "")
    stored_value = _parse_output_string(stored_output)

    if stored_value is None:
        r.add("math", WARNING, "unparseable_output",
              f"Kan opgeslagen output '{stored_output}' niet als getal parsen "
              f"(re-evaluatie gaf {recomputed_val})",
              f"mathblocks[laatste].output")
        return

    if recomputed_val != stored_value:
        r.add("math", ERROR, "result_mismatch",
              f"Re-evaluatie geeft {recomputed_val}, maar opgeslagen output "
              f"is '{stored_output}' ({stored_value})",
              "mathblocks[laatste].output")


def _parse_output_string(s: str) -> Optional[Fraction]:
    """
    Parse een output-string naar Fraction. Ondersteunde formaten:
      - "5"           → 5
      - "3/4"         → 3/4
      - "-2/3"        → -2/3
      - "2+1/3"       → 7/3   (gemengd getal)
      - "-2+1/3"      → -5/3  (negatief gemengd: |2 1/3| en min)
      - "2.5"         → 5/2   (decimale notatie, exact)
    Returns None als parsen faalt.
    """
    if s is None:
        return None
    s = str(s).strip()
    if not s:
        return None

    try:
        # Gemengd getal: bevat '+' niet aan begin
        if "+" in s and not s.startswith("+"):
            # "geheel+t/n" of "-geheel+t/n"
            geheel_str, frac_str = s.split("+", 1)
            geheel = int(geheel_str)
            if "/" in frac_str:
                t, n = frac_str.split("/")
                rest = Fraction(int(t), int(n))
            else:
                rest = Fraction(int(frac_str))
            sign = -1 if geheel < 0 else 1
            return Fraction(abs(geheel)) * sign + rest * sign

        # Gewone breuk
        if "/" in s:
            t, n = s.split("/")
            return Fraction(int(t), int(n))

        # Decimaal of geheel
        if "." in s:
            return Fraction(s)

        return Fraction(int(s))
    except (ValueError, ZeroDivisionError):
        return None


# ─── Cat 4: Randvoorwaarden ──────────────────────────────────────────────────

# Default-waarden volgens app.js inspectorState
RV_DEFAULTS = {
    "antwoord_in_breuken": True,
    "antwoord_in_decimalen": False,
    "decimalen_afronden": 2,
    "pi_decimalen": 2,
    "uitkomst_als_gemengd_getal": True,
    "wortel_resultaat": "alleen_positief",  # NIEUW: "alleen_positief" | "plus_en_min"
    # hints_aan / feedback_aan: bewust niet meer in deze lijst (horen niet
    # bij randvoorwaarden van de opgave — zijn studenttool-instellingen)
}


def _check_randvoorwaarden(opgave: Dict[str, Any], r: Report) -> None:
    meta = opgave.get("metadata", {})
    rv = meta.get("randvoorwaarden")

    # 4c: bestaan van het veld
    if rv is None:
        r.add("randvoorwaarden", WARNING, "missing_randvoorwaarden",
              "metadata.randvoorwaarden ontbreekt — opgave is mogelijk uit een "
              "oudere versie. Defaults zullen worden aangenomen.",
              "metadata.randvoorwaarden")
        rv = {}
    elif not isinstance(rv, dict):
        r.add("randvoorwaarden", ERROR, "bad_randvoorwaarden_type",
              "metadata.randvoorwaarden is geen object",
              "metadata.randvoorwaarden")
        return

    # Effectieve waardes (defaults invullen voor ontbrekende sleutels)
    eff = {**RV_DEFAULTS, **{k: v for k, v in rv.items() if v is not None}}

    # Waarschuw voor missende sleutels (alleen voor de inhoudelijke ones)
    for key in RV_DEFAULTS:
        if key not in rv:
            r.add("randvoorwaarden", WARNING, "missing_rv_key",
                  f"randvoorwaarden.{key} ontbreekt; gebruik default "
                  f"({RV_DEFAULTS[key]!r})",
                  f"metadata.randvoorwaarden.{key}")

    # 4a: interne consistentie
    if eff["antwoord_in_breuken"] and eff["antwoord_in_decimalen"]:
        r.add("randvoorwaarden", ERROR, "rv_conflict_breuken_decimalen",
              "antwoord_in_breuken en antwoord_in_decimalen kunnen niet "
              "tegelijk True zijn",
              "metadata.randvoorwaarden")
    if not eff["antwoord_in_breuken"] and not eff["antwoord_in_decimalen"]:
        r.add("randvoorwaarden", ERROR, "rv_conflict_geen_uitkomstvorm",
              "antwoord_in_breuken en antwoord_in_decimalen kunnen niet "
              "allebei False zijn — kies minstens één uitkomstvorm",
              "metadata.randvoorwaarden")
    if eff["antwoord_in_decimalen"] and eff["uitkomst_als_gemengd_getal"]:
        r.add("randvoorwaarden", ERROR, "rv_conflict_decimalen_gemengd",
              "antwoord_in_decimalen en uitkomst_als_gemengd_getal zijn "
              "tegenstrijdig",
              "metadata.randvoorwaarden")

    # Numerieke ranges
    for key in ("decimalen_afronden", "pi_decimalen"):
        val = eff[key]
        if not isinstance(val, int) or not (0 <= val <= 15):
            r.add("randvoorwaarden", ERROR, "rv_out_of_range",
                  f"{key} = {val!r} buiten geldige range [0, 15]",
                  f"metadata.randvoorwaarden.{key}")

    # wortel_resultaat
    wr = eff["wortel_resultaat"]
    if wr not in ("alleen_positief", "plus_en_min"):
        r.add("randvoorwaarden", ERROR, "rv_bad_wortel_resultaat",
              f"wortel_resultaat = {wr!r} is geen geldige waarde "
              f"(verwacht: 'alleen_positief' of 'plus_en_min')",
              "metadata.randvoorwaarden.wortel_resultaat")

    # 4b: consistentie tussen randvoorwaarden en wiskundige inhoud
    mathblocks = opgave.get("mathblocks", [])

    # 4b.1: gemengd getal — als uit, mag root geen MIXED_NUMBER_OP zijn
    last_mb = max((mb for mb in mathblocks if isinstance(mb, dict)),
                  key=lambda m: m.get("step", 0), default=None)
    if last_mb is not None:
        op_info = last_mb.get("operatie", {})
        op_type = op_info.get("type") if isinstance(op_info, dict) else None
        if not eff["uitkomst_als_gemengd_getal"] and op_type == "MIXED_NUMBER_OP":
            r.add("randvoorwaarden", ERROR, "rv_inhoud_conflict_gemengd",
                  "uitkomst_als_gemengd_getal=False maar root mathblock is "
                  "MIXED_NUMBER_OP",
                  "mathblocks[laatste].operatie.type")

    # 4b.2: ±-wortel — voor v1 alleen check dat wortel_resultaat='plus_en_min'
    # nog niet ondersteund wordt door de pipeline
    if eff["wortel_resultaat"] == "plus_en_min":
        # Zoek of er een ROOT-mathblock in zit
        has_root = any(
            isinstance(mb, dict)
            and isinstance(mb.get("operatie"), dict)
            and mb["operatie"].get("type") == "ROOT"
            for mb in mathblocks
        )
        if has_root:
            r.add("randvoorwaarden", WARNING, "rv_plus_min_not_implemented",
                  "wortel_resultaat='plus_en_min' is gezet en de opgave bevat "
                  "een wortel, maar de pipeline genereert nog geen twee takken "
                  "voor ±. Dit is een bekend openstaand punt.",
                  "metadata.randvoorwaarden.wortel_resultaat")

    # 4b.3: π-decimalen — als 0 maar expressie bevat π, waarschuw
    expr_tekst = meta.get("expressie", {}).get("tekst", "") or ""
    if eff["pi_decimalen"] == 0 and ("π" in expr_tekst or "pi" in expr_tekst.lower()):
        r.add("randvoorwaarden", WARNING, "rv_pi_decimalen_zero",
              "Expressie bevat π maar pi_decimalen = 0 — student kan geen "
              "decimaal antwoord geven",
              "metadata.randvoorwaarden.pi_decimalen")


# ─── Output-formattering ─────────────────────────────────────────────────────

def format_text(filename: str, report: Report) -> str:
    lines = []
    lines.append(f"=== {filename} ===")
    if report.is_ok():
        n_warn = len(report.warnings())
        if n_warn == 0:
            lines.append("✓ OK (alle checks geslaagd)")
        else:
            lines.append(f"✓ OK met {n_warn} waarschuwing"
                         f"{'en' if n_warn != 1 else ''}")
    else:
        lines.append(f"✗ FAIL — {len(report.errors())} error"
                     f"{'s' if len(report.errors()) != 1 else ''}, "
                     f"{len(report.warnings())} warning"
                     f"{'s' if len(report.warnings()) != 1 else ''}")

    by_cat: Dict[str, List[Issue]] = {}
    for i in report.issues:
        by_cat.setdefault(i.category, []).append(i)

    for cat in ("schema", "consistency", "math", "randvoorwaarden"):
        if cat not in by_cat:
            continue
        lines.append(f"\n[{cat}]")
        for i in by_cat[cat]:
            marker = "ERROR " if i.severity == ERROR else "WARN  "
            loc = f" ({i.location})" if i.location else ""
            lines.append(f"  {marker} {i.code}: {i.message}{loc}")

    return "\n".join(lines)


# ─── CLI ─────────────────────────────────────────────────────────────────────

def main():
    ap = argparse.ArgumentParser(
        description="Valideer een ForMath opgave-JSON-bestand."
    )
    ap.add_argument("files", nargs="+", help="Pad(en) naar opgave_*.json")
    ap.add_argument("--json", action="store_true",
                    help="Output als JSON i.p.v. tekst")
    args = ap.parse_args()

    overall_ok = True
    results = []

    for path in args.files:
        try:
            with open(path, "r", encoding="utf-8") as f:
                opgave = json.load(f)
        except FileNotFoundError:
            print(f"FOUT: bestand niet gevonden: {path}", file=sys.stderr)
            overall_ok = False
            continue
        except json.JSONDecodeError as e:
            print(f"FOUT: ongeldig JSON in {path}: {e}", file=sys.stderr)
            overall_ok = False
            continue

        report = validate(opgave)
        if not report.is_ok():
            overall_ok = False

        if args.json:
            results.append({
                "file": os.path.basename(path),
                **report.as_dict(),
            })
        else:
            print(format_text(os.path.basename(path), report))
            print()

    if args.json:
        print(json.dumps(results, indent=2, ensure_ascii=False))

    sys.exit(0 if overall_ok else 1)


if __name__ == "__main__":
    main()
