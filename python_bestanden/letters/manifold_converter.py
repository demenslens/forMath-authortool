#!/usr/bin/env python3
"""
ForQuest Manifold Converter - Fase 4
=====================================

Converteert binaire ketens naar MANIFOLD nodes in de AST.

Transformaties:
- Binaire keten (3+ operanden) → MANIFOLD node
- Behoudt niet-commutatieve ketens als BINAIR
- Kiest grootste keten bij overlappende candidates

Output: AST met MANIFOLD_OP nodes

Volgens: ForQuest_Formalisatie_Proces_v3.pdf - Sectie 10.5 Fase 4
"""

from typing import Dict, Any, List, Set, Tuple
import copy


class ManifoldConverter:
    """
    Converteert gedetecteerde manifold candidates naar MANIFOLD_OP nodes
    
    Strategie:
    1. Sorteer candidates op grootte (grootste eerst)
    2. Converteer grootste ketens
    3. Skip overlappende kleinere ketens
    4. Behoud binaire operaties voor kleine ketens (< 3 operanden)
    """
    
    def __init__(self):
        self.converted_nodes = set()  # Track welke nodes al geconverteerd zijn
        self.conversion_log = []
    
    def convert(self, ast: Dict[str, Any], detection_stats: Dict[str, Any]) -> Dict[str, Any]:
        """
        Converteer manifold candidates in AST
        
        Strategie: BOTTOM-UP met OVERLAP FILTERING
        - Filter kandidaten die volledig binnen andere kandidaten zitten
        - Behoud alleen "maximale" kandidaten
        - Converteer van klein naar groot
        
        Args:
            ast: AST met manifold_candidate annotaties (van detector)
            detection_stats: Statistieken van manifold_detector
        
        Returns:
            AST met MANIFOLD_OP nodes
        """
        # Reset
        self.converted_nodes = set()
        self.conversion_log = []
        
        # Filter overlappende kandidaten
        candidates = self._filter_overlapping_candidates(detection_stats['candidates'])
        
        # Sorteer candidates BOTTOM-UP (kleinste eerst)
        candidates = sorted(candidates, key=lambda c: c['count'], reverse=False)
        
        # Converteer
        result = self._convert_node(ast, candidates)
        
        return result
    
    def _filter_overlapping_candidates(self, candidates: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        """
        Matryoshka filtering: behoud kandidaten op verschillende boom takken.
        
        Skip een kandidaat ALLEEN als het INCREMENTEEL groter is dan
        een directe child (verschil van 1-2 operands).
        
        Behoud kandidaten die een GROTE SPRONG maken (semantische grenzen).
        """
        if not candidates:
            return []
        
        filtered = []
        
        for cand in candidates:
            # Check of er een kandidaat is die PRECIES 1 groter is
            # met exact dezelfde operands + 1 extra
            should_skip = False
            cand_ops = set(op.get('_node_id') for op in cand['operands'] if op.get('_node_id'))
            
            for other in candidates:
                if other['count'] == cand['count'] + 1:
                    other_ops = set(op.get('_node_id') for op in other['operands'] if op.get('_node_id'))
                    
                    # Als other exact 1 operand meer heeft EN alle cand ops bevat
                    if cand_ops and cand_ops.issubset(other_ops) and len(other_ops - cand_ops) == 1:
                        # Dit is incrementele groei - skip cand
                        should_skip = True
                        break
            
            if not should_skip:
                filtered.append(cand)
        
        return filtered
    
    def _convert_node(self, node: Dict[str, Any], candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Recursief converteren van nodes - BOTTOM-UP
        
        Eerst children converteren (bottom-up), dan parent
        """
        node_id = node.get('_node_id')
        
        # Skip als al geconverteerd
        if node_id in self.converted_nodes:
            return node
        
        # BOTTOM-UP: Eerst recursie naar children (diepste eerst)
        if node['type'] == 'BINARY_OP':
            node['left'] = self._convert_node(node['left'], candidates)
            node['right'] = self._convert_node(node['right'], candidates)
        elif node['type'] == 'UNARY_OP':
            node['operand'] = self._convert_node(node['operand'], candidates)
        elif node['type'] == 'POWER':
            node['base'] = self._convert_node(node.get('base', {}), candidates)
            # exponent wordt niet geconverteerd (altijd een getal)
        elif node['type'] == 'ROOT':
            node['radicand'] = self._convert_node(node.get('radicand', {}), candidates)
            # index wordt niet geconverteerd (altijd een getal)
        
        # Dan pas deze node zelf converteren
        candidate = self._find_candidate(node_id, candidates)
        
        if candidate and self._should_convert(candidate, node):
            # Converteer naar MANIFOLD
            manifold_node = self._create_manifold_node(candidate, node)
            
            # Mark als geconverteerd (maar NIET de operands - die zijn al verwerkt!)
            self.converted_nodes.add(node_id)
            
            # Log conversie
            self.conversion_log.append({
                'node_id': node_id,
                'operator': candidate['operator'],
                'operand_count': candidate['count'],
                'type': 'MANIFOLD'
            })
            
            return manifold_node
        
        return node
    
    def _find_candidate(self, node_id: int, candidates: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Vind candidate voor deze node ID"""
        for candidate in candidates:
            if candidate['node_id'] == node_id:
                return candidate
        return None
    
    def _should_convert(self, candidate: Dict[str, Any], node: Dict[str, Any]) -> bool:
        """
        Bepaal of deze candidate geconverteerd moet worden
        
        Criteria:
        - Minimaal 3 operanden
        - Node zelf mag niet al geconverteerd zijn
        - NIEUW: Skip als direct children al MANIFOLD_OP zijn
                (voorkomt MANIFOLD(MANIFOLD(...)) zonder semantische reden)
        """
        # Minimaal 3 operanden
        if candidate['count'] < 3:
            return False
        
        # Deze node zelf mag niet al geconverteerd zijn
        node_id = node.get('_node_id')
        if node_id in self.converted_nodes:
            return False
        
        # Een is_negative BINARY_OP zónder _bracketed is een aftrekking — nooit converteren.
        # Een is_negative BINARY_OP MÉT _bracketed is een negatief haakjesblok — wél converteren.
        if node.get('is_negative') and node.get('type') == 'BINARY_OP' and not node.get('_bracketed'):
            return False

        return True
    
    def _create_manifold_node(self, candidate: Dict[str, Any], original_node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Creëer een MANIFOLD_OP node
        
        BELANGRIJK: Herbouw operands door de boom te volgen.
        Stop bij MANIFOLD_OP nodes (al geconverteerde substructuren).
        Dit respecteert haakjes prioriteit!
        
        SPECIAAL: Als deze node zelf is_negative heeft, moet hij WEL uitgepakt
        worden (net als in de detector met _collect_chain_ignore_negative).
        """
        # Herbouw operands door de HUIDIGE boom te volgen
        operator = candidate['operator']
        
        # Als deze node zelf is_negative of _bracketed heeft: negeer die flag bij uitpakken,
        # maar respecteer is_negative/_bracketed van children (die zijn atomisch).
        if original_node.get('is_negative') or original_node.get('_bracketed'):
            rebuilt_operands = self._rebuild_operands_inside_bracketed(original_node, operator)
        else:
            rebuilt_operands = self._rebuild_operands(original_node, operator)
        
        manifold = {
            'type': 'MANIFOLD_OP',
            'operator': operator,
            'operands': rebuilt_operands,
            'operand_count': len(rebuilt_operands)
        }
        
        # Behoud is_negative van de originele node
        if original_node.get('is_negative'):
            manifold['is_negative'] = True
        
        # Behoud _bracketed van de originele node zodat buitenste keten grens respecteert
        if original_node.get('_bracketed'):
            manifold['_bracketed'] = True
        
        # Behoud node_id voor tracking
        if '_node_id' in original_node:
            manifold['_node_id'] = original_node['_node_id']
        
        return manifold
    
    def _rebuild_operands(self, node: Dict[str, Any], target_op: str) -> List[Dict[str, Any]]:
        """
        Herbouw operands lijst door de boom te volgen.
        
        STOP bij:
        - MANIFOLD_OP nodes (al geconverteerd, behoud als geheel)
        - Nodes met is_negative=True EN leaf children (atomisch)
        - Andere node types (geen BINARY_OP met target_op)
        
        STRUCTURELE REGELS:
        1. Een genégeerde operatie -(a+b) met leaf operands is atomisch
        2. MAAR: -(MANIFOLD + MANIFOLD) moet WEL uitgepakt worden
           omdat de MANIFOLDs zelf al semantische eenheden zijn
        """
        # Als dit een MANIFOLD_OP is, return als geheel
        if node.get('type') == 'MANIFOLD_OP':
            return [self._clean_annotations(node)]

        # Haakjes vormen een grens: atomisch behandelen
        if node.get('_bracketed'):
            return [self._clean_annotations(node)]

        # POWER is altijd atomisch — nooit openbreken
        if node.get('type') == 'POWER':
            return [self._clean_annotations(node)]

        # ROOT is altijd atomisch — nooit openbreken
        if node.get('type') == 'ROOT':
            return [self._clean_annotations(node)]

        # is_negative maakt een node ALTIJD atomisch voor de buitenste keten.
        # Een is_negative node wordt nooit opengebroken vanuit _rebuild_operands.
        # (Alleen _rebuild_operands_inside_negative mag een is_negative node uitpakken,
        #  en alleen als die node zelf als manifold-root is aangewezen.)
        if node.get('is_negative'):
            return [self._clean_annotations(node)]
        
        # Als dit niet de target operator is, return als geheel
        if node.get('type') != 'BINARY_OP' or node.get('operator') != target_op:
            return [self._clean_annotations(node)]
        
        # Dit is een BINARY_OP met target operator EN NIET negatief
        # Recursief verzamelen
        left_ops = self._rebuild_operands(node.get('left', {}), target_op)
        right_ops = self._rebuild_operands(node.get('right', {}), target_op)
        
        return left_ops + right_ops
    
    def _rebuild_operands_inside_negative(self, node: Dict[str, Any], target_op: str) -> List[Dict[str, Any]]:
        """
        Rebuild operands voor een node die ZELF is_negative heeft maar als MANIFOLD root dient.
        Eigen is_negative genegeerd. Children met is_negative/_bracketed zijn atomisch.
        """
        if node.get('type') == 'MANIFOLD_OP':
            return [self._clean_annotations(node)]
        if node.get('_bracketed'):
            return [self._clean_annotations(node)]
        if node.get('type') != 'BINARY_OP' or node.get('operator') != target_op:
            return [self._clean_annotations(node)]
        left_ops = self._rebuild_operands(node.get('left', {}), target_op)
        right_ops = self._rebuild_operands(node.get('right', {}), target_op)
        return left_ops + right_ops

    def _rebuild_operands_inside_bracketed(self, node: Dict[str, Any], target_op: str) -> List[Dict[str, Any]]:
        """
        Rebuild operands voor een node die is_negative OF _bracketed heeft als MANIFOLD root.
        Eigen is_negative EN _bracketed worden genegeerd (we zijn de root).
        Children met is_negative of _bracketed zijn atomisch.
        """
        if node.get('type') == 'MANIFOLD_OP':
            return [self._clean_annotations(node)]
        if node.get('type') != 'BINARY_OP' or node.get('operator') != target_op:
            return [self._clean_annotations(node)]
        left_ops = self._rebuild_operands(node.get('left', {}), target_op)
        right_ops = self._rebuild_operands(node.get('right', {}), target_op)
        return left_ops + right_ops
    
    def _clean_annotations(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Verwijder manifold-specifieke annotaties"""
        node = copy.deepcopy(node)
        
        # Verwijder detectie annotaties
        keys_to_remove = ['_manifold_candidate', '_manifold_operator', '_manifold_operand_count']
        for key in keys_to_remove:
            if key in node:
                del node[key]
        
        # Recursie
        if node['type'] == 'BINARY_OP':
            node['left'] = self._clean_annotations(node['left'])
            node['right'] = self._clean_annotations(node['right'])
        elif node['type'] == 'UNARY_OP':
            node['operand'] = self._clean_annotations(node['operand'])
        
        return node
    
    def get_statistics(self) -> Dict[str, Any]:
        """Retourneer conversie statistieken"""
        manifold_count = sum(1 for log in self.conversion_log if log['type'] == 'MANIFOLD')
        
        return {
            'total_conversions': len(self.conversion_log),
            'manifold_nodes': manifold_count,
            'conversions': self.conversion_log
        }


def convert_to_manifolds(ast: Dict[str, Any], detection_stats: Dict[str, Any]) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Converteer AST met manifold candidates naar finale AST met MANIFOLD nodes
    
    Args:
        ast: Geannoteerde AST (van manifold_detector)
        detection_stats: Detectie statistieken
    
    Returns:
        Tuple van (converted_ast, conversion_stats)
    
    Example:
        >>> from expression_parser import parse_expression
        >>> from ast_normalizer import normalize_ast
        >>> from manifold_detector import detect_manifolds
        >>> 
        >>> ast = parse_expression("1/2+1/3+1/4")
        >>> normalized = normalize_ast(ast)
        >>> annotated, det_stats = detect_manifolds(normalized)
        >>> converted, conv_stats = convert_to_manifolds(annotated, det_stats)
        >>> converted['type']  # Should be 'MANIFOLD_OP'
    """
    converter = ManifoldConverter()
    converted = converter.convert(ast, detection_stats)
    stats = converter.get_statistics()
    
    return converted, stats


def remove_all_annotations(node: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verwijder ALLE annotaties (_node_id, etc.) voor clean output
    """
    node = copy.deepcopy(node)
    
    # Verwijder underscore keys
    keys_to_remove = [k for k in node.keys() if k.startswith('_')]
    for key in keys_to_remove:
        del node[key]
    
    # Recursie
    if node['type'] == 'BINARY_OP':
        node['left'] = remove_all_annotations(node['left'])
        node['right'] = remove_all_annotations(node['right'])
    elif node['type'] == 'UNARY_OP':
        node['operand'] = remove_all_annotations(node['operand'])
    elif node['type'] == 'MANIFOLD_OP':
        node['operands'] = [remove_all_annotations(op) for op in node['operands']]
    
    return node


# ============================================================================
# HELPER FUNCTIES - Visualisatie
# ============================================================================

def ast_to_string(node: Dict[str, Any]) -> str:
    """
    Converteer AST (inclusief MANIFOLD) naar leesbare string
    """
    node_type = node['type']
    
    if node_type == 'NUMBER':
        return str(node['value'])
    
    if node_type == 'FRACTION':
        return f"{node['numerator']}/{node['denominator']}"
    
    if node_type == 'UNARY_OP':
        from ast_normalizer import ast_to_string as norm_to_string
        operand_str = ast_to_string(node['operand'])
        if node['operand']['type'] in ['BINARY_OP', 'MANIFOLD_OP']:
            operand_str = f"({operand_str})"
        return f"{node['operator']}{operand_str}"
    
    if node_type == 'BINARY_OP':
        from ast_normalizer import ast_to_string as norm_to_string
        return norm_to_string(node)
    
    if node_type == 'MANIFOLD_OP':
        # MANIFOLD(op1, op2, op3, ...)
        operand_strs = [ast_to_string(op) for op in node['operands']]
        operator = node['operator']
        operands_joined = f" {operator} ".join(operand_strs)
        return f"MANIFOLD({operands_joined})"
    
    return str(node)


# ============================================================================
# COMPLETE PIPELINE FUNCTIE
# ============================================================================

def parse_and_convert(expression: str) -> Tuple[Dict[str, Any], Dict[str, Any]]:
    """
    Complete pipeline: expressie → MANIFOLD AST
    
    Voert alle fasen uit:
    1. Parsing
    2. Normalisatie
    3. Detectie
    4. Conversie
    
    Args:
        expression: Wiskundige expressie string
    
    Returns:
        Tuple van (final_ast, pipeline_stats)
    """
    from expression_parser import parse_expression
    from ast_normalizer import normalize_ast
    from manifold_detector import detect_manifolds
    
    # Fase 1: Parse
    ast = parse_expression(expression)
    
    # Fase 2: Normaliseer
    normalized = normalize_ast(ast)
    
    # Fase 3: Detecteer
    annotated, detection_stats = detect_manifolds(normalized)
    
    # Fase 4: Converteer
    converted, conversion_stats = convert_to_manifolds(annotated, detection_stats)
    
    # Clean output
    final = remove_all_annotations(converted)
    
    # Stats
    stats = {
        'expression': expression,
        'detection': detection_stats,
        'conversion': conversion_stats
    }
    
    return final, stats


# ============================================================================
# TESTING & VOORBEELDEN
# ============================================================================

if __name__ == "__main__":
    try:
        from expression_parser import parse_expression
        from ast_normalizer import normalize_ast
        from manifold_detector import detect_manifolds
    except ImportError as e:
        print(f"ERROR: Kan modules niet importeren: {e}")
        exit(1)
    
    import json
    
    print("=" * 80)
    print("FORQUEST MANIFOLD CONVERTER - FASE 4")
    print("=" * 80)
    print()
    
    # Test cases
    test_cases = [
        ("1/2+1/3", "2 operanden - blijft BINAIR"),
        ("1/2+1/3+1/4", "3 operanden - wordt MANIFOLD"),
        ("1/2+1/3+1/4+1/5", "4 operanden - wordt MANIFOLD"),
        ("1×2×3×4", "4 vermenigvuldiging - wordt MANIFOLD"),
        ("(1+2)×(3+4)", "Twee aparte binaire ops"),
        ("1/9-(3/2+5/6)+2/3", "Complex met haakjes"),
        ("1/2+1/3+1/4+1/5+1/6", "5 operanden - grote MANIFOLD"),
    ]
    
    for expr, description in test_cases:
        print(f"\n{description}")
        print(f"Expressie: {expr}")
        print("-" * 70)
        
        # Volledige pipeline
        final_ast, stats = parse_and_convert(expr)
        
        # Resultaat
        print(f"Resultaat: {ast_to_string(final_ast)}")
        
        if stats['conversion']['manifold_nodes'] > 0:
            print(f"✓ {stats['conversion']['manifold_nodes']} MANIFOLD node(s) aangemaakt")
            for conv in stats['conversion']['conversions']:
                print(f"  • {conv['operator']} met {conv['operand_count']} operanden")
        else:
            print("○ Geen MANIFOLD conversie (blijft BINAIR)")
        
        print()
    
    print("=" * 80)
    print("GEDETAILLEERD VOORBEELD")
    print("=" * 80)
    print()
    
    # Gedetailleerd voorbeeld
    expr = "1/2+1/3+1/4+1/5"
    print(f"Expressie: {expr}")
    print()
    
    final_ast, stats = parse_and_convert(expr)
    
    print("VOOR conversie (genormaliseerd):")
    print("  ((1/2 + 1/3) + 1/4) + 1/5  [Binaire boom]")
    print()
    
    print("NA conversie:")
    print(f"  {ast_to_string(final_ast)}")
    print()
    
    print("Finale AST structuur:")
    print(json.dumps(final_ast, indent=2))
    print()
    
    print("=" * 80)
    print("✓ FASE 4 COMPLEET")
    print("=" * 80)
    print()
    print("Transformaties:")
    print("  ✓ Binaire keten (3+ ops) → MANIFOLD_OP")
    print("  ✓ Kleine ketens (2 ops) → blijven BINARY_OP")
    print("  ✓ Niet-commutatief → blijft BINARY_OP")
    print()
    print("Volgende stap: Fase 5 - ast_validator.py")
    print("  - Valideer dat conversie correct resultaat geeft")
    print("  - Check volgorde bij niet-commutatieve operaties")
    print()
    print("=" * 80)
    print("COMPLETE PIPELINE NU BRUIKBAAR!")
    print("=" * 80)
    print()
    print("Gebruik: parse_and_convert('1/2+1/3+1/4')")
    print("  → Geeft finale AST met MANIFOLD nodes")


# ============================================================================
# MATROESJKA CONVERTER
# ============================================================================

def _replace_matroesjka_node(node, chain, depth=0):
    """
    Vervang de root-node van een Matroesjka keten door een MATROESJKA_OP node.
    Werkt recursief door de AST.
    """
    import copy

    if node.get('_matroesjka_root'):
        # Bouw de MATROESJKA_OP node
        shells = chain['shells']
        shell_list = []

        for i, shell in enumerate(shells):
            s = {
                'operator': shell['operator'],
                'right': _clean_matroesjka_annotations(copy.deepcopy(shell['right'])),
            }
            if i == 0:
                # Eerste schil: heeft ook een linker (initiële) waarde
                s['left'] = _clean_matroesjka_annotations(copy.deepcopy(shell['left']))
            shell_list.append(s)

        return {
            'type': 'MATROESJKA_OP',
            'shells': shell_list,
            'shell_count': len(shell_list),
            'is_negative': node.get('is_negative', False),
            '_bracketed': node.get('_bracketed', False),
        }

    # Recursief verder zoeken
    t = node.get('type')
    if t == 'BINARY_OP':
        node['left'] = _replace_matroesjka_node(node['left'], chain, depth+1)
        node['right'] = _replace_matroesjka_node(node['right'], chain, depth+1)
    elif t == 'MANIFOLD_OP':
        node['operands'] = [_replace_matroesjka_node(op, chain, depth+1)
                            for op in node.get('operands', [])]
    elif t == 'POWER':
        node['base'] = _replace_matroesjka_node(node.get('base', {}), chain, depth+1)
    elif t == 'ROOT':
        node['radicand'] = _replace_matroesjka_node(node.get('radicand', {}), chain, depth+1)

    return node


def _clean_matroesjka_annotations(node):
    """Verwijder _matroesjka_root en _node_id annotaties."""
    node.pop('_matroesjka_root', None)
    node.pop('_node_id', None)
    t = node.get('type')
    if t == 'BINARY_OP':
        node['left'] = _clean_matroesjka_annotations(node.get('left', {}))
        node['right'] = _clean_matroesjka_annotations(node.get('right', {}))
    elif t == 'MANIFOLD_OP':
        node['operands'] = [_clean_matroesjka_annotations(op)
                            for op in node.get('operands', [])]
    elif t == 'POWER':
        node['base'] = _clean_matroesjka_annotations(node.get('base', {}))
    elif t == 'ROOT':
        node['radicand'] = _clean_matroesjka_annotations(node.get('radicand', {}))
    return node


def convert_matroesjka(ast, matroesjka_chains):
    """
    Converteer Matroesjka ketens naar MATROESJKA_OP nodes.

    Args:
        ast: AST met _matroesjka_root annotaties (van detect_matroesjka)
        matroesjka_chains: lijst van keten-beschrijvingen

    Returns:
        (converted_ast, stats)
    """
    import copy
    ast = copy.deepcopy(ast)

    for chain in matroesjka_chains:
        ast = _replace_matroesjka_node(ast, chain)

    # Verwijder resterende annotaties
    ast = _clean_matroesjka_annotations(ast)

    stats = {
        'matroesjka_count': len(matroesjka_chains),
        'chains': [{'shell_count': c['shell_count']} for c in matroesjka_chains],
    }
    return ast, stats
