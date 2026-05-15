"""
Unit tests voor de LaTeX <-> expressie conversie in server.py.

- latex_to_expression: MathLive LaTeX -> platte expressie
- _node_to_latex via ast_to_latex_display: interne AST -> LaTeX

Round-trip eigenschap: voor gezonde input zou latex -> expression -> AST ->
latex_display een LaTeX moeten opleveren die opnieuw door latex_to_expression
dezelfde expression geeft. Dat testen we hier.

Draaien: python3 tests/test_latex_conversion.py
"""
from __future__ import annotations

import os
import sys
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'python_bestanden'))
sys.path.insert(0, os.path.join(ROOT, 'formath_web'))

from server import latex_to_expression, ast_to_latex_display
from expression_parser import parse_expression
from ast_normalizer import normalize_ast
from manifold_detector import detect_manifolds, detect_matroesjka
from manifold_converter import convert_to_manifolds, convert_matroesjka


def full_pipeline(expr: str):
    ast = parse_expression(expr)
    norm = normalize_ast(ast)
    ann, stats = detect_manifolds(norm)
    conv, _ = convert_to_manifolds(ann, stats)
    mat_ann, chains = detect_matroesjka(conv)
    conv, _ = convert_matroesjka(mat_ann, chains)
    return conv


class TestLatexToExpression(unittest.TestCase):
    """Tests voor MathLive LaTeX -> platte expressie conversie."""

    def test_frac_simple(self):
        self.assertEqual(latex_to_expression(r'\frac{1}{2}'), '1/2')

    def test_frac_nested(self):
        # \frac{a}{b} waarbij b zelf \frac bevat
        result = latex_to_expression(r'\frac{1}{\frac{2}{3}}')
        # Na alle iteraties moet dit een vorm zijn die de parser accepteert
        self.assertIn('1', result)
        self.assertIn('2', result)
        self.assertIn('3', result)

    def test_frac_additive_num(self):
        # Teller is complex: (1+2)/3
        result = latex_to_expression(r'\frac{1+2}{3}')
        self.assertEqual(result, '(1+2)/3')

    def test_frac_additive_den(self):
        result = latex_to_expression(r'\frac{1}{2+3}')
        self.assertEqual(result, '1/(2+3)')

    def test_times(self):
        self.assertEqual(latex_to_expression(r'3\times 2'), '3×2')

    def test_cdot(self):
        self.assertEqual(latex_to_expression(r'3\cdot 2'), '3×2')

    def test_div(self):
        self.assertEqual(latex_to_expression(r'10\div 2'), '10:2')

    def test_parens_mathlive(self):
        # MathLive wraps with \left( ... \right)
        self.assertEqual(latex_to_expression(r'\left(1+2\right)'), '(1+2)')

    def test_brackets(self):
        # \lbrack en \rbrack worden [ en ]
        self.assertEqual(latex_to_expression(r'\lbrack 1+2\rbrack'), '[1+2]')

    def test_brackets_mathlive_wrapped(self):
        self.assertEqual(latex_to_expression(r'\left\lbrack 1+2\right\rbrack'), '[1+2]')

    def test_power_simple(self):
        self.assertEqual(latex_to_expression(r'3^{2}'), '3^2')

    def test_power_negative_exponent(self):
        # ^{-2} moet ^(-2) worden zodat parser ongewijzigd blijft
        self.assertEqual(latex_to_expression(r'3^{-2}'), '3^(-2)')

    def test_sqrt(self):
        self.assertEqual(latex_to_expression(r'\sqrt{16}'), 'sqrt(16)')

    def test_sqrt_nth(self):
        # Conventie: root(n, x) = n-de wortel van x
        # Dus \sqrt[3]{27} (derdemachtswortel van 27) → root(3, 27)
        self.assertEqual(latex_to_expression(r'\sqrt[3]{27}'), 'root(3,27)')

    def test_sqrt_nth_roundtrip(self):
        # Regressie voor bug #4: de gegenereerde LaTeX-display moet
        # \sqrt[3]{27} zijn, niet \sqrt[27]{3}.
        conv = full_pipeline('root(3,27)')
        latex = ast_to_latex_display(conv)
        self.assertIn(r'\sqrt[3]', latex)
        self.assertIn('27', latex)

    def test_combined(self):
        # Echte MathLive output voor een iets complexere expressie
        result = latex_to_expression(r'\frac{1}{2}+\frac{1}{3}')
        self.assertEqual(result, '1/2+1/3')

    def test_whitespace_removed(self):
        self.assertEqual(latex_to_expression(r'3 + 4'), '3+4')

    def test_empty_input(self):
        self.assertEqual(latex_to_expression(''), '')

    def test_bare_sqrt_digit(self):
        # \sqrt16 (zonder accolades) moet ook werken volgens de implementatie
        self.assertEqual(latex_to_expression(r'\sqrt16'), 'sqrt(16)')


class TestAstToLatexDisplay(unittest.TestCase):
    """Tests voor AST -> LaTeX-display (wordt gebruikt als 'latex'-veld in JSON)."""

    def assertProducesLatex(self, expr: str):
        """Helper: pipeline moet een niet-lege LaTeX-string produceren."""
        conv = full_pipeline(expr)
        latex = ast_to_latex_display(conv)
        self.assertTrue(latex, f"Geen LaTeX voor {expr!r}")
        return latex

    def test_simple_sum(self):
        self.assertProducesLatex('1+2')

    def test_fraction(self):
        latex = self.assertProducesLatex('1/2')
        self.assertIn(r'\frac', latex)

    def test_sum_of_fractions(self):
        latex = self.assertProducesLatex('1/2+1/3')
        # Moet twee \frac's bevatten
        self.assertEqual(latex.count(r'\frac'), 2)

    def test_power(self):
        latex = self.assertProducesLatex('3^2+5')
        self.assertIn('^', latex)

    def test_sqrt(self):
        latex = self.assertProducesLatex('sqrt(16)')
        self.assertIn(r'\sqrt', latex)

    def test_nth_root(self):
        # root(3, 27) = derdemachtswortel van 27 → \sqrt[3]{27}
        latex = self.assertProducesLatex('root(3,27)')
        self.assertIn(r'\sqrt[3]', latex)

    def test_negative_number_in_mul(self):
        # Negatief getal in vermenigvuldiging moet haakjes krijgen
        latex = self.assertProducesLatex('3*(-2)')
        self.assertIn(r'\left(-2\right)', latex)

    def test_power_of_fraction(self):
        # Regressie: (1/4)^3 moet \left(\frac{1}{4}\right)^{3} geven,
        # niet \frac{1}{4}^{3} (waarin alleen de noemer verheven zou worden).
        latex = self.assertProducesLatex('(1/4)^3')
        self.assertIn(r'\left(\frac{1}{4}\right)', latex)
        self.assertIn('^{3}', latex)

    def test_power_of_fraction_in_division(self):
        # Origineel bug-rapport: (1/4)^3:(3/4)^2
        latex = self.assertProducesLatex('(1/4)^3:(3/4)^2')
        self.assertEqual(latex.count(r'\left(\frac'), 2,
                         f"Verwachtte 2 haakjes om breuken, kreeg: {latex}")

    def test_power_of_sum(self):
        # (3+5)^2 moet haakjes om de som hebben
        latex = self.assertProducesLatex('(3+5)^2')
        self.assertIn(r'\left(3+5\right)', latex)

    def test_power_of_sqrt(self):
        # (sqrt(5))^2
        latex = self.assertProducesLatex('(sqrt(5))^2')
        self.assertIn(r'\left(\sqrt{5}\right)', latex)

    def test_power_of_negative_no_double_parens(self):
        # (-2)^3: negatief NUMBER krijgt al \left(-2\right) uit NUMBER-tak,
        # POWER mag daar niet nog een laag omheen zetten.
        latex = self.assertProducesLatex('(-2)^3')
        # Tellen: precies één paar \left( ... \right) rond -2
        self.assertEqual(latex.count(r'\left('), 1,
                         f"Verwachtte 1 haakjes-paar, kreeg: {latex}")


class TestRoundTripProperty(unittest.TestCase):
    """
    Property test: voor gezonde expressies moet
       expr → parse → AST → latex_display → latex_to_expression  ≈  expr

    We accepteren normalisatie-verschillen (bv. impliciete haakjes of ×/*-vorm),
    maar de AST van beide zijden moet gelijk zijn.
    """

    def roundtrip_ast_equal(self, expr: str):
        # Eerste pad: expr → AST
        ast1 = full_pipeline(expr)

        # Tweede pad: expr → AST → LaTeX → expr' → AST'
        latex = ast_to_latex_display(ast1)
        expr2 = latex_to_expression(latex)
        ast2 = full_pipeline(expr2)

        # Vergelijk via ast_to_string — een canonieke serialisatie uit de
        # normalizer, zodat we niet op interne pointers vergelijken.
        from ast_normalizer import ast_to_string
        self.assertEqual(
            ast_to_string(ast1),
            ast_to_string(ast2),
            f"Round-trip verschillend voor {expr!r}:\n"
            f"  latex:  {latex}\n"
            f"  expr2:  {expr2}"
        )

    def test_roundtrip_simple(self):
        self.roundtrip_ast_equal('1+2+3')

    def test_roundtrip_fraction(self):
        self.roundtrip_ast_equal('1/2+1/3')

    def test_roundtrip_nested(self):
        self.roundtrip_ast_equal('(1+2)*(3+4)+5')

    def test_roundtrip_power(self):
        self.roundtrip_ast_equal('3^2+5')

    def test_roundtrip_sqrt(self):
        self.roundtrip_ast_equal('sqrt(16)+sqrt(25)')

    def test_roundtrip_mixed(self):
        self.roundtrip_ast_equal('(1/2+1/3)-1/4')


if __name__ == '__main__':
    unittest.main(verbosity=2)
