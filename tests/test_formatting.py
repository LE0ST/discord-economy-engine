"""
tests/test_formatting.py — Pruebas unitarias para formateadores y utilidades de configuración.
"""

import unittest
from unittest.mock import patch

from embeds import _formato_multiplicador, _generar_texto_recibo
from config import _get_env_id


class TestFormatoMultiplicador(unittest.TestCase):
    """Pruebas de visualización de porcentajes de modificador económico."""

    def test_multiplicador_neutro(self):
        self.assertEqual(_formato_multiplicador(1.0), "±0%")

    def test_multiplicador_subsidio(self):
        self.assertEqual(_formato_multiplicador(1.15), "+15%")

    def test_multiplicador_impuesto_elite(self):
        self.assertEqual(_formato_multiplicador(0.85), "-15%")

    def test_multiplicador_impuesto_cuspide(self):
        self.assertEqual(_formato_multiplicador(0.65), "-35%")

    def test_multiplicador_atenuado(self):
        self.assertEqual(_formato_multiplicador(0.93), "-7%")


class TestGenerarTextoRecibo(unittest.TestCase):
    """Pruebas de generación del recibo visual para Discord embeds."""

    def test_recibo_neutro(self):
        texto = _generar_texto_recibo(1000, 1000, 1.0)
        self.assertIn("A Cobrar:", texto)
        self.assertIn("1,000", texto)
        self.assertNotIn("Subsidio", texto)
        self.assertNotIn("Impuesto", texto)

    def test_recibo_subsidio(self):
        texto = _generar_texto_recibo(1000, 1150, 1.15)
        self.assertIn("Base: `1,000`", texto)
        self.assertIn("Subsidio (+15%): `+150`", texto)
        self.assertIn("**A Cobrar:** `1,150 Kakera`", texto)

    def test_recibo_impuesto(self):
        texto = _generar_texto_recibo(1000, 850, 0.85)
        self.assertIn("Base: `1,000`", texto)
        self.assertIn("Impuesto (-15%): `-150`", texto)
        self.assertIn("**A Cobrar:** `850 Kakera`", texto)


class TestConfigEnvParsing(unittest.TestCase):
    """Pruebas de conversión segura de variables de entorno numéricas."""

    @patch("os.getenv", return_value="123456789012345678")
    def test_id_numerico_valido(self, mock_env):
        self.assertEqual(_get_env_id("CANAL_TEST_ID"), 123456789012345678)

    @patch("os.getenv", return_value="   987654321098765432   ")
    def test_id_con_espacios(self, mock_env):
        self.assertEqual(_get_env_id("CANAL_TEST_ID"), 987654321098765432)

    @patch("os.getenv", return_value=None)
    def test_id_inexistente_retorna_default(self, mock_env):
        self.assertEqual(_get_env_id("CANAL_TEST_ID", default=0), 0)

    @patch("os.getenv", return_value="invalido_no_numerico")
    def test_id_no_numerico_retorna_default(self, mock_env):
        self.assertEqual(_get_env_id("CANAL_TEST_ID", default=42), 42)


if __name__ == "__main__":
    unittest.main()
