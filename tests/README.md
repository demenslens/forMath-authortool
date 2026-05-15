# tests/

Test-suites voor de ForMath Opgave Invoertool. Alle tests gebruiken alleen
Python stdlib (geen `pip install` nodig).

## Draaien

Alles tegelijk:

```bash
python3 tests/test_latex_conversion.py
python3 tests/test_round_trip.py
python3 tests/test_error_integration.py
python3 tests/test_check_export.py
python3 tests/test_klasse_randvoorwaarden.py
python3 tests/test_inspector_e2e.py
python3 tests/test_opgaven_management.py
python3 _archief/smoke_test.py
```

Of de validator los op een bestaand JSON-bestand:

```bash
python3 tests/formath_validator.py pad/naar/opgave.json
```

## Bestanden

| Bestand | Wat |
|---|---|
| `formath_validator.py` | JSON-schema validator voor opgave-JSONs. Controleert top-level structuur, metadata, `ast.tree` (MathJSON-vocabulaire), `ast.node_map`, `randvoorwaarden` en `klasse`-velden, plus kruisverwijzingen. Ook CLI. |
| `test_latex_conversion.py` | 37 unit tests op `latex_to_expression` en AST-to-LaTeX-display, inclusief 6 round-trip property tests en regressietests voor de POWER-base haakjes-bug. |
| `test_round_trip.py` | 17 voorbeeld-expressies (11 origineel + 6 edges) door de volledige pipeline, elke output gevalideerd. |
| `test_error_integration.py` | End-to-end integratie: bad input → `/api/process` → `FriendlyError` JSON response. |
| `test_check_export.py` | Integratie-tests voor `/api/check_export`: duplicaat-detectie. |
| `test_klasse_randvoorwaarden.py` | 26 unit tests voor klasse-velden, LCM-berekening en randvoorwaarden (exporter + validator). |
| `test_inspector_e2e.py` | 16 end-to-end tests voor de inspector-flow: mathblocks uit `/api/process`, `klasse`+`kgv` in geschreven JSON. |
| `test_opgaven_management.py` | 32 integratie-tests voor opgavenbeheer: list, load, delete, overwrite, path-traversal-bescherming. |
| `inspect_export.py` | CLI-tool om een geëxporteerde JSON te inspecteren. |

## Nog bekende issues

- **311_007** (`[(3^2)*(12-9)^3]:(9-6)^3:(-3)*[(-6)^2]:3^4+(-2)^3`): de
  round-trip test slaagt maar met warning. 9 mathblocks krijgen geen
  `operation`-entry in `node_map`, waardoor cursor-tracking in het werkblad
  niet werkt voor die blocks. Structureel probleem in `_build_mathjson_ast`;
  aanpak bij iteratie 3+.
