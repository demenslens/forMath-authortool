#!/usr/bin/env python3
"""
ForMath Config
===============
Leest en schrijft de persistente configuratie van de pipeline.
Config wordt opgeslagen in config.json naast dit bestand.

Op dit moment bevat de config alleen:
  - output_dir: absoluut pad waarin JSON + SVG exports worden geschreven
                en opgaven worden ingelezen.
"""

import json
import os
from pathlib import Path

CONFIG_PATH = Path(__file__).resolve().parent / 'config.json'
DEFAULT_OUTPUT_DIR = os.path.expanduser('~/Desktop/JSON_files_ForMath')


def _load_raw():
    """Lees de config van schijf. Geeft dict terug, altijd met 'output_dir'."""
    cfg = {}
    if CONFIG_PATH.exists():
        try:
            with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
                cfg = json.load(f) or {}
        except Exception:
            cfg = {}
    cfg.setdefault('output_dir', DEFAULT_OUTPUT_DIR)
    return cfg


def _save_raw(cfg):
    """Schrijf config naar schijf."""
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(cfg, f, indent=2, ensure_ascii=False)


def expand_path(path: str) -> str:
    """Expand ~ en maak absoluut (zonder controleren of het bestaat)."""
    if not path:
        return path
    return os.path.abspath(os.path.expanduser(path))


def get_output_dir() -> str:
    """Huidige output directory (absoluut pad, ~ al geëxpandeerd)."""
    cfg = _load_raw()
    return expand_path(cfg['output_dir'])


def get_output_dir_raw() -> str:
    """Output directory zoals in config (kan ~ bevatten)."""
    return _load_raw()['output_dir']


def set_output_dir(new_path: str, create_if_missing: bool = False) -> dict:
    """
    Wijzig de output directory.

    Args:
        new_path: nieuwe directory (mag ~ bevatten)
        create_if_missing: als True, wordt de directory aangemaakt als hij
                           nog niet bestaat

    Returns:
        {
          'success': bool,
          'status': 'ok' | 'needs_confirmation' | 'error',
          'output_dir': expanded path,
          'raw_path': zoals in config,
          'error': string (alleen bij status=error)
        }

        Status 'needs_confirmation' betekent: directory bestaat nog niet en
        create_if_missing=False — de UI moet de gebruiker om bevestiging vragen.
    """
    if not new_path or not new_path.strip():
        return {'success': False, 'status': 'error',
                'error': 'Geen pad opgegeven'}

    raw = new_path.strip()
    expanded = expand_path(raw)

    # Bestaat het al?
    if os.path.exists(expanded):
        if not os.path.isdir(expanded):
            return {'success': False, 'status': 'error',
                    'output_dir': expanded, 'raw_path': raw,
                    'error': 'Pad bestaat al maar is geen directory'}
        if not os.access(expanded, os.W_OK):
            return {'success': False, 'status': 'error',
                    'output_dir': expanded, 'raw_path': raw,
                    'error': 'Directory bestaat maar is niet schrijfbaar'}
        # OK: opslaan
        _write_output_dir(raw)
        return {'success': True, 'status': 'ok',
                'output_dir': expanded, 'raw_path': raw}

    # Bestaat niet: óf aanmaken, óf bevestiging vragen
    if create_if_missing:
        try:
            os.makedirs(expanded, exist_ok=True)
        except Exception as e:
            return {'success': False, 'status': 'error',
                    'output_dir': expanded, 'raw_path': raw,
                    'error': f'Kon directory niet aanmaken: {e}'}
        _write_output_dir(raw)
        return {'success': True, 'status': 'ok',
                'output_dir': expanded, 'raw_path': raw,
                'created': True}

    # Vraag om bevestiging
    return {'success': False, 'status': 'needs_confirmation',
            'output_dir': expanded, 'raw_path': raw,
            'message': f'Directory bestaat nog niet: {expanded}. Aanmaken?'}


def _write_output_dir(raw_path: str):
    """Helper om alleen output_dir in de config te updaten."""
    cfg = _load_raw()
    cfg['output_dir'] = raw_path
    _save_raw(cfg)


def get_settings() -> dict:
    """Huidige instellingen voor weergave in UI."""
    raw = get_output_dir_raw()
    expanded = expand_path(raw)
    return {
        'output_dir': expanded,
        'output_dir_raw': raw,
        'exists': os.path.isdir(expanded),
        'writable': os.path.isdir(expanded) and os.access(expanded, os.W_OK),
        'config_path': str(CONFIG_PATH),
    }
