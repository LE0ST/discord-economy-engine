"""
tests/test_economy.py — Pruebas unitarias para el motor de economía adaptativa.
Verifica clasificación por tiers, atenuación inter-instancia, y efectos de estado (buffs/debuffs)
sin depender de Discord ni de una base de datos activa en producción.
"""

import unittest
from unittest.mock import patch

from config import (
    TIER_CUSPIDE_MIN,
    TIER_ELITE_MIN,
    TIER_MEDIO_MIN,
    MULTIPLICADOR_CUSPIDE,
    MULTIPLICADOR_ELITE,
    MULTIPLICADOR_MEDIO,
    MULTIPLICADOR_PUEBLO,
    MULTIPLICADOR_NEUTRO,
)
from economy import _clasificar, get_tier_info, aplicar_impuesto_adaptativo, TIERS


class TestClasificacionTiers(unittest.TestCase):
    """Pruebas de categorización de riqueza en base al balance global."""

    @patch("economy.balance_global", return_value=None)
    def test_usuario_sin_registro_es_neutro(self, mock_bg):
        self.assertEqual(_clasificar(1001), "neutro")

    @patch("economy.balance_global", return_value=0)
    def test_usuario_pueblo_cero(self, mock_bg):
        self.assertEqual(_clasificar(1002), "pueblo")

    @patch("economy.balance_global", return_value=TIER_MEDIO_MIN - 1)
    def test_usuario_pueblo_limite_superior(self, mock_bg):
        self.assertEqual(_clasificar(1003), "pueblo")

    @patch("economy.balance_global", return_value=TIER_MEDIO_MIN)
    def test_usuario_clase_media_limite_inferior(self, mock_bg):
        self.assertEqual(_clasificar(1004), "medio")

    @patch("economy.balance_global", return_value=80_000)
    def test_usuario_clase_media_intermedio(self, mock_bg):
        self.assertEqual(_clasificar(1005), "medio")

    @patch("economy.balance_global", return_value=TIER_ELITE_MIN)
    def test_usuario_elite_limite_inferior(self, mock_bg):
        self.assertEqual(_clasificar(1006), "elite")

    @patch("economy.balance_global", return_value=200_000)
    def test_usuario_elite_intermedio(self, mock_bg):
        self.assertEqual(_clasificar(1007), "elite")

    @patch("economy.balance_global", return_value=TIER_CUSPIDE_MIN)
    def test_usuario_cuspide_limite_inferior(self, mock_bg):
        self.assertEqual(_clasificar(1008), "cuspide")

    @patch("economy.balance_global", return_value=1_000_000)
    def test_usuario_cuspide_gran_acumulador(self, mock_bg):
        self.assertEqual(_clasificar(1009), "cuspide")


class TestTierInfoMetadata(unittest.TestCase):
    """Pruebas de integridad de metadata de los Tiers."""

    def test_estructura_tiers_completa(self):
        campos_esperados = {"nombre", "emoji", "multiplicador", "descripcion", "color", "min"}
        for tier_key, tier_data in TIERS.items():
            self.assertTrue(campos_esperados.issubset(tier_data.keys()), f"Tier {tier_key} incompleto")

    @patch("economy.balance_global", return_value=500_000)
    def test_get_tier_info_cuspide(self, mock_bg):
        info = get_tier_info(1010)
        self.assertEqual(info["nombre"], "Cúspide")
        self.assertEqual(info["multiplicador"], MULTIPLICADOR_CUSPIDE)

    @patch("economy.balance_global", return_value=5_000)
    def test_get_tier_info_pueblo(self, mock_bg):
        info = get_tier_info(1011)
        self.assertEqual(info["nombre"], "Pueblo")
        self.assertEqual(info["multiplicador"], MULTIPLICADOR_PUEBLO)


class TestAplicarImpuestoAdaptativo(unittest.TestCase):
    """Pruebas de cálculo de recompensas e impuestos."""

    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_global", return_value=None)
    def test_usuario_neutro_sin_modificador(self, mock_bg, mock_bf, mock_bm):
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1020, premio_base=1000, instancia_actual="i1"
        )
        self.assertEqual(premio, 1000)
        self.assertEqual(mult, MULTIPLICADOR_NEUTRO)
        self.assertFalse(uso_fortuna)
        self.assertFalse(act_maldicion)

    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_global", return_value=20_000)
    def test_subsidio_pueblo_15_porciento(self, mock_bg, mock_bf, mock_bm):
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1021, premio_base=1000, instancia_actual="i1"
        )
        self.assertEqual(premio, 1150)
        self.assertEqual(mult, MULTIPLICADOR_PUEBLO)
        self.assertFalse(uso_fortuna)
        self.assertFalse(act_maldicion)

    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_por_instancia", return_value={"i1": 50_000, "i2": 100_000, "i3": 0})
    @patch("economy.balance_global", return_value=150_000)
    def test_impuesto_elite_estandar(self, mock_bg, mock_bpi, mock_bf, mock_bm):
        # Balance local en i1 es 50,000 (>= TIER_MEDIO_MIN), no aplica atenuación
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1022, premio_base=1000, instancia_actual="i1"
        )
        self.assertEqual(premio, 850)
        self.assertEqual(mult, MULTIPLICADOR_ELITE)
        self.assertFalse(uso_fortuna)
        self.assertFalse(act_maldicion)

    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_por_instancia", return_value={"i1": 100_000, "i2": 250_000, "i3": 0})
    @patch("economy.balance_global", return_value=350_000)
    def test_impuesto_cuspide_estandar(self, mock_bg, mock_bpi, mock_bf, mock_bm):
        # Balance local en i1 es 100,000 (>= TIER_MEDIO_MIN), no aplica atenuación
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1023, premio_base=1000, instancia_actual="i1"
        )
        self.assertEqual(premio, 650)
        self.assertEqual(mult, MULTIPLICADOR_CUSPIDE)
        self.assertFalse(uso_fortuna)
        self.assertFalse(act_maldicion)


class TestAtenuacionInterInstancia(unittest.TestCase):
    """
    Pruebas de la fórmula de atenuación inter-instancia:
    Multiplicador = round(1.0 - ((1.0 - Multiplicador_Base) / 2), 2)
    """

    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_por_instancia", return_value={"i1": 150_000, "i2": 2_000, "i3": 0})
    @patch("economy.balance_global", return_value=152_000)
    def test_atenuacion_elite_en_instancia_pobre(self, mock_bg, mock_bpi, mock_bf, mock_bm):
        # Élite (base 0.85) en i2 con solo 2,000 (< 40,000)
        # Atenuación: 1.0 - (1.0 - 0.85) / 2 = 1.0 - 0.075 = 0.925 -> redondeado a 0.93
        premio, mult, _, _ = aplicar_impuesto_adaptativo(
            user_id=1030, premio_base=1000, instancia_actual="i2"
        )
        self.assertEqual(mult, 0.93)
        self.assertEqual(premio, 930)

    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_por_instancia", return_value={"i1": 350_000, "i2": 5_000, "i3": 0})
    @patch("economy.balance_global", return_value=355_000)
    def test_atenuacion_cuspide_en_instancia_pobre(self, mock_bg, mock_bpi, mock_bf, mock_bm):
        # Cúspide (base 0.65) en i2 con solo 5,000 (< 40,000)
        # Atenuación: 1.0 - (1.0 - 0.65) / 2 = 1.0 - 0.175 = 0.825
        # En Python, round(0.825, 2) aplica round-half-to-even resultando en 0.82
        premio, mult, _, _ = aplicar_impuesto_adaptativo(
            user_id=1031, premio_base=1000, instancia_actual="i2"
        )
        self.assertEqual(mult, 0.82)
        self.assertEqual(premio, 820)


class TestBuffsYMaldiciones(unittest.TestCase):
    """Pruebas de efectos temporales (Fortuna y Maldición de Torpeza)."""

    @patch("economy.modificar_cargas_fortuna")
    @patch("economy.obtener_cargas_fortuna", return_value=2)
    @patch("economy.obtener_cargas_maldicion", return_value=0)
    @patch("economy.balance_global", return_value=50_000)
    def test_bendicion_fortuna_suma_bono_y_consume_carga(
        self, mock_bg, mock_bm, mock_bf, mock_mod_bf
    ):
        # Clase Media (1.00) + Fortuna (+0.15) = 1.15
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1040, premio_base=1000, instancia_actual="i1"
        )
        self.assertEqual(mult, 1.15)
        self.assertEqual(premio, 1150)
        self.assertTrue(uso_fortuna)
        self.assertFalse(act_maldicion)
        mock_mod_bf.assert_called_once_with(1040, -1)

    @patch("economy.random", return_value=0.30)  # < 0.50 -> Sabotaje activo
    @patch("economy.modificar_cargas_maldicion")
    @patch("economy.obtener_cargas_maldicion", return_value=1)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_global", return_value=50_000)
    def test_maldicion_torpeza_activacion_anula_premio(
        self, mock_bg, mock_bf, mock_bm, mock_mod_bm, mock_random
    ):
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1041, premio_base=2000, instancia_actual="i1"
        )
        self.assertEqual(premio, 0)
        self.assertEqual(mult, 0.0)
        self.assertFalse(uso_fortuna)
        self.assertTrue(act_maldicion)
        mock_mod_bm.assert_called_once_with(1041, -1)

    @patch("economy.random", return_value=0.75)  # >= 0.50 -> Se salva
    @patch("economy.modificar_cargas_maldicion")
    @patch("economy.obtener_cargas_maldicion", return_value=1)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_global", return_value=50_000)
    def test_maldicion_torpeza_salvada_consume_carga(
        self, mock_bg, mock_bf, mock_bm, mock_mod_bm, mock_random
    ):
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1042, premio_base=1000, instancia_actual="i1"
        )
        self.assertEqual(premio, 1000)
        self.assertEqual(mult, MULTIPLICADOR_MEDIO)
        self.assertFalse(uso_fortuna)
        self.assertFalse(act_maldicion)
        mock_mod_bm.assert_called_once_with(1042, -1)

    @patch("economy.modificar_cargas_maldicion")
    @patch("economy.obtener_cargas_maldicion", return_value=3)
    @patch("economy.obtener_cargas_fortuna", return_value=0)
    @patch("economy.balance_global", return_value=50_000)
    def test_evento_especial_ignora_maldicion(
        self, mock_bg, mock_bf, mock_bm, mock_mod_bm
    ):
        # Evento especial (es_evento_especial=True) no debe procesar ni consumir maldición
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1043, premio_base=1000, instancia_actual="i1", es_evento_especial=True
        )
        self.assertEqual(premio, 1000)
        self.assertFalse(act_maldicion)
        mock_mod_bm.assert_not_called()

    @patch("economy.modificar_cargas_fortuna")
    @patch("economy.obtener_cargas_fortuna", return_value=1)
    @patch("economy.obtener_cargas_maldicion", return_value=2)
    @patch("economy.balance_global", return_value=50_000)
    def test_evento_especial_permite_fortuna(
        self, mock_bg, mock_bf, mock_bm, mock_mod_bf
    ):
        # En evento especial la bendición sí funciona y se consume
        premio, mult, uso_fortuna, act_maldicion = aplicar_impuesto_adaptativo(
            user_id=1044, premio_base=1000, instancia_actual="i1", es_evento_especial=True
        )
        self.assertEqual(premio, 1150)
        self.assertTrue(uso_fortuna)
        self.assertFalse(act_maldicion)
        mock_mod_bf.assert_called_once_with(1044, -1)


if __name__ == "__main__":
    unittest.main()
