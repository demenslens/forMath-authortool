#!/usr/bin/env python3
"""
ForQuest Expression Parser - Fase 1
====================================

Parseert een wiskundige expressie string naar een Abstract Syntax Tree (AST).

Functionaliteit:
- Respecteert standaard wiskunde voorrangsregels
- Links-associatief bij gelijke voorrang
- Ondersteunt: +, -, ×, :, haakjes, getallen, breuken, unaire minus

Output: AST met node types: BinaryOp, UnaryOp, Number, Fraction

Volgens: ForQuest_Formalisatie_Proces_v3.pdf - Sectie 10.5 Fase 1
"""

import re
from typing import Union, Dict, Any, List
from dataclasses import dataclass
from enum import Enum


class TokenType(Enum):
    """Token types voor lexer"""
    NUMBER = "NUMBER"
    FRACTION = "FRACTION"
    PLUS = "PLUS"
    MINUS = "MINUS"
    MULTIPLY = "MULTIPLY"
    DIVIDE = "DIVIDE"
    POWER = "POWER"          # ^ voor machten
    LPAREN = "LPAREN"
    RPAREN = "RPAREN"
    LBRACKET = "LBRACKET"
    RBRACKET = "RBRACKET"
    COMMA = "COMMA"          # , voor functie argumenten
    IDENTIFIER = "IDENTIFIER"  # Voor functienamen (sqrt, root, etc.)
    PARAMETER = "PARAMETER"    # Voor letter-parameters (a, b, c, ...) in letterrekenen
    EOF = "EOF"


# Bekende multi-letter functienamen. De tokenizer gebruikt deze whitelist
# om onderscheid te maken tussen een functie-aanroep (sqrt, root, pi) en
# een serie losse parameters (ab → a × b).
KNOWN_FUNCTIONS = {'sqrt', 'root', 'pi'}


@dataclass
class Token:
    """Token met type en waarde"""
    type: TokenType
    value: Any
    position: int


class Lexer:
    """
    Lexical analyzer - converteert expressie string naar tokens
    
    Herkent:
    - Getallen: 123, 45
    - Breuken: 1/2, 3/4
    - Operatoren: +, -, ×, :
    - Haakjes: ( ) [ ]
    """
    
    def __init__(self, text: str):
        self.text = text.replace(' ', '')  # Verwijder spaties
        self.pos = 0
        self.current_char = self.text[0] if self.text else None
    
    def error(self, msg: str):
        raise SyntaxError(f"Lexer error at position {self.pos}: {msg}")
    
    def advance(self):
        """Ga naar volgend karakter"""
        self.pos += 1
        self.current_char = self.text[self.pos] if self.pos < len(self.text) else None
    
    def peek(self, offset: int = 1) -> str:
        """Kijk vooruit zonder positie te veranderen"""
        peek_pos = self.pos + offset
        return self.text[peek_pos] if peek_pos < len(self.text) else None
    
    def read_identifier(self) -> str:
        """Lees een identifier (functienaam zoals sqrt, root, etc.)"""
        id_str = ''
        while self.current_char and (self.current_char.isalpha() or self.current_char.isdigit() or self.current_char == '_'):
            id_str += self.current_char
            self.advance()
        return id_str
    
    def read_number(self) -> int:
        """Lees een geheel getal"""
        num_str = ''
        while self.current_char and self.current_char.isdigit():
            num_str += self.current_char
            self.advance()
        return int(num_str)
    
    def read_fraction_or_number(self) -> Token:
        """
        Lees getal of breuk
        
        Breuk detectie: 1/2, 3/4
        Deling detectie: (1+2)/3 → geen breuk, wel deling
        
        Regel: Breuk = getal/getal zonder spaties en haakjes ervoor
        """
        start_pos = self.pos
        numerator = self.read_number()
        
        # Check of het een breuk is: direct gevolgd door / en dan nog een getal
        if self.current_char == '/' and self.peek() and self.peek().isdigit():
            # Check: geen haakje ervoor (anders is het deling van een expressie)
            if start_pos == 0 or self.text[start_pos - 1] not in ')]}':
                self.advance()  # Skip /
                denominator = self.read_number()
                return Token(TokenType.FRACTION, (numerator, denominator), start_pos)
        
        # Gewoon getal
        return Token(TokenType.NUMBER, numerator, start_pos)
    
    def get_next_token(self) -> Token:
        """Haal volgende token uit de input"""
        while self.current_char:
            
            # Whitespace (al verwijderd, maar voor zekerheid)
            if self.current_char.isspace():
                self.advance()
                continue
            
            # Identifier (functienamen: sqrt, root, sin, cos, etc.) of
            # parameter (enkele kleine letter: a, b, c, ...).
            if self.current_char.isalpha():
                start_pos = self.pos
                # Check eerst of een bekende multi-letter functienaam start.
                # Voorbeelden: "sqrt", "root", "pi". Een conservatieve check:
                # lees de volgende letters/cijfers tot whitespace of non-alpha,
                # kijk of de string een bekende functienaam is.
                ahead = ''
                p = self.pos
                while p < len(self.text) and (self.text[p].isalpha() or self.text[p].isdigit()):
                    ahead += self.text[p]
                    p += 1
                if ahead in KNOWN_FUNCTIONS:
                    # Multi-letter functienaam — lees als IDENTIFIER
                    identifier = self.read_identifier()
                    return Token(TokenType.IDENTIFIER, identifier, start_pos)
                # Anders: één kleine letter = PARAMETER (a, b, c, ...).
                # Hoofdletters of onbekende multi-letter identifiers worden
                # voorlopig geweigerd (tot we hoofdletters of multi-letter
                # parameters willen ondersteunen).
                if self.current_char.islower():
                    ch = self.current_char
                    self.advance()
                    return Token(TokenType.PARAMETER, ch, start_pos)
                # Hoofdletter of iets vreemds: behoud oude gedrag (read als IDENTIFIER)
                identifier = self.read_identifier()
                return Token(TokenType.IDENTIFIER, identifier, start_pos)
            
            # Getallen en breuken
            if self.current_char.isdigit():
                return self.read_fraction_or_number()
            
            # Operatoren en haakjes
            pos = self.pos
            char = self.current_char
            
            if char == '+':
                self.advance()
                return Token(TokenType.PLUS, '+', pos)
            
            if char == '-':
                self.advance()
                return Token(TokenType.MINUS, '-', pos)
            
            if char == '×' or char == '*':
                self.advance()
                return Token(TokenType.MULTIPLY, '×', pos)
            
            # / is DIVIDE in deze gevallen:
            # 1. Na ), ], } (resultaat van expressie)
            # 2. Als : (expliciet deling symbool)
            # 3. Als NIET gevolgd door digit (dan kan het geen breuk zijn)
            if char == ':':
                self.advance()
                return Token(TokenType.DIVIDE, '÷', pos)
            
            if char == '/':
                # Check of er een haakje voor staat
                prev_char = self.text[pos - 1] if pos > 0 else ''
                
                # / is DIVIDE na ), ], }
                if prev_char in ')]}':
                    self.advance()
                    return Token(TokenType.DIVIDE, '÷', pos)
                
                # / is DIVIDE als NIET gevolgd door digit
                if not self.peek() or not self.peek().isdigit():
                    self.advance()
                    return Token(TokenType.DIVIDE, '÷', pos)
                
                # Anders: kan een breuk zijn (wordt gehandeld door read_fraction_or_number)
                # Maar we komen hier alleen als we NIET in read_fraction_or_number zitten
                # Dat betekent: / zonder nummer ervoor
                # Dit is ook DIVIDE
                self.advance()
                return Token(TokenType.DIVIDE, '÷', pos)
            
            if char == '^':
                self.advance()
                return Token(TokenType.POWER, '^', pos)
            
            if char == '(':
                self.advance()
                return Token(TokenType.LPAREN, '(', pos)
            
            if char == ')':
                self.advance()
                return Token(TokenType.RPAREN, ')', pos)
            
            if char == '[':
                self.advance()
                return Token(TokenType.LBRACKET, '[', pos)
            
            if char == ']':
                self.advance()
                return Token(TokenType.RBRACKET, ']', pos)
            
            if char == ',':
                self.advance()
                return Token(TokenType.COMMA, ',', pos)
            
            self.error(f"Onbekend karakter: '{char}'")
        
        return Token(TokenType.EOF, None, self.pos)


class ASTNode:
    """Base class voor AST nodes"""
    pass


@dataclass
class NumberNode(ASTNode):
    """Geheel getal node (of irrationale constante zoals π)"""
    value: int

    def to_dict(self) -> Dict[str, Any]:
        d = {
            'type': 'NUMBER',
            'value': self.value
        }
        # Optionele velden voor irrationale constanten zoals pi
        if getattr(self, '_is_irrational', False):
            d['is_irrational'] = True
        if getattr(self, '_symbol', None):
            d['symbol'] = self._symbol
        if getattr(self, '_decimals', None) is not None:
            d['decimals'] = self._decimals
        return d


@dataclass
class FractionNode(ASTNode):
    """Breuk node"""
    numerator: int
    denominator: int
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'FRACTION',
            'numerator': self.numerator,
            'denominator': self.denominator
        }


@dataclass
class ParameterNode(ASTNode):
    """Letter-parameter node (a, b, c, ...).

    Een PARAMETER is een leaf-node die een letter representeert in
    letter-rekenopgaven. Vergelijkbaar met NumberNode, maar dan voor
    letters in plaats van getallen.

    Zie letterrekenen.md voor de wiskundige conventies.
    """
    name: str  # kleine letter a..z

    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'PARAMETER',
            'name': self.name
        }


@dataclass
class BinaryOpNode(ASTNode):
    """Binaire operatie node"""
    operator: str  # '+', '-', '×', ':'
    left: ASTNode
    right: ASTNode
    
    def to_dict(self) -> Dict[str, Any]:
        d = {
            'type': 'BINARY_OP',
            'operator': self.operator,
            'left': self.left.to_dict(),
            'right': self.right.to_dict()
        }
        if getattr(self, '_bracketed', False):
            d['_bracketed'] = True
        return d


@dataclass
class UnaryOpNode(ASTNode):
    """Unaire operatie node (vooral unaire minus)"""
    operator: str  # '-'
    operand: ASTNode
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'UNARY_OP',
            'operator': self.operator,
            'operand': self.operand.to_dict()
        }


@dataclass
class PowerNode(ASTNode):
    """Macht operatie node"""
    base: ASTNode
    exponent: ASTNode
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'POWER',
            'base': self.base.to_dict(),
            'exponent': self.exponent.to_dict()
        }


@dataclass
class RootNode(ASTNode):
    """Wortel operatie node (unair mathBlock zoals POWER)"""
    radicand: ASTNode  # De waarde waarvan we de wortel nemen
    index: ASTNode     # De n-de wortel (2 voor vierkantswortel, 3 voor derdemacht, etc.)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'ROOT',
            'radicand': self.radicand.to_dict(),
            'index': self.index.to_dict()
        }


@dataclass
class FunctionCallNode(ASTNode):
    """Functie aanroep node (sqrt, root, etc.)"""
    function_name: str
    arguments: List[ASTNode]
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'type': 'FUNCTION_CALL',
            'function': self.function_name,
            'arguments': [arg.to_dict() for arg in self.arguments]
        }


class Parser:
    """
    Recursive Descent Parser
    
    Grammatica (met voorrangsregels):
    
    expression   : term ((PLUS | MINUS) term)*
    term         : power ((MULTIPLY | DIVIDE) power)*
    power        : factor (POWER factor)*
    factor       : PLUS factor
                 | MINUS factor
                 | function_call
                 | NUMBER
                 | FRACTION
                 | LPAREN expression RPAREN
                 | LBRACKET expression RBRACKET
    
    function_call: IDENTIFIER LPAREN expression (COMMA expression)* RPAREN
    
    Voorrangsregels:
    1. Haakjes: ( ) [ ]
    2. Functies: sqrt(), root()
    3. Machten: ^
    4. Unaire operators: - (unaire minus)
    5. Vermenigvuldiging en deling: × :
    6. Optelling en aftrekking: + -
    
    Links-associatief: 1+2+3 = (1+2)+3
    Rechts-associatief voor macht: 2^3^2 = 2^(3^2)
    """
    
    def __init__(self, lexer: Lexer):
        self.lexer = lexer
        self.current_token = self.lexer.get_next_token()
    
    def error(self, msg: str):
        raise SyntaxError(f"Parser error at token {self.current_token}: {msg}")
    
    def eat(self, token_type: TokenType):
        """Consumeer token van verwacht type"""
        if self.current_token.type == token_type:
            self.current_token = self.lexer.get_next_token()
        else:
            self.error(f"Expected {token_type}, got {self.current_token.type}")
    
    def factor(self) -> ASTNode:
        """
        factor : PLUS factor
               | MINUS factor
               | function_call
               | NUMBER
               | FRACTION
               | LPAREN expression RPAREN
               | LBRACKET expression RBRACKET
        """
        token = self.current_token
        
        # Unaire plus (skip)
        if token.type == TokenType.PLUS:
            self.eat(TokenType.PLUS)
            return self.factor()
        
        # Unaire minus
        if token.type == TokenType.MINUS:
            self.eat(TokenType.MINUS)
            return UnaryOpNode('-', self.factor())
        
        # Functie aanroep (sqrt, root, pi, etc.)
        if token.type == TokenType.IDENTIFIER:
            return self.function_call()

        # Letter-parameter (a, b, c, ... voor letterrekenen)
        if token.type == TokenType.PARAMETER:
            self.eat(TokenType.PARAMETER)
            return ParameterNode(token.value)

        # Getal
        if token.type == TokenType.NUMBER:
            self.eat(TokenType.NUMBER)
            return NumberNode(token.value)
        
        # Breuk
        if token.type == TokenType.FRACTION:
            self.eat(TokenType.FRACTION)
            num, denom = token.value
            return FractionNode(num, denom)
        
        # Haakjes ( )
        if token.type == TokenType.LPAREN:
            self.eat(TokenType.LPAREN)
            node = self.expression()
            self.eat(TokenType.RPAREN)
            node._bracketed = True  # markeer als haakjes-blok
            return node

        # Haakjes [ ]
        if token.type == TokenType.LBRACKET:
            self.eat(TokenType.LBRACKET)
            node = self.expression()
            self.eat(TokenType.RBRACKET)
            node._bracketed = True  # markeer als haakjes-blok
            return node
        
        self.error(f"Unexpected token in factor")
    
    def function_call(self) -> ASTNode:
        """
        Parse functie aanroep
        
        Ondersteunde functies:
        - sqrt(x) - vierkantswortel → ROOT node met index=2
        - root(n, x) - n-de wortel van x → ROOT node met index=n
        """
        func_name = self.current_token.value
        self.eat(TokenType.IDENTIFIER)
        
        # Verwacht haakje
        self.eat(TokenType.LPAREN)
        
        # Parse argumenten
        arguments = []
        
        # Eerste argument
        arguments.append(self.expression())
        
        # Eventuele extra argumenten (voor root(n, x))
        while self.current_token.type == TokenType.COMMA:
            self.eat(TokenType.COMMA)
            arguments.append(self.expression())
        
        self.eat(TokenType.RPAREN)
        
        # Converteer naar ROOT nodes (unaire mathBlocks)
        if func_name == 'sqrt':
            if len(arguments) != 1:
                self.error(f"sqrt verwacht 1 argument, kreeg {len(arguments)}")
            # sqrt(x) = x^(1/2) = root met index 2
            return RootNode(
                radicand=arguments[0],
                index=NumberNode(2)  # Vierkantswortel = index 2
            )
        
        elif func_name == 'root':
            if len(arguments) != 2:
                self.error(f"root verwacht 2 argumenten (n, x), kreeg {len(arguments)}")
            # root(n, x) = x^(1/n)
            return RootNode(
                radicand=arguments[1],  # x
                index=arguments[0]       # n
            )

        elif func_name == 'pi':
            # pi(n) — irrationale constante π afgerond op n decimalen.
            # Geeft een NUMBER-node terug met de afgeronde waarde + symbolische
            # metadata (zodat de visualizer en JSON-exporter weten dat het π is).
            if len(arguments) != 1:
                self.error(f"pi verwacht 1 argument (decimalen), kreeg {len(arguments)}")
            # n moet een geheel getal zijn
            n_node = arguments[0]
            if not isinstance(n_node, NumberNode):
                self.error("pi verwacht een geheel getal als aantal decimalen")
            n = int(n_node.value)
            if n < 0 or n > 15:
                self.error(f"Aantal decimalen voor pi moet tussen 0 en 15 liggen, kreeg {n}")
            import math
            # Bereken afgeronde waarde van pi
            rounded_value = round(math.pi, n)
            # Bouw NumberNode met afgeronde float-waarde en symbolische metadata
            node = NumberNode(rounded_value)
            node._is_irrational = True
            node._symbol = 'π'
            node._decimals = n
            node._original_value = math.pi  # voor latere precisie als nodig
            return node

        else:
            self.error(f"Onbekende functie: {func_name}")
        
        # Unreachable
        return NumberNode(0)
    
    def term(self) -> ASTNode:
        """
        term : power ((MULTIPLY | DIVIDE | <impliciet>) power)*

        Links-associatief: 2×3×4 = (2×3)×4

        Impliciete vermenigvuldiging: wanneer twee factoren elkaar opvolgen
        zonder operator ertussen (bv. 2a, ab, 2(a+b), a(b+c), (a)(b)), dan
        wordt dat behandeld als een vermenigvuldiging. De precedence is
        identiek aan een expliciete *, zodat bv. 1/2a = (1/2)·a klopt.

        Een impliciete vermenigvuldiging wordt herkend wanneer het huidige
        token een factor-startend token is:
        - NUMBER, PARAMETER (links-factor)
        - LPAREN, LBRACKET (haakje)
        - IDENTIFIER (functienaam zoals sqrt)
        Maar NIET wanneer er een operator ervoor staat — die wordt al door
        de uitwendige loop afgehandeld.
        """
        node = self.power()

        # Tokens die een nieuw factor kunnen starten (voor impliciete *):
        _IMPLICIT_START = {
            TokenType.NUMBER, TokenType.FRACTION,
            TokenType.PARAMETER, TokenType.IDENTIFIER,
            TokenType.LPAREN, TokenType.LBRACKET,
        }

        while (self.current_token.type in (TokenType.MULTIPLY, TokenType.DIVIDE)
               or self.current_token.type in _IMPLICIT_START):
            token = self.current_token

            if token.type == TokenType.MULTIPLY:
                self.eat(TokenType.MULTIPLY)
                node = BinaryOpNode('×', node, self.power())

            elif token.type == TokenType.DIVIDE:
                self.eat(TokenType.DIVIDE)
                node = BinaryOpNode(':', node, self.power())

            else:
                # Impliciete vermenigvuldiging: geen token consumeren,
                # gewoon de volgende power() parsen en samen tot een
                # vermenigvuldiging maken.
                node = BinaryOpNode('×', node, self.power())

        return node

    def power(self) -> ASTNode:
        """
        power : factor (POWER factor)*
        
        Rechts-associatief: 2^3^2 = 2^(3^2)
        """
        node = self.factor()
        
        if self.current_token.type == TokenType.POWER:
            self.eat(TokenType.POWER)
            # Rechts-associatief: parse de rest recursief
            exponent = self.power()
            node = PowerNode(node, exponent)
        
        return node
    
    def expression(self) -> ASTNode:
        """
        expression : term ((PLUS | MINUS) term)*
        
        Links-associatief: 1+2+3 = (1+2)+3
        """
        node = self.term()
        
        while self.current_token.type in (TokenType.PLUS, TokenType.MINUS):
            token = self.current_token
            
            if token.type == TokenType.PLUS:
                self.eat(TokenType.PLUS)
                node = BinaryOpNode('+', node, self.term())
            
            elif token.type == TokenType.MINUS:
                self.eat(TokenType.MINUS)
                node = BinaryOpNode('-', node, self.term())
        
        return node
    
    def parse(self) -> ASTNode:
        """Parse de volledige expressie"""
        node = self.expression()
        
        if self.current_token.type != TokenType.EOF:
            self.error("Expected end of expression")
        
        return node


def _preprocess_expression(expression: str) -> str:
    """
    Pre-processing voor MathLive ascii-math output.

    MathLive geeft breuken altijd weer als (teller)/(noemer).
    Bijv. frac{3}{5} → (3)/(5), frac{33}{15} → (33)/(15).

    Stap 1: vervang alle (getal)/(getal) → getal/getal
            zodat de lexer ze als FRACTION herkent.
            Bijv. (3)/(5) → 3/5,  2-(33)/(15) → 2-33/15

    Stap 2: vervang :(expr)/(expr) → :(expr/expr)
            voor deling door een breuk.
            Bijv. (3+4):(5)/(27) → (3+4):(5/27)
    """
    # Stap 1: (getal)/(getal) → getal/getal  (iteratief voor meerdere breuken)
    frac_pattern = r'\((\d+)\)\s*/\s*\((\d+)\)'
    prev = None
    while prev != expression:
        prev = expression
        expression = re.sub(frac_pattern,
                            lambda m: m.group(1) + '/' + m.group(2),
                            expression)

    # Stap 2: :(expressie)/(expressie) → :(expressie/expressie)
    div_pattern = r':\s*\(([^()]*)\)\s*/\s*\(([^()]*)\)'
    expression = re.sub(div_pattern,
                        lambda m: ':(' + m.group(1) + '/' + m.group(2) + ')',
                        expression)
    return expression


def parse_expression(expression: str) -> Dict[str, Any]:
    """
    Hoofdfunctie: Parse expressie string naar AST

    Args:
        expression: Wiskundige expressie string (bijv. "1/2+1/3")

    Returns:
        Dict: AST als dictionary

    Example:
        >>> parse_expression("1/2+1/3")
        {
            'type': 'BINARY_OP',
            'operator': '+',
            'left': {'type': 'FRACTION', 'numerator': 1, 'denominator': 2},
            'right': {'type': 'FRACTION', 'numerator': 1, 'denominator': 3}
        }
    """
    expression = _preprocess_expression(expression)
    lexer = Lexer(expression)
    parser = Parser(lexer)
    ast = parser.parse()
    return ast.to_dict()


# ============================================================================
# TESTING & VOORBEELDEN
# ============================================================================

if __name__ == "__main__":
    import json
    
    print("=" * 80)
    print("FORQUEST EXPRESSION PARSER - FASE 1")
    print("=" * 80)
    print()
    
    # Test cases
    test_cases = [
        "1/2+1/3",
        "1-1/2",
        "(1+2)×3",
        "1/2+1/3+1/4",
        "-1+2",
        "1×2+3",
        "(1-1/2)-[(7/24+3/4)×(1/5+7/25)-1]",
        "1/9-(3/2+5/6)+2/3",
    ]
    
    for expr in test_cases:
        print(f"Expressie: {expr}")
        try:
            ast = parse_expression(expr)
            print(f"✓ Geparsed")
            print(f"  AST: {json.dumps(ast, indent=2)}")
            print()
        except Exception as e:
            print(f"✗ Error: {e}")
            print()
    
    print("=" * 80)
    print("✓ FASE 1 COMPLEET")
    print("=" * 80)
    print()
    print("Volgende stap: Fase 2 - ast_normalizer.py")
    print("  - Converteer a-b naar a+(-b)")
    print("  - Vereenvoudig dubbele negaties")
