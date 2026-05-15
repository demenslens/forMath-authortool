#!/usr/bin/env python3
"""
ForQuest Manifold Detector - Fase 3
====================================

Detecteert ketens van commutatieve operaties die kandidaten zijn voor MANIFOLD conversie.

Detectie criteria:
1. Keten van dezelfde commutatieve operator (+ of ×)
2. Minimaal 3 operanden (anders blijft het BINAIR)
3. Allemaal in dezelfde tak (geen tak grenzen overschrijden)

Output: AST met annotaties voor manifold candidates

Volgens: ForQuest_Formalisatie_Proces_v3.pdf - Sectie 10.5 Fase 3
"""

from typing import Dict, Any, List, Tuple, Set
import copy


class ManifoldDetector:
    """
    Detecteert ketens van commutatieve operaties voor MANIFOLD conversie
    
    Een keten is een manifold candidate als:
    - 3 of meer inputs
    - Alle operators zijn hetzelfde (+ of ×)
    - Operator is commutatief
    
    Commutatieve operators: + en ×
    Niet-commutatieve: - en : (maar - is al genormaliseerd naar +(-x))
    """
    
    def __init__(self):
        self.manifold_candidates = []
        self.node_id_counter = 0
    
    def detect(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Detecteer manifold candidates in AST
        
        Args:
            ast: Genormaliseerde AST van ast_normalizer
        
        Returns:
            AST met manifold_candidate annotaties
        """
        # Reset
        self.manifold_candidates = []
        self.node_id_counter = 0
        
        # Annoteer nodes met IDs
        annotated = self._annotate_node_ids(ast)
        
        # Detecteer ketens
        self._detect_chains(annotated)
        
        # Voeg manifold annotaties toe
        result = self._add_manifold_annotations(annotated)
        
        return result
    
    def _annotate_node_ids(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Voeg unieke IDs toe aan elke node voor tracking"""
        node = copy.deepcopy(node)
        node['_node_id'] = self.node_id_counter
        self.node_id_counter += 1

        if node['type'] == 'BINARY_OP':
            node['left'] = self._annotate_node_ids(node['left'])
            node['right'] = self._annotate_node_ids(node['right'])
        elif node['type'] == 'UNARY_OP':
            node['operand'] = self._annotate_node_ids(node['operand'])
        elif node['type'] == 'POWER':
            node['base'] = self._annotate_node_ids(node['base'])
            node['exponent'] = self._annotate_node_ids(node['exponent'])
        elif node['type'] == 'ROOT':
            node['radicand'] = self._annotate_node_ids(node['radicand'])
            node['index'] = self._annotate_node_ids(node['index'])

        return node
    
    def _detect_chains(self, node: Dict[str, Any]) -> None:
        """
        Detecteer commutatieve ketens recursief
        
        Gaat door de AST en vindt ketens van + of ×
        
        BELANGRIJK: Detecteert OOK binnen is_negative nodes
        voor matryoshka structuren!
        """
        node_type = node['type']
        
        # Recursie eerst (bottom-up)
        if node_type == 'BINARY_OP':
            self._detect_chains(node['left'])
            self._detect_chains(node['right'])
        elif node_type == 'UNARY_OP':
            self._detect_chains(node['operand'])
        elif node_type == 'POWER':
            self._detect_chains(node.get('base', {}))
            self._detect_chains(node.get('exponent', {}))
        elif node_type == 'ROOT':
            self._detect_chains(node.get('radicand', {}))
            # index is een getal, geen verdere detectie nodig
        
        # Check of deze node een keten start
        if node_type == 'BINARY_OP':
            operator = node['operator']

            # Alleen commutatieve operators
            if operator in ['+', '×']:
                # Een is_negative of _bracketed node is atomisch voor de BUITENSTE keten,
                # maar mag WEL als root van zijn eigen binnenste keten dienen.
                # We verzamelen de keten van BINNEN de node (negeer eigen is_negative/_bracketed).
                if node.get('is_negative') or node.get('_bracketed'):
                    chain = self._collect_chain_inside_bracketed(node, operator)
                else:
                    chain = self._collect_chain(node, operator)

                # Manifold candidate als 3+ operanden
                if len(chain) >= 3:
                    self.manifold_candidates.append({
                        'node_id': node['_node_id'],
                        'operator': operator,
                        'operands': chain,
                        'count': len(chain)
                    })
    
    def _collect_chain(self, node: Dict[str, Any], target_op: str) -> List[Dict[str, Any]]:
        """
        Verzamel alle operanden in een keten van dezelfde operator.

        STOP bij:
        - Nodes met is_negative=True (genégeerde sub-expressies zijn atomisch)
        - Nodes met _bracketed=True (haakjes vormen een grens)
        - Nodes die niet de target operator hebben
        """
        # Haakjes vormen altijd een grens: atomisch behandelen
        if node.get('_bracketed'):
            return [node]

        # Negatieve sub-expressie: atomisch
        if node.get('is_negative'):
            return [node]

        # POWER is altijd atomisch — nooit openbreken
        if node['type'] == 'POWER':
            return [node]

        # ROOT is altijd atomisch — nooit openbreken
        if node['type'] == 'ROOT':
            return [node]

        if node['type'] != 'BINARY_OP' or node['operator'] != target_op:
            return [node]

        # Recursief verzamelen
        left_operands = self._collect_chain(node['left'], target_op)
        right_operands = self._collect_chain(node['right'], target_op)

        return left_operands + right_operands
    
    def _collect_chain_inside_negative(self, node: Dict[str, Any], target_op: str) -> List[Dict[str, Any]]:
        """
        Verzamel operanden BINNEN een is_negative node.
        Eigen is_negative genegeerd. Children met is_negative/_bracketed zijn atomisch.
        """
        if node.get('_bracketed'):
            return [node]
        if node['type'] != 'BINARY_OP' or node['operator'] != target_op:
            return [node]
        left_operands = self._collect_chain(node['left'], target_op)
        right_operands = self._collect_chain(node['right'], target_op)
        return left_operands + right_operands

    def _collect_chain_inside_bracketed(self, node: Dict[str, Any], target_op: str) -> List[Dict[str, Any]]:
        """
        Verzamel operanden BINNEN een is_negative of _bracketed node.
        Eigen is_negative EN _bracketed worden genegeerd (we zijn de root).
        Children met is_negative of _bracketed zijn atomisch.
        """
        if node['type'] != 'BINARY_OP' or node['operator'] != target_op:
            return [node]
        left_operands = self._collect_chain(node['left'], target_op)
        right_operands = self._collect_chain(node['right'], target_op)
        return left_operands + right_operands
    
    def _add_manifold_annotations(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Voeg manifold_candidate annotaties toe aan relevante nodes
        """
        # Check of deze node een manifold candidate is
        is_candidate = False
        candidate_info = None
        
        for candidate in self.manifold_candidates:
            if node.get('_node_id') == candidate['node_id']:
                is_candidate = True
                candidate_info = candidate
                break
        
        if is_candidate:
            node['_manifold_candidate'] = True
            node['_manifold_operator'] = candidate_info['operator']
            node['_manifold_operand_count'] = candidate_info['count']
        
        # Recursie
        if node['type'] == 'BINARY_OP':
            node['left'] = self._add_manifold_annotations(node['left'])
            node['right'] = self._add_manifold_annotations(node['right'])
        elif node['type'] == 'UNARY_OP':
            node['operand'] = self._add_manifold_annotations(node['operand'])
        
        return node
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourneer detectie statistieken"""
        plus_chains = [c for c in self.manifold_candidates if c['operator'] == '+']
        mult_chains = [c for c in self.manifold_candidates if c['operator'] == '×']
        
        return {
            'total_candidates': len(self.manifold_candidates),
            'plus_chains': len(plus_chains),
            'multiply_chains': len(mult_chains),
            'largest_chain': max([c['count'] for c in self.manifold_candidates]) if self.manifold_candidates else 0,
            'candidates': self.manifold_candidates
        }


def detect_manifolds(ast: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Detecteer manifold candidates in een AST
    
    Args:
        ast: Genormaliseerde AST (van ast_normalizer)
    
    Returns:
        Tuple van (annotated_ast, statistics)
    
    Example:
        >>> from expression_parser import parse_expression
        >>> from ast_normalizer import normalize_ast
        >>> ast = parse_expression("1/2+1/3+1/4")
        >>> normalized = normalize_ast(ast)
        >>> annotated, stats = detect_manifolds(normalized)
        >>> stats['total_candidates']  # Should be 1 (the + chain with 3 operands)
    """
    detector = ManifoldDetector()
    annotated = detector.detect(ast)
    stats = detector.get_statistics()
    
    return annotated, stats


def remove_annotations(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verwijder interne annotaties (_node_id, _manifold_candidate, etc.)
    
    Handig voor clean output
    """
    node = copy.deepcopy(node)
    
    # Verwijder underscore keys
    keys_to_remove = [k for k in node.keys() if k.startswith('_')]
    for key in keys_to_remove:
        del node[key]
    
    # Recursie
    if node['type'] == 'BINARY_OP':
        node['left'] = remove_annotations(node['left'])
        node['right'] = remove_annotations(node['right'])
    elif node['type'] == 'UNARY_OP':
        node['operand'] = remove_annotations(node['operand'])
    
    return node


# ============================================================================
# HELPER FUNCTIES - Visualisatie
# ============================================================================

def visualize_candidates(ast: Dict[str, Any], stats: Dict[str, Any]) -> str:
    """
    Maak visuele representatie van manifold candidates
    """
    from ast_normalizer import ast_to_string
    
    lines = []
    lines.append("MANIFOLD CANDIDATES DETECTED:")
    lines.append("=" * 70)
    
    if stats['total_candidates'] == 0:
        lines.append("Geen manifold candidates gevonden.")
        return '\n'.join(lines)
    
    lines.append(f"Totaal: {stats['total_candidates']}")
    lines.append(f"  + ketens: {stats['plus_chains']}")
    lines.append(f"  × ketens: {stats['multiply_chains']}")
    lines.append(f"  Grootste keten: {stats['largest_chain']} operanden")
    lines.append("")
    
    for i, candidate in enumerate(stats['candidates'], 1):
        lines.append(f"Candidate {i}:")
        lines.append(f"  Operator: {candidate['operator']}")
        lines.append(f"  Operanden: {candidate['count']}")
        lines.append(f"  Operand waarden:")
        for j, operand in enumerate(candidate['operands'], 1):
            operand_str = ast_to_string(operand)
            lines.append(f"    {j}. {operand_str}")
        lines.append("")
    
    return '\n'.join(lines)


# ============================================================================
# TESTING & VOORBEELDEN
# ============================================================================

if __name__ == "__main__":
    try:
        from expression_parser import parse_expression
        from ast_normalizer import normalize_ast, ast_to_string
    except ImportError as e:
        print(f"ERROR: Kan modules niet importeren: {e}")
        print("Zorg dat expression_parser.py en ast_normalizer.py in dezelfde directory staan")
        exit(1)
    
    import json
    
    print("=" * 80)
    print("FORQUEST MANIFOLD DETECTOR - FASE 3")
    print("=" * 80)
    print()
    
    # Test cases
    test_cases = [
        ("1/2+1/3", "2 operanden - GEEN manifold (moet BINAIR blijven)"),
        ("1/2+1/3+1/4", "3 operanden - WEL manifold"),
        ("1/2+1/3+1/4+1/5", "4 operanden - WEL manifold"),
        ("1×2×3×4", "4 operanden vermenigvuldiging - WEL manifold"),
        ("1+2×3", "Gemengde operators - GEEN manifold"),
        ("(1+2)×(3+4)", "Twee aparte ketens"),
        ("1/9-(3/2+5/6)+2/3", "Mix met haakjes"),
        ("1/2+1/3+1/4+1/5+1/6", "5 operanden - grote manifold"),
    ]
    
    for expr, description in test_cases:
        print(f"\n{description}")
        print(f"Expressie: {expr}")
        print("-" * 70)
        
        # Parse en normaliseer
        ast = parse_expression(expr)
        normalized = normalize_ast(ast)
        
        print(f"Genormaliseerd: {ast_to_string(normalized)}")
        
        # Detecteer
        annotated, stats = detect_manifolds(normalized)
        
        # Resultaat
        if stats['total_candidates'] > 0:
            print(f"✓ {stats['total_candidates']} manifold candidate(s) gevonden:")
            for candidate in stats['candidates']:
                op_count = candidate['count']
                op_type = candidate['operator']
                print(f"  • {op_type} keten met {op_count} operanden")
        else:
            print("○ Geen manifold candidates (blijft BINAIR)")
        
        print()
    
    print("=" * 80)
    print("GEDETAILLEERD VOORBEELD")
    print("=" * 80)
    print()
    
    # Gedetailleerd voorbeeld
    expr = "1/2+1/3+1/4+1/5"
    print(f"Expressie: {expr}")
    print()
    
    ast = parse_expression(expr)
    normalized = normalize_ast(ast)
    annotated, stats = detect_manifolds(normalized)
    
    print(visualize_candidates(annotated, stats))
    
    print("=" * 80)
    print("✓ FASE 3 COMPLEET")
    print("=" * 80)
    print()
    print("Detectie criteria:")
    print("  ✓ Commutatieve operator (+ of ×)")
    print("  ✓ Minimaal 3 operanden")
    print("  ✓ Zelfde operator door hele keten")
    print()
    print("Volgende stap: Fase 4 - manifold_converter.py")
    print("  - Transformeer binaire ketens → manifold nodes")
    print("  - Behoud niet-commutatieve ketens als binair")
    print("  - Genereer finale AST voor SVG generator")


# ============================================================================
# MATROESJKA DETECTOR
# ============================================================================

def _collect_matroesjka_chain(node, chain=None):
    """
    Verzamel een links-associatieve keten van BINARY_OP(: of ×) nodes.
    
    Een Matroesjka keten is een reeks van minstens 3 opeenvolgende
    binaire bewerkingen (: of ×) waarbij de linker operand steeds de
    uitkomst van de vorige bewerking is.
    
    Structuur in AST (links-associatief):
        ((A:B):C)×D  →  keten [A:B, :C, ×D]
    
    Returns lijst van dicts: [
        {'operator': ':', 'left': node_A, 'right': node_B, 'node': root_node},  # schil 1
        {'operator': ':', 'right': node_C, 'node': ...},                         # schil 2
        {'operator': '×', 'right': node_D, 'node': ...},                         # schil 3
    ]
    """
    if chain is None:
        chain = []

    t = node.get('type')
    op = node.get('operator', '')

    # Alleen niet-bracketed BINARY_OP met : of × hoort in de keten
    if t == 'BINARY_OP' and op in (':', '×') and not node.get('_bracketed') and not node.get('is_negative'):
        left_node = node.get('left', {})
        right_node = node.get('right', {})

        # Ga eerst recursief de linkerkant in
        _collect_matroesjka_chain(left_node, chain)

        # Voeg deze node toe aan de keten
        entry = {
            'operator': op,
            'right': right_node,
            'node_id': node.get('_node_id'),
            'node': node,
        }
        # De eerste schil heeft ook een linker operand (de initiële waarde)
        if not chain:
            entry['left'] = left_node
        chain.append(entry)
    # Anders: stop — dit is een atomische node (basis van de keten)
    return chain


def _find_all_matroesjka_chains(node, results=None):
    """
    Zoek recursief alle Matroesjka ketens in de AST.
    Een keten is alleen een Matroesjka als hij minstens 3 schillen heeft.
    """
    if results is None:
        results = []

    t = node.get('type')
    op = node.get('operator', '')

    if t == 'BINARY_OP' and op in (':', '×') and not node.get('_bracketed') and not node.get('is_negative'):
        # Probeer een keten te bouwen vanaf deze node als wortel
        chain = _collect_matroesjka_chain(node, [])
        if len(chain) >= 3:
            # Controleer of dit de langste keten is (niet een sub-keten)
            # door te checken of de ouder-node zelf ook in een keten zit
            results.append({
                'root_node_id': node.get('_node_id'),
                'shells': chain,
                'shell_count': len(chain),
            })
            # Ga NIET verder de linkerkant in — die is al onderdeel van deze keten
            # Wel de rechterkant afzoeken voor geneste structuren
            _find_all_matroesjka_chains(node.get('right', {}), results)
        else:
            # Keten te kort: zoek verder in beide kinderen
            _find_all_matroesjka_chains(node.get('left', {}), results)
            _find_all_matroesjka_chains(node.get('right', {}), results)
    else:
        # Geen keten-node: zoek verder in kinderen
        for k in ['left', 'right', 'base', 'radicand']:
            if k in node:
                _find_all_matroesjka_chains(node[k], results)
        for operand in node.get('operands', []):
            _find_all_matroesjka_chains(operand, results)

    return results


def _annotate_matroesjka(node, chain_root_ids):
    """
    Annoteer de root-node van elke Matroesjka keten met _matroesjka_root=True.
    """
    node_id = node.get('_node_id')
    if node_id in chain_root_ids:
        node['_matroesjka_root'] = True

    t = node.get('type')
    if t == 'BINARY_OP':
        _annotate_matroesjka(node.get('left', {}), chain_root_ids)
        _annotate_matroesjka(node.get('right', {}), chain_root_ids)
    elif t == 'MANIFOLD_OP':
        for op in node.get('operands', []):
            _annotate_matroesjka(op, chain_root_ids)
    elif t == 'POWER':
        _annotate_matroesjka(node.get('base', {}), chain_root_ids)
    elif t == 'ROOT':
        _annotate_matroesjka(node.get('radicand', {}), chain_root_ids)

    return node


def detect_matroesjka(ast):
    """
    Detecteer Matroesjka manifold ketens in de AST (na manifold conversie).
    
    Een Matroesjka keten is een links-associatieve reeks van minstens 3
    opeenvolgende BINARY_OP(: of ×) bewerkingen.
    
    Args:
        ast: AST na manifold_converter
    
    Returns:
        Tuple (annotated_ast, matroesjka_chains) waarbij:
        - annotated_ast: AST met _matroesjka_root annotaties
        - matroesjka_chains: lijst van keten-beschrijvingen
    """
    import copy
    ast = copy.deepcopy(ast)

    chains = _find_all_matroesjka_chains(ast)

    # Dedupliceer: verwijder sub-ketens (ketens waarvan de root onderdeel
    # is van een langere keten)
    all_node_ids_in_chains = {}
    for chain in chains:
        for shell in chain['shells']:
            nid = shell.get('node_id')
            if nid is not None:
                if nid not in all_node_ids_in_chains:
                    all_node_ids_in_chains[nid] = chain['root_node_id']
                elif chain['shell_count'] > chains[0]['shell_count']:
                    all_node_ids_in_chains[nid] = chain['root_node_id']

    # Bewaar alleen de langste keten per overlappende groep
    unique_chains = []
    seen_roots = set()
    for chain in sorted(chains, key=lambda c: -c['shell_count']):
        root_id = chain['root_node_id']
        if root_id not in seen_roots:
            # Controleer dat geen van de shells al in een langere keten zit
            shell_ids = {s.get('node_id') for s in chain['shells']}
            overlap = shell_ids & seen_roots
            if not overlap:
                unique_chains.append(chain)
                seen_roots.add(root_id)

    # Annoteer root nodes
    root_ids = {c['root_node_id'] for c in unique_chains}
    ast = _annotate_matroesjka(ast, root_ids)

    return ast, unique_chains
