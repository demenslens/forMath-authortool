#!/usr/bin/env python3
"""
ForQuest AST Normalizer - Fase 2
=================================

Normaliseert de AST voor eenvoudiger manifold detectie.

Transformaties:
1. Converteer a-b naar a+(-b)
2. Vereenvoudig dubbele negaties: -(-a) → a
3. Normaliseer a:b naar a×(1/b) [optioneel, voor consistency]

Waarom?
- Maakt manifold detectie eenvoudiger (alleen + hoeft gedetecteerd)
- Uniforme representatie van aftrekking
- Vereenvoudigt latere fases

Input:  AST van expression_parser.py
Output: Genormaliseerde AST

Volgens: ForQuest_Formalisatie_Proces_v3.pdf - Sectie 10.5 Fase 2
"""

from typing import Dict, Any
import copy


class ASTNormalizer:
    """
    Normaliseert AST voor manifold detectie
    
    Belangrijkste transformaties:
    - a - b  →  a + (-b)
    - -(-a)  →  a
    - a : b  →  a × (1/b) [optioneel]
    """
    
    def __init__(self, normalize_division: bool = False):
        """
        Args:
            normalize_division: Als True, converteer a:b naar a×(1/b)
                               Voor ForQuest: False (we houden : apart)
        """
        self.normalize_division = normalize_division
        self.transformations_applied = []
    
    def normalize(self, ast: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliseer een AST
        
        Args:
            ast: AST dictionary van expression_parser
        
        Returns:
            Genormaliseerde AST
        """
        # Werk op een kopie
        normalized = copy.deepcopy(ast)
        
        # Reset transformatie log
        self.transformations_applied = []
        
        # Pas transformaties toe
        normalized = self._normalize_node(normalized)
        
        return normalized
    
    def _normalize_node(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """Recursief normaliseren van een node"""
        
        node_type = node['type']
        
        # Leaf nodes
        if node_type == 'NUMBER':
            return node

        if node_type == 'FRACTION':
            return self._normalize_fraction(node)
        
        # Unaire operaties
        if node_type == 'UNARY_OP':
            return self._normalize_unary(node)
        
        # Binaire operaties
        if node_type == 'BINARY_OP':
            return self._normalize_binary(node)

        # POWER nodes: normaliseer base en exponent, bewaar structuur
        if node_type == 'POWER':
            result = {
                'type': 'POWER',
                'base': self._normalize_node(node['base']),
                'exponent': self._normalize_node(node['exponent']),
            }
            if node.get('is_negative'):
                result['is_negative'] = True
            if node.get('_bracketed'):
                result['_bracketed'] = True
            return result

        # ROOT nodes: normaliseer radicand en index, bewaar structuur
        if node_type == 'ROOT':
            result = {
                'type': 'ROOT',
                'radicand': self._normalize_node(node['radicand']),
                'index': self._normalize_node(node['index']),
            }
            if node.get('is_negative'):
                result['is_negative'] = True
            if node.get('_bracketed'):
                result['_bracketed'] = True
            return result

        return node
    
    def _normalize_fraction(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliseer FRACTION node.

        Als teller deelbaar is door noemer (oneigenlijke breuk die uitkomt
        op een geheel getal), vervang door BINARY_OP deling (:)
        met teller en noemer als NUMBER inputs.

        Voorbeelden:
            6/2  → BINARY_OP(:, NUMBER(6), NUMBER(2))
            9/3  → BINARY_OP(:, NUMBER(9), NUMBER(3))
            7/3  → blijft FRACTION (geen geheel getal)
            1/2  → blijft FRACTION
        """
        num = node['numerator']
        den = node['denominator']
        is_neg = node.get('is_negative', False)

        if den != 0 and num % den == 0:
            self.transformations_applied.append({
                'type': 'improper_fraction_to_division',
                'from': f'{"-" if is_neg else ""}{num}/{den}',
                'to': f'{"-" if is_neg else ""}BINARY_OP(: {num}, {den})',
            })
            result = {
                'type': 'BINARY_OP',
                'operator': ':',
                'left':  {'type': 'NUMBER', 'value': num},
                'right': {'type': 'NUMBER', 'value': den},
            }
            if is_neg:
                result['is_negative'] = True
            return result

        return node

    def _normalize_unary(self, node: Dict[str, Any], pre_normalized_operand=None) -> Dict[str, Any]:
        """
        Normaliseer unaire operatie

        Transformaties:
        - -(-a) → a  (dubbele negatie eliminatie)
        - -(NUMBER/FRACTION/BINARY_OP/...) → node met is_negative=True

        pre_normalized_operand: optioneel al-genormaliseerde operand (voorkomt dubbele normalisatie)
        """
        operator = node['operator']
        original_operand = node.get('operand', {})

        # Gebruik pre-genormaliseerde operand als gegeven, anders normaliseer
        if pre_normalized_operand is not None:
            operand = pre_normalized_operand
        else:
            operand = self._normalize_node(original_operand)

        if operator == '-' and operand.get('is_negative'):
            self.transformations_applied.append({
                'type': 'double_negation_elimination',
                'from': '-(-x)', 'to': 'x'
            })
            operand['is_negative'] = False
            return operand

        if operator == '-':
            self.transformations_applied.append({
                'type': 'negation_integration',
                'from': f'-(node type={operand["type"]})',
                'to': 'node with is_negative=True'
            })
            operand['is_negative'] = True
            # Bewaar _bracketed van de originele (pre-normalisatie) operand
            if original_operand.get('_bracketed'):
                operand['_bracketed'] = True
            return operand

        return {'type': 'UNARY_OP', 'operator': operator, 'operand': operand}

    def _normalize_binary(self, node: Dict[str, Any]) -> Dict[str, Any]:
        """
        Normaliseer binaire operatie
        
        Transformaties:
        - a - b → a + (-b)
        - a : b → a × (1/b) [indien normalize_division=True]
        """
        operator = node['operator']
        left = self._normalize_node(node['left'])
        right = self._normalize_node(node['right'])
        
        # Transformatie 1: a - b → a + (-b)
        if operator == '-':
            self.transformations_applied.append({
                'type': 'subtraction_to_addition',
                'from': 'a - b',
                'to': 'a + (-b)'
            })

            # Geef de al-genormaliseerde right door om dubbele normalisatie te voorkomen
            negated_right = self._normalize_unary({
                'type': 'UNARY_OP',
                'operator': '-',
                'operand': node['right']  # originele (nog niet genormaliseerde)
            }, pre_normalized_operand=right)
            # Markeer dat is_negative via aftrekking werd gezet (niet via literal '-' prefix)
            if isinstance(negated_right, dict):
                negated_right['_via_subtraction'] = True

            new_node = {
                'type': 'BINARY_OP',
                'operator': '+',
                'left': left,
                'right': negated_right
            }
            # Behoud _bracketed flag zodat haakjes grens niet verloren gaat
            if node.get('_bracketed'):
                new_node['_bracketed'] = True
            return new_node
        
        # Transformatie 2: a : b → a × (1/b) [optioneel]
        if operator == ':' and self.normalize_division:
            self.transformations_applied.append({
                'type': 'division_to_multiplication',
                'from': 'a : b',
                'to': 'a × (1/b)'
            })
            
            # Maak reciprocal van rechter operand
            if right['type'] == 'NUMBER':
                reciprocal = {
                    'type': 'FRACTION',
                    'numerator': 1,
                    'denominator': right['value']
                }
            elif right['type'] == 'FRACTION':
                # 1/(a/b) = b/a
                reciprocal = {
                    'type': 'FRACTION',
                    'numerator': right['denominator'],
                    'denominator': right['numerator']
                }
            else:
                # Complexe expressie: kan niet naar breuk
                # Behoud : operator
                return {
                    'type': 'BINARY_OP',
                    'operator': ':',
                    'left': left,
                    'right': right
                }
            
            return {
                'type': 'BINARY_OP',
                'operator': '×',
                'left': left,
                'right': reciprocal
            }
        
        # Geen transformatie
        result = {
            'type': 'BINARY_OP',
            'operator': operator,
            'left': left,
            'right': right
        }
        if node.get('_bracketed'):
            result['_bracketed'] = True
        return result


def normalize_ast(ast: Dict[str, Any], normalize_division: bool = False) -> Dict[str, Any]:
    """
    Normaliseer een AST
    
    Args:
        ast: AST dictionary van expression_parser
        normalize_division: Converteer ook a:b naar a×(1/b)
    
    Returns:
        Genormaliseerde AST
    
    Example:
        >>> from expression_parser import parse_expression
        >>> ast = parse_expression("1-1/2")
        >>> normalized = normalize_ast(ast)
        >>> # Result: 1 + (-1/2) in plaats van 1 - 1/2
    """
    normalizer = ASTNormalizer(normalize_division=normalize_division)
    result = normalizer.normalize(ast)
    
    return result


def get_transformations(ast: Dict[str, Any]) -> list:
    """
    Normaliseer en retourneer lijst van toegepaste transformaties
    
    Handig voor debugging en logging
    """
    normalizer = ASTNormalizer()
    normalizer.normalize(ast)
    return normalizer.transformations_applied


# ============================================================================
# HELPER FUNCTIES - AST naar String (voor visualisatie)
# ============================================================================

def ast_to_string(node: Dict[str, Any]) -> str:
    """
    Converteer AST naar leesbare string
    
    Handig voor debugging en testen
    """
    node_type = node['type']
    
    if node_type == 'NUMBER':
        return str(node['value'])
    
    if node_type == 'FRACTION':
        return f"{node['numerator']}/{node['denominator']}"
    
    if node_type == 'UNARY_OP':
        operand_str = ast_to_string(node['operand'])
        # Voeg haakjes toe indien nodig
        if node['operand']['type'] == 'BINARY_OP':
            operand_str = f"({operand_str})"
        return f"{node['operator']}{operand_str}"
    
    if node_type == 'BINARY_OP':
        left_str = ast_to_string(node['left'])
        right_str = ast_to_string(node['right'])
        
        # Voeg haakjes toe bij lagere voorrang
        if node['left']['type'] == 'BINARY_OP':
            if _needs_parens(node['left']['operator'], node['operator'], 'left'):
                left_str = f"({left_str})"
        
        if node['right']['type'] == 'BINARY_OP':
            if _needs_parens(node['right']['operator'], node['operator'], 'right'):
                right_str = f"({right_str})"
        
        return f"{left_str} {node['operator']} {right_str}"
    
    return str(node)


def _needs_parens(inner_op: str, outer_op: str, position: str) -> bool:
    """Check of haakjes nodig zijn"""
    precedence = {'+': 1, '-': 1, '×': 2, ':': 2}
    
    inner_prec = precedence.get(inner_op, 0)
    outer_prec = precedence.get(outer_op, 0)
    
    # Lagere voorrang heeft altijd haakjes nodig
    if inner_prec < outer_prec:
        return True
    
    # Bij gelijke voorrang: rechts van - en : heeft haakjes nodig
    if inner_prec == outer_prec and position == 'right' and outer_op in ['-', ':']:
        return True
    
    return False


# ============================================================================
# TESTING & VOORBEELDEN
# ============================================================================

if __name__ == "__main__":
    # Import parser voor testen
    try:
        from expression_parser import parse_expression
    except ImportError:
        print("ERROR: Kan expression_parser.py niet importeren")
        print("Zorg dat expression_parser.py in dezelfde directory staat")
        exit(1)
    
    import json
    
    print("=" * 80)
    print("FORQUEST AST NORMALIZER - FASE 2")
    print("=" * 80)
    print()
    
    # Test cases
    test_cases = [
        ("1-1/2", "Aftrekking naar optelling"),
        ("1-2-3", "Meerdere aftrekkingen"),
        ("1+2-3+4", "Mix van optelling en aftrekking"),
        ("-(-1)", "Dubbele negatie"),
        ("-(-(1+2))", "Dubbele negatie met expressie"),
        ("1-(2-3)", "Geneste aftrekking"),
        ("(1-1/2)-[(7/24+3/4)×(1/5+7/25)-1]", "Complex ForQuest voorbeeld"),
    ]
    
    for expr, description in test_cases:
        print(f"\n{description}")
        print(f"Origineel: {expr}")
        print("-" * 70)
        
        # Parse
        ast = parse_expression(expr)
        print(f"Geparsed:     {ast_to_string(ast)}")
        
        # Normaliseer
        normalized = normalize_ast(ast)
        print(f"Genormaliseerd: {ast_to_string(normalized)}")
        
        # Toon transformaties
        transformations = get_transformations(ast)
        if transformations:
            print("\nTransformaties:")
            for t in transformations:
                print(f"  • {t['from']} → {t['to']}")
        
        print()
    
    print("=" * 80)
    print("VERGELIJKING VOOR EN NA")
    print("=" * 80)
    print()
    
    # Gedetailleerd voorbeeld
    expr = "1/9-(3/2+5/6)+2/3"
    print(f"Expressie: {expr}")
    print()
    
    ast = parse_expression(expr)
    print("VOOR normalisatie:")
    print(json.dumps(ast, indent=2))
    print()
    
    normalized = normalize_ast(ast)
    print("NA normalisatie:")
    print(json.dumps(normalized, indent=2))
    print()
    
    print("=" * 80)
    print("✓ FASE 2 COMPLEET")
    print("=" * 80)
    print()
    print("Transformaties:")
    print("  ✓ a - b → a + (-b)")
    print("  ✓ -(-a) → a")
    print()
    print("Volgende stap: Fase 3 - manifold_detector.py")
    print("  - Identificeer ketens van commutatieve operaties")
    print("  - Markeer candidates voor manifolds (3+ inputs met +)")
