#!/usr/bin/env python3
"""
ForMath folder_manager
======================
Module voor het beheren van de folder-structuur onder
~/Desktop/ForMath Exercise/.

Filosofie
---------
- Het bestandssysteem is de single source of truth — geen index.json,
  geen cache. Bij elke vraag scannen we de folder-boom.
- Operaties zijn defensief: ze valideren input, weigeren onveilige
  pad-constructies, en raken niets aan dat niet expliciet gevraagd is.
- Een folder mag nooit verwijderd worden als hij niet leeg is — om
  ongelukken te voorkomen.

Functies
--------
- list_folders(root)             → folder-boom als geneste dict
- list_opgaven_in_folder(path)   → lijst opgaven (JSON-bestanden) in 1 folder
- create_folder(parent, name)    → maak nieuwe folder
- rename_folder(path, new_name)  → hernoem folder
- delete_folder(path)            → verwijder folder (faalt als niet leeg)
- move_folder(src, dst_parent)   → verplaats folder + inhoud
- copy_folder(src, dst_parent)   → kopie folder + inhoud (zelfde IDs)
- find_opgave_path(opgave_id, root) → vind het bestandspad bij een ID
"""

import os
import re
import shutil
from pathlib import Path
from typing import Optional


# ─── Pad-validatie ─────────────────────────────────────────────────────────

# Toegestane karakters in een foldernaam: letters, cijfers, spatie,
# underscore, koppelteken, punt. Geen slashes, geen aanhalingstekens,
# geen path-separator-trucs.
_VALID_FOLDER_NAME = re.compile(r'^[\w \-\.()]+$')


def _validate_folder_name(name: str) -> Optional[str]:
    """Valideer een nieuwe folder-naam. Returns None bij OK, anders error string."""
    if not name or not name.strip():
        return 'Naam mag niet leeg zijn'
    if len(name) > 80:
        return 'Naam is te lang (max 80 tekens)'
    if not _VALID_FOLDER_NAME.match(name):
        return ('Naam bevat ongeldige tekens. Toegestaan: letters, cijfers, '
                'spatie, _, -, ., ()')
    if name.startswith('.'):
        return 'Naam mag niet met een punt beginnen (verborgen folder)'
    if name in ('.', '..'):
        return 'Reserved naam'
    return None


def _safe_join(root: str, *parts: str) -> str:
    """Veilige join die zorgt dat het resultaat binnen root blijft.

    Verijdelt aanvallen als '..' of absolute paden in 'parts'.
    Raises ValueError bij een verdacht pad.
    """
    root_abs = os.path.realpath(root)
    candidate = os.path.realpath(os.path.join(root_abs, *parts))
    # Resultaat moet onder root liggen.
    if not (candidate == root_abs or candidate.startswith(root_abs + os.sep)):
        raise ValueError(f"Pad valt buiten root: {candidate} (root: {root_abs})")
    return candidate


# ─── Folder-boom uitlezen ──────────────────────────────────────────────────

def list_folders(root: str) -> dict:
    """Bouw een geneste dict-representatie van de folder-boom onder root.

    Structuur:
    {
        'name': 'ForMath Exercise',
        'path': '/Users/.../ForMath Exercise',
        'children': [
            {'name': 'Niet ingedeeld', 'path': '...', 'children': [...]},
            ...
        ],
        'opgave_count': 5,   # aantal .json-bestanden direct in deze folder
    }

    Lege root → 'children': [], 'opgave_count': 0.
    Root bestaat niet → returns None.
    """
    root_abs = os.path.realpath(root)
    if not os.path.isdir(root_abs):
        return None

    def walk(path):
        name = os.path.basename(path)
        children = []
        opgave_count = 0
        try:
            entries = sorted(os.listdir(path), key=lambda s: s.lower())
        except OSError:
            entries = []
        for entry in entries:
            if entry.startswith('.'):
                continue
            full = os.path.join(path, entry)
            if os.path.isdir(full):
                children.append(walk(full))
            elif os.path.isfile(full) and entry.endswith('.json'):
                opgave_count += 1
        return {
            'name': name,
            'path': path,
            'children': children,
            'opgave_count': opgave_count,
        }

    return walk(root_abs)


def list_opgaven_in_folder(folder_path: str) -> list:
    """Lijst alle JSON-opgaven in één folder (niet recursief).

    Returns een lijst met dicts: [{'id': 'foo', 'path': '/abs/path/foo.json'}, ...].
    Geeft lege lijst terug als folder niet bestaat.
    """
    if not os.path.isdir(folder_path):
        return []
    result = []
    try:
        entries = sorted(os.listdir(folder_path), key=lambda s: s.lower())
    except OSError:
        return []
    for entry in entries:
        if entry.startswith('.'):
            continue
        if not entry.endswith('.json'):
            continue
        full = os.path.join(folder_path, entry)
        if not os.path.isfile(full):
            continue
        opgave_id = entry[:-5]  # strip .json
        result.append({'id': opgave_id, 'path': full})
    return result


# ─── Folder-operaties ──────────────────────────────────────────────────────

def create_folder(parent_path: str, name: str, root: str) -> dict:
    """Maak een nieuwe sub-folder onder parent_path.

    parent_path moet binnen root liggen. name moet geldig zijn.

    Returns: {'success': bool, 'path': new_path, 'error': str}
    """
    err = _validate_folder_name(name)
    if err:
        return {'success': False, 'error': err}

    try:
        # Veiligheid: parent_path moet binnen root liggen
        parent_safe = _safe_join(root, os.path.relpath(parent_path, root))
        new_path = _safe_join(root, os.path.relpath(parent_path, root), name)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if not os.path.isdir(parent_safe):
        return {'success': False, 'error': 'Ouder-folder bestaat niet'}

    if os.path.exists(new_path):
        return {'success': False, 'error': f"Folder '{name}' bestaat al"}

    try:
        os.makedirs(new_path)
    except OSError as e:
        return {'success': False, 'error': f'Kon folder niet aanmaken: {e}'}

    return {'success': True, 'path': new_path, 'name': name}


def rename_folder(folder_path: str, new_name: str, root: str) -> dict:
    """Hernoem een folder. Inhoud blijft, alleen de naam verandert.

    Returns: {'success': bool, 'path': new_path, 'error': str}
    """
    err = _validate_folder_name(new_name)
    if err:
        return {'success': False, 'error': err}

    try:
        rel = os.path.relpath(folder_path, root)
        folder_safe = _safe_join(root, rel)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if not os.path.isdir(folder_safe):
        return {'success': False, 'error': 'Folder bestaat niet'}

    # Root zelf hernoemen mag niet
    if os.path.realpath(folder_safe) == os.path.realpath(root):
        return {'success': False, 'error': 'Root-folder kan niet hernoemd worden'}

    parent = os.path.dirname(folder_safe)
    new_path = os.path.join(parent, new_name)

    if os.path.exists(new_path):
        return {'success': False, 'error': f"Folder '{new_name}' bestaat al"}

    try:
        os.rename(folder_safe, new_path)
    except OSError as e:
        return {'success': False, 'error': f'Kon folder niet hernoemen: {e}'}

    return {'success': True, 'path': new_path, 'name': new_name}


def delete_folder(folder_path: str, root: str) -> dict:
    """Verwijder een folder, maar alleen als hij leeg is.

    Een folder is leeg als hij geen JSON-opgaven of sub-folders bevat.
    Verborgen bestanden (zoals .DS_Store) worden genegeerd in deze check.

    Returns: {'success': bool, 'error': str}
    """
    try:
        rel = os.path.relpath(folder_path, root)
        folder_safe = _safe_join(root, rel)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if not os.path.isdir(folder_safe):
        return {'success': False, 'error': 'Folder bestaat niet'}

    if os.path.realpath(folder_safe) == os.path.realpath(root):
        return {'success': False, 'error': 'Root-folder kan niet verwijderd worden'}

    # Check: leeg? (.-bestanden negeren, ze worden weggehaald)
    try:
        entries = [e for e in os.listdir(folder_safe) if not e.startswith('.')]
    except OSError as e:
        return {'success': False, 'error': f'Kon folder niet lezen: {e}'}

    if entries:
        return {'success': False,
                'error': f'Folder is niet leeg ({len(entries)} item(s)). '
                         f'Verplaats of verwijder eerst de inhoud.'}

    # Verwijder ook eventuele .DS_Store etc.
    try:
        shutil.rmtree(folder_safe)
    except OSError as e:
        return {'success': False, 'error': f'Kon folder niet verwijderen: {e}'}

    return {'success': True}


def move_folder(folder_path: str, new_parent_path: str, root: str) -> dict:
    """Verplaats een folder (met inhoud) naar een nieuwe parent.

    De folder-naam blijft hetzelfde, alleen de parent verandert.

    Returns: {'success': bool, 'path': new_path, 'error': str}
    """
    try:
        rel_src = os.path.relpath(folder_path, root)
        rel_dst_parent = os.path.relpath(new_parent_path, root)
        src_safe = _safe_join(root, rel_src)
        dst_parent_safe = _safe_join(root, rel_dst_parent)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if not os.path.isdir(src_safe):
        return {'success': False, 'error': 'Bron-folder bestaat niet'}
    if not os.path.isdir(dst_parent_safe):
        return {'success': False, 'error': 'Doel-folder bestaat niet'}
    if os.path.realpath(src_safe) == os.path.realpath(root):
        return {'success': False, 'error': 'Root-folder kan niet verplaatst worden'}

    # Kan niet in zichzelf of in eigen sub-folder geplaatst worden
    src_real = os.path.realpath(src_safe)
    dst_parent_real = os.path.realpath(dst_parent_safe)
    if dst_parent_real == src_real or dst_parent_real.startswith(src_real + os.sep):
        return {'success': False,
                'error': 'Kan folder niet in zichzelf of in eigen sub-folder plaatsen'}

    name = os.path.basename(src_safe)
    new_path = os.path.join(dst_parent_safe, name)

    if os.path.exists(new_path):
        return {'success': False,
                'error': f"Doel-folder bevat al een '{name}'"}

    try:
        shutil.move(src_safe, new_path)
    except OSError as e:
        return {'success': False, 'error': f'Kon folder niet verplaatsen: {e}'}

    return {'success': True, 'path': new_path}


def copy_folder(folder_path: str, new_parent_path: str, root: str,
                new_name: Optional[str] = None) -> dict:
    """Kopieer een folder (met inhoud) naar een nieuwe parent.

    De opgave-bestanden zelf worden identiek gekopieerd (zelfde IDs!).
    De aanroeper moet daarna eventueel de IDs aanpassen als dat nodig is.

    Args:
        folder_path: bron-folder
        new_parent_path: doel-parent
        root: opslag-root
        new_name: optionele nieuwe naam (default: zelfde naam met '(kopie)')

    Returns: {'success': bool, 'path': new_path, 'error': str}
    """
    try:
        rel_src = os.path.relpath(folder_path, root)
        rel_dst_parent = os.path.relpath(new_parent_path, root)
        src_safe = _safe_join(root, rel_src)
        dst_parent_safe = _safe_join(root, rel_dst_parent)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    if not os.path.isdir(src_safe):
        return {'success': False, 'error': 'Bron-folder bestaat niet'}
    if not os.path.isdir(dst_parent_safe):
        return {'success': False, 'error': 'Doel-folder bestaat niet'}
    if os.path.realpath(src_safe) == os.path.realpath(root):
        return {'success': False, 'error': 'Root-folder kan niet gekopieerd worden'}

    # Verzin nieuwe naam als die niet expliciet gegeven is
    if new_name is None:
        base_name = os.path.basename(src_safe)
        # Als doel-parent ≠ bron-parent, mag dezelfde naam
        if os.path.realpath(os.path.dirname(src_safe)) == os.path.realpath(dst_parent_safe):
            new_name = f'{base_name} (kopie)'
        else:
            new_name = base_name
    else:
        err = _validate_folder_name(new_name)
        if err:
            return {'success': False, 'error': err}

    new_path = os.path.join(dst_parent_safe, new_name)

    # Als naam al bestaat, hang volgnummer aan
    if os.path.exists(new_path):
        counter = 2
        while os.path.exists(f'{new_path} {counter}'):
            counter += 1
        new_path = f'{new_path} {counter}'

    try:
        shutil.copytree(src_safe, new_path)
    except OSError as e:
        return {'success': False, 'error': f'Kon folder niet kopiëren: {e}'}

    return {'success': True, 'path': new_path,
            'name': os.path.basename(new_path)}


# ─── Opgave-lookup ─────────────────────────────────────────────────────────

def find_opgave_path(opgave_id: str, root: str) -> Optional[str]:
    """Vind het pad bij een opgave-ID door de folder-boom te scannen.

    Returns het volledige pad (.../opgave_id.json) of None.

    Bij meerdere matches (theoretisch onmogelijk maar laten we het opvangen):
    de eerste match wordt geretourneerd; een waarschuwing wordt geprint.
    """
    if not os.path.isdir(root):
        return None

    target = f'{opgave_id}.json'
    matches = []

    for dirpath, dirnames, filenames in os.walk(root):
        # Skip verborgen folders
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        if target in filenames:
            matches.append(os.path.join(dirpath, target))

    if not matches:
        return None
    if len(matches) > 1:
        print(f"[folder_manager] WAARSCHUWING: opgave '{opgave_id}' bestaat "
              f"op {len(matches)} plekken: {matches}. Eerste wordt gebruikt.")
    return matches[0]


def list_all_opgaven(root: str) -> list:
    """Lijst ALLE opgaven uit de hele boom, met hun folder-pad.

    Returns: [{'id': 'foo', 'path': '/abs/path/foo.json', 'folder': 'sub/folder'}, ...]
    'folder' is het pad relatief aan root.
    """
    if not os.path.isdir(root):
        return []
    root_abs = os.path.realpath(root)
    result = []
    for dirpath, dirnames, filenames in os.walk(root_abs):
        dirnames[:] = [d for d in dirnames if not d.startswith('.')]
        rel_folder = os.path.relpath(dirpath, root_abs)
        for fname in sorted(filenames, key=lambda s: s.lower()):
            if fname.startswith('.') or not fname.endswith('.json'):
                continue
            full = os.path.join(dirpath, fname)
            opgave_id = fname[:-5]
            result.append({
                'id': opgave_id,
                'path': full,
                'folder': '' if rel_folder == '.' else rel_folder,
            })
    return result


# ─── Opgave-operaties ──────────────────────────────────────────────────────

def _free_filename(target_dir: str, base_name: str, ext: str) -> str:
    """Vind een vrije bestandsnaam in target_dir, met suffix bij conflict.

    base_name zonder extensie (bv. 'opgave_20260513_001'), ext zonder punt
    (bv. 'json'). Returns een bestandsnaam zonder pad.

    'foo.json' bestaat al → 'foo (1).json'
    'foo.json' én 'foo (1).json' bestaan al → 'foo (2).json'
    """
    candidate = f'{base_name}.{ext}'
    if not os.path.exists(os.path.join(target_dir, candidate)):
        return candidate
    counter = 1
    while True:
        candidate = f'{base_name} ({counter}).{ext}'
        if not os.path.exists(os.path.join(target_dir, candidate)):
            return candidate
        counter += 1


def move_opgave_to_folder(opgave_id: str, target_folder_name: str,
                          root: str, source_folder: Optional[str] = None) -> dict:
    """Verplaats een opgave (JSON + SVG) naar een folder direct onder root.

    Bij naam-conflict in de doel-folder wordt een suffix toegevoegd, zodat
    geen bestand wordt overschreven.

    Args:
        opgave_id: ID van de opgave (zonder .json/.svg)
        target_folder_name: folder-naam direct onder root (bv. 'Prullenbak')
        root: opslag-root
        source_folder: optioneel relatief pad onder root waar de opgave nu
            staat (bv. 'Trial'). Wordt gebruikt om eenduidig de bron te
            bepalen bij meerdere matches op opgave_id. Indien None: zoek
            via find_opgave_path (eerste match).

    Returns:
        {
          'success': bool,
          'error': str (bij fout),
          'json_path': new path (bij succes),
          'svg_path': new path of None (bij succes, SVG was er niet),
          'renamed_to': nieuwe ID als suffix is toegevoegd, of None
        }
    """
    if not opgave_id or not target_folder_name:
        return {'success': False, 'error': 'opgave_id en target_folder_name verplicht'}

    # Vind huidige locatie. Als source_folder is meegegeven, gebruik die
    # direct (eenduidig). Anders fallback op find_opgave_path.
    src_json = None
    if source_folder is not None:
        try:
            src_dir = _safe_join(root, source_folder) if source_folder else os.path.realpath(root)
            candidate = os.path.join(src_dir, f'{opgave_id}.json')
            if os.path.isfile(candidate):
                src_json = candidate
        except ValueError:
            pass
    if src_json is None:
        src_json = find_opgave_path(opgave_id, root)
    if not src_json or not os.path.isfile(src_json):
        return {'success': False, 'error': f"Opgave '{opgave_id}' niet gevonden"}

    src_dir = os.path.dirname(src_json)
    src_svg = os.path.join(src_dir, f'{opgave_id}.svg')
    has_svg = os.path.isfile(src_svg)

    # Bepaal doel-folder (direct onder root)
    try:
        target_dir = _safe_join(root, target_folder_name)
    except ValueError as e:
        return {'success': False, 'error': str(e)}

    # Doel mag niet bron-folder zijn (zou een no-op zijn, maar onverwacht)
    if os.path.realpath(src_dir) == os.path.realpath(target_dir):
        return {'success': False,
                'error': f"Opgave staat al in '{target_folder_name}'"}

    # Maak doel-folder aan als die nog niet bestaat
    if not os.path.isdir(target_dir):
        try:
            os.makedirs(target_dir, exist_ok=True)
        except OSError as e:
            return {'success': False,
                    'error': f'Kon doel-folder niet aanmaken: {e}'}

    # Bepaal vrije bestandsnaam voor JSON (en evt. SVG met zelfde base)
    new_json_name = _free_filename(target_dir, opgave_id, 'json')
    new_id = new_json_name[:-5]  # zonder .json
    renamed = (new_id != opgave_id)

    dst_json = os.path.join(target_dir, new_json_name)
    dst_svg  = os.path.join(target_dir, f'{new_id}.svg') if has_svg else None

    # Verplaats JSON eerst; als dat lukt, dan SVG. Bij fout bij SVG laten we
    # JSON op de nieuwe locatie staan — eerlijk gezegd onmogelijk te
    # herstellen zonder atomic rename-systeem, dus we melden het.
    try:
        shutil.move(src_json, dst_json)
    except OSError as e:
        return {'success': False, 'error': f'Kon JSON niet verplaatsen: {e}'}

    if has_svg:
        try:
            shutil.move(src_svg, dst_svg)
        except OSError as e:
            return {'success': False,
                    'error': f"JSON is verplaatst maar SVG faalde: {e}. "
                             f"JSON staat nu in {dst_json}, SVG nog in {src_svg}.",
                    'json_path': dst_json,
                    'renamed_to': new_id if renamed else None}

    return {
        'success': True,
        'json_path': dst_json,
        'svg_path': dst_svg,
        'renamed_to': new_id if renamed else None,
    }
