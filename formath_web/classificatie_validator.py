"""
ForMath classificatie-validator
Laadt het JSON-schema voor opgave-classificatie en biedt een
validatiefunctie. Soft-fail als jsonschema niet geïnstalleerd is:
de server blijft draaien, alleen wordt classificatie dan niet gevalideerd.

Gebruik:
    from classificatie_validator import validate_classificatie
    error = validate_classificatie(blok)   # None bij geldig, anders foutmelding
"""

import json
import os

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemas')
SCHEMA_PATH = os.path.join(SCHEMA_DIR, 'classificatie_schema.json')

# Lazy-loaded singletons
_schema = None
_validator = None
_jsonschema_available = None
_load_error = None


def _try_load():
    """Probeer schema en validator één keer te laden. Vangt alle fouten."""
    global _schema, _validator, _jsonschema_available, _load_error

    if _jsonschema_available is not None:
        return  # al geprobeerd

    # 1. Bestaat het schemabestand?
    if not os.path.exists(SCHEMA_PATH):
        _jsonschema_available = False
        _load_error = f"Schema niet gevonden: {SCHEMA_PATH}"
        return

    # 2. Is jsonschema geïnstalleerd?
    try:
        from jsonschema import Draft7Validator
    except ImportError:
        _jsonschema_available = False
        _load_error = (
            "Module 'jsonschema' niet geïnstalleerd. "
            "Classificatievalidatie wordt overgeslagen. "
            "Installeer met: pip3 install jsonschema"
        )
        return

    # 3. Schema inlezen en valideren
    try:
        with open(SCHEMA_PATH, 'r', encoding='utf-8') as f:
            _schema = json.load(f)
        Draft7Validator.check_schema(_schema)
        _validator = Draft7Validator(_schema)
        _jsonschema_available = True
    except Exception as e:
        _jsonschema_available = False
        _load_error = f"Schema ongeldig: {e}"


def is_available() -> bool:
    """True als classificatievalidatie actief is."""
    _try_load()
    return _jsonschema_available is True


def status_message() -> str:
    """Voor printen bij serverstart."""
    _try_load()
    if _jsonschema_available:
        return f"[OK] classificatie-schema geladen: {SCHEMA_PATH}"
    return f"[WAARSCHUWING] classificatievalidatie uit: {_load_error}"


def validate_classificatie(blok):
    """
    Valideer een classificatieblok tegen het schema.

    Args:
        blok: dict met classificatievelden, of None.

    Returns:
        None als geldig (of als blok None/leeg is, of als validator niet
        beschikbaar is — soft-fail policy).
        String met foutmelding als ongeldig.
    """
    if blok is None:
        return None  # ontbrekende classificatie is geldig (optioneel)

    if not isinstance(blok, dict):
        return f"classificatie moet een object zijn, niet {type(blok).__name__}"

    if not blok:
        return None  # lege dict is geldig

    _try_load()
    if not _jsonschema_available:
        # Soft-fail: schrijf wel, valideer niet
        return None

    errors = sorted(_validator.iter_errors(blok), key=lambda e: e.path)
    if not errors:
        return None

    # Combineer foutmeldingen tot één leesbare regel
    msgs = []
    for e in errors:
        path = '.'.join(str(p) for p in e.path) or '(root)'
        msgs.append(f"{path}: {e.message}")
    return "; ".join(msgs)
