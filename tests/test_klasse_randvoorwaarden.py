"""
Unit tests voor de klasse-, kgv- en randvoorwaarden-uitbreidingen
(iteratie 4 — inspector / randvoorwaarden).

Dekking:
- _lcm en _lcm_list
- _extract_denominators op diverse input-vormen
- generate_formath_json met en zonder klasses/randvoorwaarden
- validator errors en warnings voor verkeerd gebruik
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(ROOT, 'python_bestanden'))
sys.path.insert(0, os.path.join(ROOT, 'formath_web'))
sys.path.insert(0, HERE)

import json_exporter
from json_exporter import (
    _lcm, _lcm_list, _extract_denominators,
    generate_formath_json,
)
from formath_validator import validate_opgave

from expression_parser import parse_expression
from ast_normalizer import normalize_ast
from manifold_detector import detect_manifolds
from manifold_converter import convert_to_manifolds


def pipeline(expr):
    ast = parse_expression(expr)
    norm = normalize_ast(ast)
    ann, stats = detect_manifolds(norm)
    conv, _ = convert_to_manifolds(ann, stats)
    return conv


class TestLcm(unittest.TestCase):
    def test_lcm_basic(self):
        self.assertEqual(_lcm(2, 3), 6)
        self.assertEqual(_lcm(4, 6), 12)
        self.assertEqual(_lcm(5, 5), 5)
        self.assertEqual(_lcm(7, 1), 7)

    def test_lcm_with_zero(self):
        # 0 is geen valide noemer, maar functie mag niet crashen
        self.assertEqual(_lcm(0, 5), 0)
        self.assertEqual(_lcm(5, 0), 0)

    def test_lcm_list_three(self):
        self.assertEqual(_lcm_list([2, 3, 4]), 12)
        self.assertEqual(_lcm_list([2, 4, 8]), 8)
        self.assertEqual(_lcm_list([3, 5, 7]), 105)

    def test_lcm_list_single(self):
        self.assertEqual(_lcm_list([5]), 5)

    def test_lcm_list_empty(self):
        self.assertIsNone(_lcm_list([]))


class TestExtractDenominators(unittest.TestCase):
    def test_simple_fractions(self):
        mb = {'input': [
            {'type': 'extern', 'waarde': '1/3'},
            {'type': 'extern', 'waarde': '1/6'},
        ]}
        self.assertEqual(_extract_denominators(mb), [3, 6])

    def test_mixed_fraction_and_integer(self):
        mb = {'input': [
            {'type': 'extern', 'waarde': '1/2'},
            {'type': 'extern', 'waarde': '5'},   # geheel getal, geen noemer
        ]}
        self.assertEqual(_extract_denominators(mb), [2])

    def test_negative_fraction(self):
        mb = {'input': [
            {'type': 'extern', 'waarde': '-2/3'},
            {'type': 'extern', 'waarde': '1/5'},
        ]}
        self.assertEqual(_extract_denominators(mb), [3, 5])

    def test_empty_input(self):
        self.assertEqual(_extract_denominators({'input': []}), [])


class TestExporterKlasses(unittest.TestCase):
    """Test generate_formath_json met klasse-instellingen."""

    def setUp(self):
        json_exporter.OUTPUT_DIR = tempfile.mkdtemp(prefix='formath_test_')

    def _export(self, expr, **kwargs):
        conv = pipeline(expr)
        result, _ = generate_formath_json(conv, expr, '', expression=expr, **kwargs)
        return result

    def test_no_klasses_no_fields(self):
        """Zonder klasse-parameter: geen klasse-veld in mathblocks."""
        result = self._export('1/2+1/3')
        for mb in result['mathblocks']:
            self.assertNotIn('klasse', mb)

    def test_klasse_a1_no_kgv(self):
        """A1 zet alleen klasse-veld, geen KGV."""
        result = self._export('1/2+1/3', mathblock_klasses={'A1': 'A1'})
        mb = result['mathblocks'][0]
        self.assertEqual(mb.get('klasse'), 'A1')
        self.assertNotIn('kgv', mb)

    def test_klasse_b2_adds_kgv(self):
        """B2 op optelling: klasse + KGV van noemers."""
        result = self._export('1/2+1/3', mathblock_klasses={'A1': 'B2'})
        mb = result['mathblocks'][0]
        self.assertEqual(mb.get('klasse'), 'B2')
        self.assertEqual(mb.get('kgv'), 6)

    def test_klasse_b2_manifold_sum(self):
        """B2 op manifold-sum (M+(3)): KGV over alle noemers."""
        result = self._export('1/2+1/3+1/4', mathblock_klasses={'A1': 'B2'})
        mb = result['mathblocks'][0]
        self.assertEqual(mb.get('klasse'), 'B2')
        self.assertEqual(mb.get('kgv'), 12)  # lcm(2,3,4)=12

    def test_unknown_klasse_silently_ignored(self):
        """Onbekende klasse wordt niet toegevoegd (validator vangt dit)."""
        result = self._export('1/2+1/3', mathblock_klasses={'A1': 'C9'})
        mb = result['mathblocks'][0]
        self.assertNotIn('klasse', mb)


class TestExporterRandvoorwaarden(unittest.TestCase):
    def setUp(self):
        json_exporter.OUTPUT_DIR = tempfile.mkdtemp(prefix='formath_test_')

    def test_default_false(self):
        """Zonder parameter: randvoorwaarden.vereenvoudig_uitkomst is False."""
        conv = pipeline('1/2+1/3')
        result, _ = generate_formath_json(conv, '1/2+1/3', '')
        rv = result['metadata'].get('randvoorwaarden')
        self.assertIsNotNone(rv)
        self.assertEqual(rv.get('vereenvoudig_uitkomst'), False)

    def test_explicit_true(self):
        conv = pipeline('1/2+1/3')
        result, _ = generate_formath_json(
            conv, '1/2+1/3', '',
            randvoorwaarden={'vereenvoudig_uitkomst': True}
        )
        self.assertTrue(result['metadata']['randvoorwaarden']['vereenvoudig_uitkomst'])

    def test_non_bool_coerced(self):
        """Niet-bool waarde wordt ge-cast (bv. int 1 → True)."""
        conv = pipeline('1/2+1/3')
        result, _ = generate_formath_json(
            conv, '1/2+1/3', '',
            randvoorwaarden={'vereenvoudig_uitkomst': 1}
        )
        self.assertIs(result['metadata']['randvoorwaarden']['vereenvoudig_uitkomst'], True)


class TestValidatorKlasses(unittest.TestCase):
    """Test dat de validator klasse-fouten en -warnings correct vangt."""

    def _base_opgave(self):
        """Minimaal valide opgave voor validator-testen."""
        return {
            'metadata': {
                'id': 'test_001',
                'auteur': 'Test',
                'expressie': {
                    'latex': '1+1',
                    'ast': {
                        'tree': ['Add', 1, 1],
                        'node_map': [
                            {'path': [], 'mathblock_id': 'A1', 'type': 'operation'},
                            {'path': [0], 'mathblock_id': 'A1', 'type': 'input', 'waarde': '1'},
                            {'path': [1], 'mathblock_id': 'A1', 'type': 'input', 'waarde': '1'},
                        ],
                    },
                },
                'aantal_mathblocks': 1,
                'aantal_steps': 1,
            },
            'mathblocks': [{
                'id': 'A1',
                'step': 1,
                'operatie': {'symbool': '+'},
                'input': [
                    {'type': 'extern', 'waarde': '1'},
                    {'type': 'extern', 'waarde': '1'},
                ],
                'output': '2',
            }],
            'externe_inputs': [],
            'steps': [{'step': 1, 'mathblocks': ['A1']}],
            'duo_verzameling': [],
        }

    def test_valid_a1(self):
        opgave = self._base_opgave()
        opgave['mathblocks'][0]['klasse'] = 'A1'
        result = validate_opgave(opgave)
        self.assertTrue(result.ok, f"Errors: {result.errors}")

    def test_unknown_klasse(self):
        opgave = self._base_opgave()
        opgave['mathblocks'][0]['klasse'] = 'Z9'
        result = validate_opgave(opgave)
        self.assertFalse(result.ok)
        self.assertTrue(any('onbekende klasse' in e for e in result.errors))

    def test_b2_without_kgv_gives_warning(self):
        opgave = self._base_opgave()
        opgave['mathblocks'][0]['klasse'] = 'B2'
        # geen kgv
        result = validate_opgave(opgave)
        self.assertTrue(result.ok)  # warning, geen error
        self.assertTrue(any('zonder \'kgv\'' in w for w in result.warnings),
                        f"Warnings: {result.warnings}")

    def test_b2_with_valid_kgv(self):
        opgave = self._base_opgave()
        opgave['mathblocks'][0]['klasse'] = 'B2'
        opgave['mathblocks'][0]['kgv'] = 6
        result = validate_opgave(opgave)
        self.assertTrue(result.ok, f"Errors: {result.errors}")
        # geen kgv-warning
        self.assertFalse(any('kgv' in w for w in result.warnings))

    def test_b2_with_invalid_kgv(self):
        opgave = self._base_opgave()
        opgave['mathblocks'][0]['klasse'] = 'B2'
        opgave['mathblocks'][0]['kgv'] = -5   # ongeldig
        result = validate_opgave(opgave)
        self.assertFalse(result.ok)
        self.assertTrue(any("'kgv' moet positieve int zijn" in e for e in result.errors))


class TestValidatorRandvoorwaarden(unittest.TestCase):
    def _base_opgave_with_rv(self, rv):
        return {
            'metadata': {
                'id': 'test_001',
                'auteur': 'Test',
                'expressie': {
                    'latex': '1',
                    'ast': {'tree': 1, 'node_map': []},
                },
                'aantal_mathblocks': 0,
                'aantal_steps': 0,
                'randvoorwaarden': rv,
            },
            'mathblocks': [],
            'externe_inputs': [],
            'steps': [],
            'duo_verzameling': [],
        }

    def test_valid(self):
        opgave = self._base_opgave_with_rv({'vereenvoudig_uitkomst': True})
        result = validate_opgave(opgave)
        self.assertTrue(result.ok, f"Errors: {result.errors}")

    def test_non_bool_value(self):
        opgave = self._base_opgave_with_rv({'vereenvoudig_uitkomst': 'ja'})
        result = validate_opgave(opgave)
        self.assertFalse(result.ok)

    def test_unknown_key_warns(self):
        opgave = self._base_opgave_with_rv({
            'vereenvoudig_uitkomst': True,
            'toekomstige_voorwaarde': 'xyz',
        })
        result = validate_opgave(opgave)
        self.assertTrue(result.ok)  # warning, geen error
        self.assertTrue(any('onbekende sleutel' in w for w in result.warnings))

    def test_optional_whole_thing(self):
        """randvoorwaarden zelf is optioneel — mag gewoon ontbreken."""
        opgave = {
            'metadata': {
                'id': 'test_001',
                'auteur': 'Test',
                'expressie': {
                    'latex': '1',
                    'ast': {'tree': 1, 'node_map': []},
                },
                'aantal_mathblocks': 0,
                'aantal_steps': 0,
            },
            'mathblocks': [],
            'externe_inputs': [],
            'steps': [],
            'duo_verzameling': [],
        }
        result = validate_opgave(opgave)
        self.assertTrue(result.ok, f"Errors: {result.errors}")


class TestExporterOpdracht(unittest.TestCase):
    """Test generate_formath_json met opdracht-parameter."""

    def setUp(self):
        json_exporter.OUTPUT_DIR = tempfile.mkdtemp(prefix='formath_test_')

    def _export(self, expr, **kwargs):
        conv = pipeline(expr)
        result, _ = generate_formath_json(conv, expr, '', expression=expr, **kwargs)
        return result

    def test_default_is_reken_uit(self):
        """Zonder parameter: metadata.opdracht = 'reken_uit'."""
        result = self._export('1+1')
        self.assertEqual(result['metadata'].get('opdracht'), 'reken_uit')

    def test_vereenvoudig(self):
        result = self._export('1/2+1/3', opdracht='vereenvoudig')
        self.assertEqual(result['metadata']['opdracht'], 'vereenvoudig')

    def test_unknown_falls_back_to_default(self):
        """Onbekende waarde valt stil terug op default (validator meldt)."""
        result = self._export('1+1', opdracht='iets_geks')
        self.assertEqual(result['metadata']['opdracht'], 'reken_uit')

    def test_none_uses_default(self):
        result = self._export('1+1', opdracht=None)
        self.assertEqual(result['metadata']['opdracht'], 'reken_uit')


class TestValidatorOpdracht(unittest.TestCase):
    """metadata.opdracht check."""

    def _base(self, opdracht=None):
        meta = {
            'id': 'test_001',
            'auteur': 'Test',
            'expressie': {'latex': '1', 'ast': {'tree': 1, 'node_map': []}},
            'aantal_mathblocks': 0,
            'aantal_steps': 0,
        }
        if opdracht is not None:
            meta['opdracht'] = opdracht
        return {
            'metadata': meta,
            'mathblocks': [], 'externe_inputs': [],
            'steps': [], 'duo_verzameling': [],
        }

    def test_valid_reken_uit(self):
        result = validate_opgave(self._base('reken_uit'))
        self.assertTrue(result.ok, f"Errors: {result.errors}")

    def test_valid_vereenvoudig(self):
        result = validate_opgave(self._base('vereenvoudig'))
        self.assertTrue(result.ok)

    def test_missing_is_ok(self):
        """Opdracht-veld is optioneel."""
        result = validate_opgave(self._base(None))
        self.assertTrue(result.ok)

    def test_unknown_value_errors(self):
        result = validate_opgave(self._base('bereken'))
        self.assertFalse(result.ok)
        self.assertTrue(any('onbekende waarde' in e for e in result.errors))

    def test_wrong_type_errors(self):
        result = validate_opgave(self._base(42))
        self.assertFalse(result.ok)


if __name__ == '__main__':
    unittest.main(verbosity=2)
