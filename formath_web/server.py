"""
ForMath Web Server
Serveert de HTML pagina en verwerkt expressies via de forMath AST pipeline.

Gebruik:
    python3 server.py
    Open http://localhost:8765 in je browser
"""

import http.server
import socketserver
import json
import os
import sys
import re
import traceback
import xml.etree.ElementTree as ET

# Voeg paden toe voor imports
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_DIR = os.path.dirname(BASE_DIR)
PIPELINE_PARENT = os.path.join(PROJECT_DIR, 'python_bestanden')

# Mapping van soort_opgave-keuzewaarde naar pipeline-directory.
# Voorlopig wijzen 'rekenen_letters' en 'simpele_vergelijkingen' nog naar
# letters/ (een kopie van getallen/) — we passen die pas aan als we de
# letters-pipeline daadwerkelijk gaan ontwikkelen.
SOORT_TO_DIR = {
    'rekenen_getallen':       'getallen',
    'rekenen_letters':        'letters',
    'simpele_vergelijkingen': 'letters',
}
DEFAULT_PIPELINE = 'getallen'

def pipeline_dir_for(soort_opgave):
    """Geef het pad naar de pipeline-directory voor een gegeven soort_opgave."""
    name = SOORT_TO_DIR.get(soort_opgave, DEFAULT_PIPELINE)
    return os.path.join(PIPELINE_PARENT, name)

# Voor dit moment laden we alleen de default pipeline (getallen) bij het
# opstarten van de server. De letters-pipeline is nog identiek aan getallen,
# dus dezelfde modules werken — switchen wordt later toegevoegd zodra de
# pipelines echt verschillen.
PIPELINE_DIR = pipeline_dir_for(DEFAULT_PIPELINE)

sys.path.insert(0, BASE_DIR)
sys.path.insert(0, PIPELINE_DIR)
# PIPELINE_PARENT (python_bestanden/) bevat modules die door alle pipelines
# gedeeld worden — bijvoorbeeld config.py en folder_manager.py. Zonder deze
# regel kan Python die niet vinden, want sys.path bevat alleen de
# pipeline-specifieke sub-folder (getallen/ of letters/).
sys.path.insert(0, PIPELINE_PARENT)

# Importeer de forMath AST pipeline
from expression_parser import parse_expression
from ast_normalizer import normalize_ast
from manifold_detector import detect_manifolds, detect_matroesjka
from manifold_converter import convert_to_manifolds, convert_matroesjka
from simplify_injector import inject_simplify_ops
from mixed_number_injector import inject_mixed_number
from ast_visualizer import generate_ast_svg

print("[OK] ForMath AST pipeline geladen (default: getallen)")
print(f"     Pipeline directory: {PIPELINE_DIR}")


PORT = 8765


# ============================================================
# LaTeX → plain expression converter
# ============================================================

def latex_to_expression(latex: str) -> str:
    """
    Converteer MathLive LaTeX naar een platte expressie string
    die de forMath expression_parser begrijpt.

    Voorbeelden:
        \\frac{1}{2} + \\frac{1}{3}  →  1/2+1/3
        3 \\times 2                   →  3×2
        \\left(3+5\\right) \\times 2  →  (3+5)×2
        3^{2}                         →  3^2
        \\sqrt{16}                    →  sqrt(16)
    """
    s = latex

    # ── Stap 1: \frac{a}{b} → breuk of deling ──
    # Herhaal tot er geen \frac meer in de string zit. Elke iteratie
    # vervangt één \frac, dus dit eindigt na precies n iteraties voor n
    # frac-occurrences. We laten ook een safety-limit staan om in
    # pathologische gevallen niet eindeloos door te lopen.
    safety = 200
    while '\\frac' in s and safety > 0:
        new_s = _replace_frac(s)
        if new_s == s:
            break  # geen verandering meer mogelijk
        s = new_s
        safety -= 1

    # ── Stap 2: \sqrt[n]{x} en \sqrt{x} ──
    # Herhaal tot er geen \sqrt meer in de string zit. Net als bij \frac is
    # de regex-aanpak niet voldoende voor geneste accolades (\sqrt{\sqrt{16}}),
    # daarom gebruiken we _replace_sqrt() met _extract_brace_group() voor
    # correcte accolade-balancing.
    safety = 200
    while '\\sqrt' in s and safety > 0:
        new_s = _replace_sqrt(s)
        if new_s == s:
            break
        s = new_s
        safety -= 1

    # ── Stap 3: Operatoren ──
    s = s.replace('\\times', '×')
    s = s.replace('\\cdot', '×')
    s = s.replace('\\div', ':')

    # ── Stap 3b: Constanten ──
    # \pi met subscript (aantal decimalen): \pi_{2} → pi(2), \pi_{5} → pi(5)
    # Bare \pi (zonder subscript) → pi(2) als default
    # Word-boundary om te voorkomen dat \pi matcht in andere commando's.
    s = re.sub(r'\\pi_\{(\d+)\}', r'pi(\1)', s)
    s = re.sub(r'\\pi_(\d)', r'pi(\1)', s)  # zonder accolades: \pi_3
    s = re.sub(r'\\pi(?![a-zA-Z_(])', 'pi(2)', s)  # bare \pi → default 2
    # Impliciete vermenigvuldiging rond pi: '2pi(' → '2*pi(' en 'pi(n)2' → 'pi(n)*2'
    s = re.sub(r'(\d)pi\(', r'\1*pi(', s)
    s = re.sub(r'(pi\(\d+\))(\d)', r'\1*\2', s)

    # ── Stap 4: Haakjes ──
    # MathLive kan \lbrack/\rbrack of gewoon [ ] gebruiken
    s = s.replace('\\left\\lbrack', '[')
    s = s.replace('\\right\\rbrack', ']')
    s = s.replace('\\lbrack', '[')
    s = s.replace('\\rbrack', ']')
    s = s.replace('\\left(', '(')
    s = s.replace('\\right)', ')')
    s = s.replace('\\left[', '[')
    s = s.replace('\\right]', ']')
    s = s.replace('\\left\\{', '(')
    s = s.replace('\\right\\}', ')')

    # ── Stap 5: Machten ──
    # ^{expr} → ^expr  (voor simpele exponenten)
    s = re.sub(r'\^{(\d+)}', r'^\1', s)
    # ^{-n} → ^(-n)
    s = re.sub(r'\^{(-\d+)}', r'^(\1)', s)
    # ^{expr} met complexe inhoud → ^(expr)
    s = re.sub(r'\^{([^{}]+)}', r'^(\1)', s)

    # ── Stap 6: Overige LaTeX cleanup ──
    # Veiligheids-check: als hier nog \frac of \sqrt in de string zit, is er
    # iets misgegaan in stap 1 of 2. Onverwerkte \frac{1}{2} wordt door de
    # cleanup hieronder samengesmolten tot "12" — een stille corruptie die
    # eerder een opgave met diep geneste breuken heeft gemangeld.
    # Idem voor \sqrt{\sqrt{16}} die zonder fail tot "(16)" verwerd.
    # Liever een duidelijke fout dan een verkeerde uitkomst.
    for cmd in ('\\frac', '\\sqrt'):
        if cmd in s:
            raise SyntaxError(
                f"Onverwerkte {cmd} in LaTeX-string: '{s[:80]}...'. "
                "De expressie heeft mogelijk een onverwachte geneste structuur."
            )
    # Verwijder overgebleven accolades die geen betekenis hebben
    s = s.replace('{', '').replace('}', '')
    # Verwijder overgebleven backslash-commando's
    s = re.sub(r'\\[a-zA-Z]+', '', s)
    # Verwijder spaties
    s = s.replace(' ', '')

    return s


def _replace_frac(s: str) -> str:
    """Vervang één niveau van \\frac{...}{...} patronen.

    Regels:
    - \\frac{3}{5}     → 3/5          (getal/getal → FRACTION in pipeline)
    - \\frac{3+4}{5}   → (3+4)/5      (complex/getal → BINARY_OP(:) maar LaTeX bewaard)
    - \\frac{3}{5*2}   → 3/(5*2)      (getal/complex → BINARY_OP(:) maar LaTeX bewaard)
    - \\frac{3+4}{5*2} → (3+4)/(5*2)  (complex/complex → BINARY_OP(:) maar LaTeX bewaard)

    Het '/' teken wordt altijd gebruikt — de pipeline herkent:
    - getal/getal zonder haakjes → FRACTION
    - (expr)/(expr) met haakjes → na pre-processing :(expr/expr) → BINARY_OP(:)
    """
    i = s.find('\\frac')
    if i == -1:
        return s

    pos = i + 5  # na '\frac'

    # Skip eventuele whitespace tussen \frac en het eerste accoladegroep
    # (MathLive levert soms "\frac {1}{2}" met spatie ertussen).
    while pos < len(s) and s[pos] in ' \t':
        pos += 1

    # Eerste argument
    arg1, end1 = _extract_brace_group(s, pos)
    if arg1 is None:
        # Bare \frac: probeer twee losse cijfers
        if pos < len(s) and s[pos].isdigit():
            j = pos
            while j < len(s) and s[j].isdigit():
                j += 1
            digits = s[pos:j]
            if len(digits) >= 2:
                return s[:i] + digits[0] + '/' + digits[1:] + s[j:]
        return s

    # Tweede argument
    # Skip ook hier eventuele whitespace tussen de twee accoladengroepen.
    pos2 = end1
    while pos2 < len(s) and s[pos2] in ' \t':
        pos2 += 1
    arg2, end2 = _extract_brace_group(s, pos2)
    if arg2 is None:
        return s

    # Whitespace in teller/noemer is voor de pipeline irrelevant en zorgt
    # ervoor dat ".isdigit()" onterecht False zou geven (bv. "\frac{ 1 }{ 2 }").
    arg1 = arg1.strip()
    arg2 = arg2.strip()

    # Beide getallen → gewone breuk getal/getal
    if arg1.isdigit() and arg2.isdigit():
        replacement = f'{arg1}/{arg2}'
    # Complexe teller of noemer → haakjes eromheen, / ertussen
    # Pre-processing in expression_parser herkent (getal)/(getal) → FRACTION
    # en laat (complex)/(complex) als BINARY_OP(:) staan
    else:
        t = arg1 if arg1.isdigit() else f'({arg1})'
        n = arg2 if arg2.isdigit() else f'({arg2})'
        replacement = f'{t}/{n}'

    return s[:i] + replacement + s[end2:]


def _extract_brace_group(s: str, pos: int):
    """Extract inhoud van {…} op positie pos. Returns (content, end_pos) of (None, pos)"""
    if pos >= len(s) or s[pos] != '{':
        return None, pos
    depth = 0
    start = pos + 1
    j = pos
    while j < len(s):
        if s[j] == '{':
            depth += 1
        elif s[j] == '}':
            depth -= 1
            if depth == 0:
                return s[start:j], j + 1
        j += 1
    return None, pos


def _replace_sqrt(s: str) -> str:
    r"""Vervang één voorkomen van \sqrt[n]{x} of \sqrt{x} door root(n,x) of sqrt(x).

    Net als bij _replace_frac gebruikt deze functie _extract_brace_group om
    accolade-nesting correct af te handelen. Een eerdere regex-aanpak
    (\\sqrt\{([^{}]*)\}) faalde stilletjes op \sqrt{\sqrt{16}} omdat de
    binnen-accolades de regex deden mismatchen — de hele \sqrt verdween
    en alleen de radicand "(16)" bleef over.

    Regels:
    - \sqrt[n]{x}  → root(n, x)
    - \sqrt{x}     → sqrt(x)
    - \sqrtN       → sqrt(N)         (bare digit-vorm)
    """
    i = s.find('\\sqrt')
    if i == -1:
        return s

    pos = i + 5  # na '\sqrt'

    # Skip eventuele whitespace tussen \sqrt en de optionele [n]/{x}.
    # MathLive levert soms "\sqrt {16}" of "\sqrt [3]{27}".
    while pos < len(s) and s[pos] in ' \t':
        pos += 1

    # Optionele [n] voor de index
    index_str = None
    if pos < len(s) and s[pos] == '[':
        # Zoek bijbehorende ]
        end_bracket = s.find(']', pos)
        if end_bracket == -1:
            return s  # malformed
        index_str = s[pos+1:end_bracket]
        pos = end_bracket + 1
        # Skip ook hier eventuele whitespace tussen [n] en {x}
        while pos < len(s) and s[pos] in ' \t':
            pos += 1

    # Radicand: ofwel {...} (met _extract_brace_group), ofwel bare digits
    if pos < len(s) and s[pos] == '{':
        radicand, end = _extract_brace_group(s, pos)
        if radicand is None:
            return s  # malformed
    elif pos < len(s) and s[pos].isdigit():
        j = pos
        while j < len(s) and s[j].isdigit():
            j += 1
        radicand = s[pos:j]
        end = j
    else:
        return s  # geen radicand gevonden

    # Bouw vervanging
    radicand = radicand.strip()
    if index_str is not None:
        replacement = f'root({index_str},{radicand})'
    else:
        replacement = f'sqrt({radicand})'

    return s[:i] + replacement + s[end:]


# ============================================================
# AST → LaTeX converter
# ============================================================

def _node_to_latex(node, top_level=True):
    """Zet een interne AST node om naar LaTeX string voor weergave.

    Fixes t.o.v. vorige versie:
    - Bug 1: negatieve getallen die als POWER-base of vermenigvuldigingsoperand
             staan krijgen altijd \\left(-v\\right) zodat MathLive ze correct leest.
    - Bug 2: geneste machten (POWER waarvan de base zelf een POWER is) krijgen
             haakjes: \\left(base^{exp}\\right)^{exp2}.
    - Bug 3: _bracketed nodes die de base van een POWER zijn krijgen altijd
             \\left(...)\\right) zodat de haakjes niet verdwijnen.
    """
    t = node.get('type')
    neg = node.get('is_negative', False)
    bra = node.get('_bracketed', False)

    # ── NUMBER ────────────────────────────────────────────────────────────────
    if t == 'NUMBER':
        v = str(node['value'])
        if neg:
            # Negatief getal: altijd \left(-v\right) zodat de context
            # (bijv. POWER-base of vermenigvuldiging) het correct leest.
            # _via_subtraction nodes zijn onderdeel van een optelling (12-9)
            # en krijgen gewoon -v zonder haakjes.
            via_sub = node.get('_via_subtraction', False)
            if via_sub:
                return f"-{v}"
            return f"\\left(-{v}\\right)"
        return v

    # ── FRACTION ──────────────────────────────────────────────────────────────
    if t == 'FRACTION':
        num = node['numerator']
        den = node['denominator']
        inner = f"\\frac{{{num}}}{{{den}}}"
        if neg:
            return f"-{inner}"
        return inner

    # ── PARAMETER ─────────────────────────────────────────────────────────────
    # Letter-parameter (a, b, c, ...) voor letterrekenen. LaTeX gebruikt de
    # letter direct; we wikkelen niet in extra commando's.
    if t == 'PARAMETER':
        n = node['name']
        if neg:
            return f"\\left(-{n}\\right)"
        return n

    # ── BINARY_OP ─────────────────────────────────────────────────────────────
    if t == 'BINARY_OP':
        op = node['operator']
        left_node = node.get('left', {})
        right_node = node.get('right', {})
        left = _node_to_latex(left_node, top_level=False)
        right = _node_to_latex(right_node, top_level=False)

        right_neg = right_node.get('is_negative', False)
        if op == ':':
            # Complexe breuk: beide kinderen zijn _bracketed → \frac{}{}
            left_bra = left_node.get('_bracketed', False)
            right_bra = right_node.get('_bracketed', False)
            if left_bra and right_bra:
                left_inner = _node_to_latex_unbracketed(left_node)
                right_inner = _node_to_latex_unbracketed(right_node)
                inner = f"\\frac{{{left_inner}}}{{{right_inner}}}"
            else:
                inner = f"{left}:{right}"
        elif op == '+':
            inner = f"{left}{right}" if right_neg else f"{left}+{right}"
        elif op == '×':
            inner = f"{left}\\times {right}"
        else:
            inner = f"{left}{op}{right}"

        if neg:
            return f"-\\left({inner}\\right)"
        if bra and not top_level:
            return f"\\left({inner}\\right)"
        return inner

    # ── MANIFOLD_OP ───────────────────────────────────────────────────────────
    if t == 'MANIFOLD_OP':
        op = node['operator']
        parts = [_node_to_latex(op2, top_level=False) for op2 in node.get('operands', [])]
        if op == '+':
            result_parts = [parts[0]]
            for i, operand in enumerate(node['operands'][1:], 1):
                if operand.get('is_negative', False):
                    result_parts.append(parts[i])
                else:
                    result_parts.append(f"+{parts[i]}")
            inner = ''.join(result_parts)
        elif op == '×':
            inner = '\\times '.join(parts)
        else:
            inner = op.join(parts)

        if neg:
            return f"-\\left({inner}\\right)"
        if bra and not top_level:
            return f"\\left({inner}\\right)"
        return inner

    # ── POWER ─────────────────────────────────────────────────────────────────
    if t == 'POWER':
        base_node = node.get('base', {})
        exp_val = node.get('exponent', {}).get('value', '?')
        base_t = base_node.get('type')
        base_neg = base_node.get('is_negative', False)
        base_bra = base_node.get('_bracketed', False)

        base_latex = _node_to_latex(base_node, top_level=False)

        # Bug 2 + 3: de base heeft altijd haakjes nodig als:
        # - de base zelf een POWER is (geneste macht: (a^b)^c)
        # - de base _bracketed is maar al geen haakjes heeft gekregen
        #   (dit kan als de base een NUMBER of FRACTION is zonder neg)
        # NUMBER/FRACTION met neg krijgen al \left(-v\right) uit de NUMBER-tak
        # BINARY_OP/_bracketed krijgt \left(...\right) uit de BINARY_OP-tak
        # POWER-base heeft nog geen haakjes → die voegen we hier toe
        needs_parens = (base_t == 'POWER')

        if needs_parens:
            base_latex = f"\\left({base_latex}\\right)"

        inner = f"{base_latex}^{{{exp_val}}}"

        if neg:
            return f"-\\left({inner}\\right)"
        if bra and not top_level:
            return f"\\left({inner}\\right)"
        return inner

    # ── ROOT ──────────────────────────────────────────────────────────────────
    if t == 'ROOT':
        radicand_node = node.get('radicand', {})
        idx_val = node.get('index', {}).get('value', 2)
        radicand_latex = _node_to_latex(radicand_node, top_level=False)

        if str(idx_val) == '2':
            inner = f"\\sqrt{{{radicand_latex}}}"
        else:
            inner = f"\\sqrt[{idx_val}]{{{radicand_latex}}}"

        if neg:
            return f"-{inner}"
        if bra and not top_level:
            return f"\\left({inner}\\right)"
        return inner

    # ── MATROESJKA_OP ─────────────────────────────────────────────────────────
    if t == 'MATROESJKA_OP':
        shells = node.get('shells', [])
        if not shells:
            return '?'
        # Schil 1: left op right
        s0 = shells[0]
        left_latex = _node_to_latex(s0.get('left', {}), top_level=False)
        right_latex = _node_to_latex(s0.get('right', {}), top_level=False)
        op0 = s0['operator']
        inner = f"{left_latex}{op0}{right_latex}"
        # Volgende schillen: result op right
        for shell in shells[1:]:
            right_latex = _node_to_latex(shell.get('right', {}), top_level=False)
            op = shell['operator']
            inner = f"\\left({inner}\\right){op}{right_latex}"

        if neg:
            return f"-\\left({inner}\\right)"
        if bra and not top_level:
            return f"\\left({inner}\\right)"
        return inner

    # ── SIMPLIFY_OP ───────────────────────────────────────────────────────────
    if t == 'SIMPLIFY_OP':
        # Vereenvoudigen: toon de source LaTeX
        # (de studenttool toont de vereenvoudigde waarde als output)
        source = node.get('source', {})
        return _node_to_latex(source, top_level=top_level)

    # ── MIXED_NUMBER_OP ───────────────────────────────────────────────────────
    if t == 'MIXED_NUMBER_OP':
        # Gemengd getal: toon gewoon de source-LaTeX. Het gemengd getal zelf
        # is een transformatie die door de studenttool als output wordt
        # gegenereerd; voor de invoer-display tonen we de source-expressie.
        source = node.get('source', {})
        return _node_to_latex(source, top_level=top_level)

    return '?'


def _node_to_latex_unbracketed(node):
    r"""
    Geeft de LaTeX van een _bracketed node zonder buitenste \left(…\right).
    Gebruikt als teller of noemer in \frac{}{}.
    """
    # Tijdelijk _bracketed uitzetten zodat geen extra haakjes worden toegevoegd
    orig = node.get('_bracketed', False)
    node['_bracketed'] = False
    result = _node_to_latex(node, top_level=True)
    node['_bracketed'] = orig
    return result


def ast_to_latex_display(converted_ast):
    """Genereer LaTeX display string vanuit de geconverteerde AST."""
    try:
        return _node_to_latex(converted_ast, top_level=True)
    except Exception:
        return ''


# ============================================================
# HTTP Handler
# ============================================================

class ForMathHandler(http.server.SimpleHTTPRequestHandler):
    """HTTP handler voor de ForMath web app"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=BASE_DIR, **kwargs)

    def do_GET(self):
        # API endpoints via GET
        if self.path == '/api/list_opgaven':
            self._handle_list_opgaven()
            return
        if self.path.startswith('/api/load_opgave'):
            self._handle_load_opgave()
            return
        if self.path == '/api/settings':
            self._handle_get_settings()
            return
        # Standaard static serving
        if self.path == '/' or self.path == '/index.html':
            self.path = '/index.html'
        super().do_GET()

    def do_POST(self):
        if self.path == '/api/process':
            self._handle_process()
        elif self.path == '/api/export_json':
            self._handle_export_json()
        elif self.path == '/api/check_export':
            self._handle_check_export()
        elif self.path == '/api/delete_opgave':
            self._handle_delete_opgave()
        elif self.path == '/api/save_hints':
            self._handle_save_hints()
        elif self.path == '/api/settings':
            self._handle_set_settings()
        # Folder-operaties (sub-ronde C)
        elif self.path == '/api/folders/create':
            self._handle_folder_create()
        elif self.path == '/api/folders/rename':
            self._handle_folder_rename()
        elif self.path == '/api/folders/delete':
            self._handle_folder_delete()
        elif self.path == '/api/folders/move':
            self._handle_folder_move()
        elif self.path == '/api/folders/copy':
            self._handle_folder_copy()
        # Opgave verplaatsen (sub-ronde D / prullenbak)
        elif self.path == '/api/move_opgave':
            self._handle_move_opgave()
        else:
            self.send_error(404, "Endpoint niet gevonden")

    def _handle_process(self):
        """Verwerk LaTeX expressie via de forMath AST pipeline"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            request_data = json.loads(body.decode('utf-8'))
            latex = request_data.get('latex', '')
            latex_display = request_data.get('latex_display', latex)
            soort_opgave  = request_data.get('soort_opgave', 'rekenen_getallen')

            if not latex:
                self._send_json({'success': False, 'error': 'Geen expressie ontvangen'})
                return

            print(f"\n[INPUT] LaTeX: {latex}")
            print(f"[INPUT] soort_opgave: {soort_opgave}")
            if latex_display != latex:
                print(f"[DISP]  LaTeX display: {latex_display}")

            # NB: voor nu gebruiken alle soorten dezelfde pipeline (de letters/
            # directory is een identieke kopie). Als de letters-pipeline straks
            # afwijkt moet hier per soort_opgave een andere set functies geladen
            # worden — zie SOORT_TO_DIR / pipeline_dir_for() bovenaan.

            # Stap 1: LaTeX → platte expressie
            expression = latex_to_expression(latex)
            print(f"[CONV]  Expressie: {expression}")

            # Stap 2: Parse → AST
            ast = parse_expression(expression)
            print(f"[PARSE] AST type: {ast.get('type')}")

            # Stap 3: Normaliseer AST
            normalized = normalize_ast(ast)

            # Stap 4: Detecteer manifolds
            annotated, detection_stats = detect_manifolds(normalized)
            print(f"[MANIF] {detection_stats}")

            # Stap 5: Converteer manifolds
            converted, _ = convert_to_manifolds(annotated, detection_stats)

            # Stap 5b: Detecteer en converteer Matroesjka manifolds
            #
            # UITGESCHAKELD per 2026-05-08 op verzoek van auteur.
            # Reden: Matroesjka-detectie genereert een apart mathblock-type
            # dat in deze fase van het project niet (meer) gewenst is.
            # Modules blijven aanwezig zodat dit eenvoudig terug te zetten is.
            #
            # mat_annotated, mat_chains = detect_matroesjka(converted)
            # converted, mat_stats = convert_matroesjka(mat_annotated, mat_chains)
            # if mat_stats['matroesjka_count'] > 0:
            #     print(f"[MATR] {mat_stats['matroesjka_count']} Matroesjka keten(s) gedetecteerd")

            # Stap 5c: Voeg SIMPLIFY_OP mathblocks toe waar vereenvoudiging nodig is
            converted, simp_stats = inject_simplify_ops(converted)
            if simp_stats['simplify_count'] > 0:
                print(f"[SIMP] {simp_stats['simplify_count']} SIMPLIFY_OP(s) ingevoegd")

            # Stap 5d: Voeg MIXED_NUMBER_OP toe BOVENOP de root als de
            # einduitkomst een oneigenlijke breuk is.
            converted, mn_stats = inject_mixed_number(converted)
            if mn_stats['mixed_number_count'] > 0:
                print(f"[MIXED] {mn_stats['mixed_number_count']} MIXED_NUMBER_OP toegevoegd")

            # Genereer latex_display vanuit de AST.
            # Behalve: als de gebruiker een LaTeX-string met formatting heeft
            # gestuurd (\frac, \sqrt, ...), respecteer die zodat MathLive de
            # opgave bij herladen kan tonen zoals de auteur hem heeft ingetypt
            # (b.v. gestapelde breuken). De AST-versie zou een "vlakke"
            # variant teruggeven en die rendering verloren laten gaan.
            ast_latex_display = ast_to_latex_display(converted)
            if '\\' in latex:  # bevat LaTeX-commando's zoals \frac
                latex_display = latex
            else:
                latex_display = ast_latex_display

            # Stap 6: Genereer AST SVG
            tree = generate_ast_svg(
                converted,
                title=f"AST: {expression}",
                expression=expression
            )

            # ElementTree → SVG string
            ET.indent(tree, space="  ")
            svg = ET.tostring(tree.getroot(), encoding='unicode')

            print(f"[OK] AST SVG gegenereerd ({len(svg)} bytes)")

            # Verwijder interne annotaties voor clean JSON export
            from manifold_converter import remove_all_annotations
            clean_ast = remove_all_annotations(converted)

            self._send_json({
                'success': True,
                'svg': svg,
                'ast': clean_ast,
                'data': {
                    'tekst': expression,
                    'latex_display': latex_display,
                }
            })

        except SyntaxError as e:
            print(f"[FOUT] Syntax error: {e}")
            print(f"[FOUT] LaTeX: {latex!r}")
            expr = latex_to_expression(latex) if latex else ''
            print(f"[FOUT] Expressie: {expr!r}")
            self._send_json({'success': False, 'error': f'Parse fout: {e}'})

        except Exception as e:
            print(f"[FOUT] {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    def _handle_export_json(self):
        """Genereer uitgebreide forMath JSON en sla op in OUTPUT_DIR."""
        try:
            from json_exporter import OUTPUT_DIR
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            request_data = json.loads(body.decode('utf-8'))
            latex = request_data.get('latex', '')
            latex_display = request_data.get('latex_display', latex)
            mathml = request_data.get('mathml', '')
            # Extra metadata velden uit app.js
            overwrite_id       = request_data.get('overwrite_id')    # of None
            randvoorwaarden    = request_data.get('randvoorwaarden', {}) or {}
            mathblock_klasses  = request_data.get('mathblock_klasses', {}) or {}
            opdracht           = request_data.get('opdracht', '') or ''
            soort_opgave       = request_data.get('soort_opgave', 'rekenen_getallen')
            productie          = request_data.get('productie', 'enkelvoudig')
            # Sub-ronde D: nieuwe metadata-velden
            onderwijstype      = request_data.get('onderwijstype', '') or ''
            onderwijsniveau    = request_data.get('onderwijsniveau', '') or ''
            notitie            = request_data.get('notitie', '') or ''

            if not latex:
                self._send_json({'success': False, 'error': 'Geen expressie ontvangen'})
                return

            print(f"\n[JSON EXPORT] LaTeX: {latex}  overwrite_id={overwrite_id}  soort={soort_opgave}  productie={productie}")

            # Pipeline (zelfde toelichting als in _handle_process: voor nu
            # gebruiken alle soorten dezelfde pipeline-modules)
            expression = latex_to_expression(latex)
            ast = parse_expression(expression)
            normalized = normalize_ast(ast)
            annotated, detection_stats = detect_manifolds(normalized)
            converted, _ = convert_to_manifolds(annotated, detection_stats)

            # Matroesjka detectie en conversie
            #
            # UITGESCHAKELD per 2026-05-08 op verzoek van auteur.
            # Zie commentaar in _handle_process voor toelichting.
            #
            # mat_annotated, mat_chains = detect_matroesjka(converted)
            # converted, _ = convert_matroesjka(mat_annotated, mat_chains)

            # SIMPLIFY_OP injectie
            converted, _ = inject_simplify_ops(converted)

            # MIXED_NUMBER_OP injectie (alleen als root een oneigenlijke breuk is)
            converted, _ = inject_mixed_number(converted)

            # Genereer latex_display vanuit de AST. Behoud user-LaTeX als
            # die formatting bevat (zie commentaar in _handle_process).
            ast_latex_display = ast_to_latex_display(converted)
            if '\\' in latex:
                latex_display = latex
            else:
                latex_display = ast_latex_display

            # Genereer JSON
            from json_exporter import generate_formath_json
            result, filepath = generate_formath_json(converted, latex, mathml,
                                                     latex_display=latex_display,
                                                     expression=expression)

            # Voeg extra metadata toe die app.js verwacht
            if 'metadata' in result:
                result['metadata']['randvoorwaarden'] = randvoorwaarden
                result['metadata']['opdracht'] = opdracht
                result['metadata']['soort_opgave'] = soort_opgave
                result['metadata']['productie'] = productie
                # Sub-ronde D: nieuwe metadata-velden
                result['metadata']['onderwijstype'] = onderwijstype
                result['metadata']['onderwijsniveau'] = onderwijsniveau
                result['metadata']['notitie'] = notitie

            # Voeg 'klasse' toe aan elke mathblock die een klasse opgegeven heeft
            if mathblock_klasses:
                for mb in result.get('mathblocks', []):
                    mb_id = mb.get('id')
                    if mb_id in mathblock_klasses:
                        mb['klasse'] = mathblock_klasses[mb_id]

            # ─── Integriteitscheck A (structureel) ──────────────────────────
            # Vóór we de uiteindelijke write doen: valideer de structuur.
            # Bij fouten: gooi het tijdelijke bestand weg en blokkeer opslag.
            from json_validator import validate_structure_with_warnings
            check_a = validate_structure_with_warnings(result)
            if check_a['errors']:
                # Gooi het tijdelijke bestand weg dat generate_formath_json maakte
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                print(f"[INTEGRITEIT] Structurele check faalt: {check_a['errors']}")
                self._send_json({
                    'success': False,
                    'error': 'JSON-integriteit faalt',
                    'integrity_errors': check_a['errors'],
                    'integrity_warnings': check_a['warnings'],
                })
                return
            integrity_warnings = list(check_a['warnings'])

            # Als overwrite_id is opgegeven: schrijf onder die naam i.p.v. de
            # automatisch gegenereerde bestandsnaam. De bestaande opgave kan
            # in een willekeurige sub-folder staan — we behouden zijn locatie.
            if overwrite_id:
                # Verwijder het automatisch aangemaakte (nieuwe) bestand
                try:
                    os.remove(filepath)
                except OSError:
                    pass
                # Zoek de bestaande locatie van de opgave die we overschrijven.
                from folder_manager import find_opgave_path
                existing_path = find_opgave_path(overwrite_id, OUTPUT_DIR)
                if existing_path:
                    filepath = existing_path
                else:
                    # Niet gevonden — fall back op de default-write-folder.
                    # overwrite_id heeft al de 'opgave_'-prefix (of niet, afhankelijk
                    # van waar het vandaan kwam), dus we voegen alleen .json toe.
                    from json_exporter import _current_write_dir
                    filepath = os.path.join(_current_write_dir(),
                                            f"{overwrite_id}.json")

            # (Her)schrijf de JSON naar de juiste locatie
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(result, f, indent=2, ensure_ascii=False)

            print(f"[OK] JSON opgeslagen: {filepath}")

            # ─── Integriteitscheck C (roundtrip) ────────────────────────────
            # Lees het bestand terug en vergelijk met wat we wilden schrijven.
            # Bij mismatch: het bestand blijft staan, maar we melden het als
            # waarschuwing (zoals afgesproken).
            from json_validator import validate_roundtrip
            roundtrip_warnings = validate_roundtrip(filepath, result)
            if roundtrip_warnings:
                print(f"[INTEGRITEIT] Roundtrip-check faalt: {roundtrip_warnings}")
                integrity_warnings.extend(roundtrip_warnings)

            # Genereer en sla SVG op met hetzelfde ID
            tree = generate_ast_svg(
                converted,
                title=f"AST: {expression}",
                expression=expression
            )
            ET.indent(tree, space="  ")
            svg = ET.tostring(tree.getroot(), encoding='unicode')

            svg_filepath = filepath.replace('.json', '.svg')
            with open(svg_filepath, 'w', encoding='utf-8') as f:
                f.write(svg)

            print(f"[OK] SVG opgeslagen: {svg_filepath}")

            self._send_json({
                'success': True,
                'filepath': filepath,
                'svg_filepath': svg_filepath,
                'filename': os.path.basename(filepath),
                'integrity_warnings': integrity_warnings,
            })

        except Exception as e:
            print(f"[FOUT] JSON export: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/list_opgaven ─────────────────────────────────────────────────────
    def _handle_list_opgaven(self):
        """Lijst alle opgaven uit de opgaven-boom met metadata.

        Sinds 2026-05-13: scant de hele folder-boom onder OUTPUT_DIR via
        folder_manager.list_all_opgaven, zodat opgaven in sub-folders ook
        worden gevonden.

        Sinds 2026-05-13 (sub-ronde B): retourneert ook een 'folders' lijst
        zodat lege folders zichtbaar zijn voor de UI. Voor nu alleen één
        niveau diep (direct onder root).
        """
        try:
            from json_exporter import OUTPUT_DIR
            from folder_manager import list_all_opgaven, list_folders
            opgaven = []
            for opg in list_all_opgaven(OUTPUT_DIR):
                fpath = opg['path']
                fname = os.path.basename(fpath)
                entry = {
                    'id': opg['id'],
                    'filename': fname,
                    'folder': opg['folder'],   # relatief pad onder OUTPUT_DIR
                    'corrupt': False,
                }
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    meta = data.get('metadata', {})
                    expr = meta.get('expressie', {})
                    entry['tekst'] = expr.get('tekst', '')
                    entry['latex'] = expr.get('latex', '')
                    entry['aantal_mathblocks'] = meta.get('aantal_mathblocks', 0)
                    entry['aantal_steps'] = meta.get('aantal_steps', 0)
                except Exception:
                    entry['corrupt'] = True
                opgaven.append(entry)

            # Folders: één niveau diep (direct onder root). Lege folders
            # worden hierdoor ook zichtbaar in de UI.
            folders = []
            tree = list_folders(OUTPUT_DIR)
            if tree:
                for child in tree.get('children', []):
                    folders.append({
                        'name': child['name'],
                        'opgave_count': child['opgave_count'],
                    })

            self._send_json({
                'success': True,
                'opgaven': opgaven,
                'folders': folders,
                'output_dir': OUTPUT_DIR,
            })
        except Exception as e:
            print(f"[FOUT] list_opgaven: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/load_opgave ──────────────────────────────────────────────────────
    def _handle_load_opgave(self):
        """Laad één opgave JSON + bijbehorende SVG op basis van ?id=X.

        Zoekt de opgave in de hele folder-boom via folder_manager.
        """
        try:
            from urllib.parse import urlparse, parse_qs
            from json_exporter import OUTPUT_DIR
            from folder_manager import find_opgave_path
            qs = parse_qs(urlparse(self.path).query)
            opgave_id = (qs.get('id') or [''])[0]
            if not opgave_id:
                self._send_json({'success': False, 'error': 'Geen id ontvangen'})
                return

            json_path = find_opgave_path(opgave_id, OUTPUT_DIR)
            if not json_path or not os.path.exists(json_path):
                self._send_json({'success': False, 'error': 'Opgave niet gevonden: ' + opgave_id})
                return
            svg_path = json_path.replace('.json', '.svg')

            with open(json_path, 'r', encoding='utf-8') as f:
                opgave = json.load(f)

            svg = ''
            if os.path.exists(svg_path):
                with open(svg_path, 'r', encoding='utf-8') as f:
                    svg = f.read()

            self._send_json({
                'success': True,
                'opgave': opgave,
                'svg': svg,
            })
        except Exception as e:
            print(f"[FOUT] load_opgave: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/check_export ─────────────────────────────────────────────────────
    def _handle_check_export(self):
        """
        Controleer of een LaTeX-expressie al bestaat in de output directory.
        Returns: { success, expression, output_dir, duplicates: [filename, ...] }
        """
        try:
            from json_exporter import OUTPUT_DIR
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            req = json.loads(body.decode('utf-8'))
            latex = req.get('latex', '')

            if not latex:
                self._send_json({'success': False, 'error': 'Geen expressie ontvangen'})
                return

            # Bepaal de "canonical" expressie zoals export dat ook zou doen
            expression = latex_to_expression(latex)

            # Zoek duplicaten: alle JSON-bestanden met zelfde expressie.tekst.
            # Scan de hele folder-boom, niet alleen de root.
            from folder_manager import list_all_opgaven
            duplicates = []
            for opg in list_all_opgaven(OUTPUT_DIR):
                fpath = opg['path']
                fname = os.path.basename(fpath)
                try:
                    with open(fpath, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    ex = data.get('metadata', {}).get('expressie', {})
                    bestaande_tekst = ex.get('tekst', '')
                    bestaande_latex = ex.get('latex', '')
                    if bestaande_tekst == expression or bestaande_latex == latex:
                        duplicates.append(fname)
                except Exception:
                    continue

            self._send_json({
                'success': True,
                'expression': expression,
                'output_dir': OUTPUT_DIR,
                'duplicates': duplicates,
            })
        except Exception as e:
            print(f"[FOUT] check_export: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/delete_opgave ────────────────────────────────────────────────────
    def _handle_delete_opgave(self):
        """Verwijder opgave-JSON en bijbehorende SVG."""
        try:
            from json_exporter import OUTPUT_DIR
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            req = json.loads(body.decode('utf-8'))
            opgave_id = req.get('id', '')

            if not opgave_id:
                self._send_json({'success': False, 'error': 'Geen id ontvangen'})
                return

            from folder_manager import find_opgave_path
            json_path = find_opgave_path(opgave_id, OUTPUT_DIR)
            if not json_path:
                self._send_json({'success': False, 'error': 'Opgave niet gevonden: ' + opgave_id})
                return
            svg_path = json_path.replace('.json', '.svg')

            removed = []
            if os.path.exists(json_path):
                os.remove(json_path)
                removed.append(os.path.basename(json_path))
            if os.path.exists(svg_path):
                os.remove(svg_path)
                removed.append(os.path.basename(svg_path))

            if not removed:
                self._send_json({'success': False, 'error': 'Opgave niet gevonden: ' + opgave_id})
                return

            print(f"[DELETE] {opgave_id}: verwijderd ({', '.join(removed)})")
            self._send_json({'success': True, 'removed': removed})
        except Exception as e:
            print(f"[FOUT] delete_opgave: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/save_hints ───────────────────────────────────────────────────────
    def _handle_save_hints(self):
        """
        Werk alleen het `hints` veld (en bij uitbreiding andere mathblock-velden
        die in de request staan) bij op een bestaande opgave.
        Body: { id: "opgave_...", mathblocks: [ ... volledige mathblocks ... ] }
        """
        try:
            from json_exporter import OUTPUT_DIR
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            req = json.loads(body.decode('utf-8'))

            opgave_id = req.get('id', '')
            new_mathblocks = req.get('mathblocks', [])

            if not opgave_id:
                self._send_json({'success': False, 'error': 'Geen id ontvangen'})
                return

            from folder_manager import find_opgave_path
            json_path = find_opgave_path(opgave_id, OUTPUT_DIR)
            if not json_path or not os.path.exists(json_path):
                self._send_json({'success': False, 'error': 'Opgave niet gevonden: ' + opgave_id})
                return

            # Laad huidige JSON
            with open(json_path, 'r', encoding='utf-8') as f:
                opgave = json.load(f)

            # Werk alleen de hints bij per mathblock (niet de rest)
            if not isinstance(new_mathblocks, list):
                self._send_json({'success': False, 'error': 'mathblocks moet een lijst zijn'})
                return

            hints_by_id = {}
            for mb in new_mathblocks:
                if isinstance(mb, dict) and 'id' in mb and 'hints' in mb:
                    hints_by_id[mb['id']] = mb['hints']

            # Merge terug in de opgave JSON
            updated = 0
            for mb in opgave.get('mathblocks', []):
                mb_id = mb.get('id')
                if mb_id in hints_by_id:
                    mb['hints'] = hints_by_id[mb_id]
                    updated += 1

            # Schrijf terug
            with open(json_path, 'w', encoding='utf-8') as f:
                json.dump(opgave, f, indent=2, ensure_ascii=False)

            print(f"[HINTS] {opgave_id}: {updated} mathblock hints bijgewerkt")
            self._send_json({'success': True, 'updated': updated})
        except Exception as e:
            print(f"[FOUT] save_hints: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/settings (GET) ───────────────────────────────────────────────────
    def _handle_get_settings(self):
        """Retourneer de huidige instellingen (output directory)."""
        try:
            from config import get_settings
            self._send_json({'success': True, 'settings': get_settings()})
        except Exception as e:
            print(f"[FOUT] get_settings: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/settings (POST) ──────────────────────────────────────────────────
    def _handle_set_settings(self):
        """
        Wijzig de instellingen.
        Body: { output_dir: "...", create_if_missing: bool }
        """
        try:
            from config import set_output_dir, get_settings
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            req = json.loads(body.decode('utf-8'))

            new_dir = req.get('output_dir', '')
            create  = bool(req.get('create_if_missing', False))

            result = set_output_dir(new_dir, create_if_missing=create)

            if result.get('status') == 'ok':
                print(f"[SETTINGS] output_dir gewijzigd naar: {result['output_dir']}"
                      + (" (aangemaakt)" if result.get('created') else ""))
                self._send_json({
                    'success': True,
                    'status': 'ok',
                    'settings': get_settings(),
                    'created': bool(result.get('created')),
                })
                return

            if result.get('status') == 'needs_confirmation':
                # Directory bestaat nog niet — vraag bevestiging aan UI
                self._send_json({
                    'success': False,
                    'status': 'needs_confirmation',
                    'output_dir': result.get('output_dir'),
                    'message': result.get('message'),
                })
                return

            # Echte fout
            self._send_json({
                'success': False,
                'status': 'error',
                'error': result.get('error', 'onbekende fout'),
            })
        except Exception as e:
            print(f"[FOUT] set_settings: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/folders/create ───────────────────────────────────────────────────
    def _handle_folder_create(self):
        """Maak een nieuwe folder onder de root.

        Body: {'name': 'Hoofdstuk 1'}
        Voor sub-ronde C: alleen folders direct onder root (geen nesting).
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            name = data.get('name', '').strip()
            if not name:
                self._send_json({'success': False, 'error': 'Geen naam opgegeven'})
                return
            from json_exporter import OUTPUT_DIR
            from folder_manager import create_folder
            result = create_folder(OUTPUT_DIR, name, OUTPUT_DIR)
            self._send_json(result)
        except Exception as e:
            print(f"[FOUT] folder_create: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/folders/rename ───────────────────────────────────────────────────
    def _handle_folder_rename(self):
        """Hernoem een folder.

        Body: {'folder': 'Oud naam', 'new_name': 'Nieuwe naam'}
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            folder_name = data.get('folder', '').strip()
            new_name = data.get('new_name', '').strip()
            if not folder_name or not new_name:
                self._send_json({'success': False, 'error': 'folder en new_name verplicht'})
                return
            from json_exporter import OUTPUT_DIR
            from folder_manager import rename_folder
            folder_path = os.path.join(OUTPUT_DIR, folder_name)
            result = rename_folder(folder_path, new_name, OUTPUT_DIR)
            self._send_json(result)
        except Exception as e:
            print(f"[FOUT] folder_rename: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/folders/delete ───────────────────────────────────────────────────
    def _handle_folder_delete(self):
        """Verwijder een lege folder.

        Body: {'folder': 'Hoofdstuk 1'}
        Faalt expliciet als folder niet leeg is.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            folder_name = data.get('folder', '').strip()
            if not folder_name:
                self._send_json({'success': False, 'error': 'folder verplicht'})
                return
            from json_exporter import OUTPUT_DIR
            from folder_manager import delete_folder
            folder_path = os.path.join(OUTPUT_DIR, folder_name)
            result = delete_folder(folder_path, OUTPUT_DIR)
            self._send_json(result)
        except Exception as e:
            print(f"[FOUT] folder_delete: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/folders/move ─────────────────────────────────────────────────────
    def _handle_folder_move(self):
        """Verplaats een folder naar een nieuwe parent.

        Body: {'folder': 'Hoofdstuk 1', 'new_parent': 'Klas 2'}
        new_parent leeg/None = root.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            folder_name = data.get('folder', '').strip()
            new_parent = data.get('new_parent', '').strip()
            if not folder_name:
                self._send_json({'success': False, 'error': 'folder verplicht'})
                return
            from json_exporter import OUTPUT_DIR
            from folder_manager import move_folder
            folder_path = os.path.join(OUTPUT_DIR, folder_name)
            new_parent_path = (os.path.join(OUTPUT_DIR, new_parent)
                               if new_parent else OUTPUT_DIR)
            result = move_folder(folder_path, new_parent_path, OUTPUT_DIR)
            self._send_json(result)
        except Exception as e:
            print(f"[FOUT] folder_move: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/folders/copy ─────────────────────────────────────────────────────
    def _handle_folder_copy(self):
        """Kopieer een folder (met inhoud) naar een nieuwe parent.

        Body: {'folder': 'Hoofdstuk 1', 'new_parent': '', 'new_name': 'Kopie'}
        new_parent leeg = root; new_name optioneel.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            folder_name = data.get('folder', '').strip()
            new_parent = data.get('new_parent', '').strip()
            new_name = data.get('new_name', '').strip() or None
            if not folder_name:
                self._send_json({'success': False, 'error': 'folder verplicht'})
                return
            from json_exporter import OUTPUT_DIR
            from folder_manager import copy_folder
            folder_path = os.path.join(OUTPUT_DIR, folder_name)
            new_parent_path = (os.path.join(OUTPUT_DIR, new_parent)
                               if new_parent else OUTPUT_DIR)
            result = copy_folder(folder_path, new_parent_path, OUTPUT_DIR,
                                 new_name=new_name)
            self._send_json(result)
        except Exception as e:
            print(f"[FOUT] folder_copy: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    # ── /api/move_opgave ──────────────────────────────────────────────────────
    def _handle_move_opgave(self):
        """Verplaats een opgave (JSON + SVG) naar een doel-folder.

        Body: {
          'id': 'opgave_20260513_001',
          'target_folder': 'Prullenbak',
          'source_folder': 'Trial'   (optioneel, eenduidig bij conflict)
        }
        Bij naam-conflict in doel-folder wordt een suffix toegevoegd.
        """
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            body = self.rfile.read(content_length)
            data = json.loads(body.decode('utf-8'))
            opgave_id = (data.get('id') or '').strip()
            target = (data.get('target_folder') or '').strip()
            source = data.get('source_folder')  # mag None zijn
            if not opgave_id or not target:
                self._send_json({'success': False,
                                 'error': 'id en target_folder verplicht'})
                return
            from json_exporter import OUTPUT_DIR
            from folder_manager import move_opgave_to_folder
            result = move_opgave_to_folder(
                opgave_id, target, OUTPUT_DIR, source_folder=source
            )
            self._send_json(result)
        except Exception as e:
            print(f"[FOUT] move_opgave: {e}")
            traceback.print_exc()
            self._send_json({'success': False, 'error': str(e)})

    def _send_json(self, data: dict):
        response = json.dumps(data, ensure_ascii=False)
        self.send_response(200)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Content-Length', str(len(response.encode('utf-8'))))
        self.end_headers()
        self.wfile.write(response.encode('utf-8'))

    def log_message(self, format, *args):
        if '/api/' in (args[0] if args else ''):
            super().log_message(format, *args)


if __name__ == '__main__':
    print(f"\n{'='*50}")
    print(f"  ForMath Web Server (AST Pipeline)")
    print(f"  Build: 2026-05-08 (pipeline-tak getallen/letters)")
    print(f"  http://localhost:{PORT}")
    print(f"{'='*50}\n")

    # Self-check imports zodat fouten direct zichtbaar zijn
    try:
        from mixed_number_injector import inject_mixed_number
        from simplify_injector import inject_simplify_ops
        print("[OK] mixed_number_injector geladen")
        print("[OK] simplify_injector geladen")
    except ImportError as e:
        print(f"[FOUT] Module ontbreekt: {e}")
        print(f"[FOUT] Server start NIET met volledige pipeline!")

    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), ForMathHandler) as httpd:
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            print("\n\nServer gestopt.")
