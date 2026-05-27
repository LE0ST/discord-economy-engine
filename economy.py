# =========================
# economy.py — Sistema Anti-Monopolio Adaptativo
# =========================

import logging
from random import random

from config import (
    TIER_CUSPIDE_MIN, TIER_ELITE_MIN, TIER_MEDIO_MIN,
    MULTIPLICADOR_CUSPIDE, MULTIPLICADOR_ELITE, MULTIPLICADOR_MEDIO,
    MULTIPLICADOR_PUEBLO, MULTIPLICADOR_NEUTRO
)
from balance import (
    balance_global, balance_por_instancia, 
    obtener_cargas_fortuna, modificar_cargas_fortuna,
    obtener_cargas_maldicion, modificar_cargas_maldicion  # 🌟 Añadidos
)

TIERS = {
    "cuspide": {
        "nombre":        "Cúspide",
        "emoji":         "👑",
        "multiplicador": MULTIPLICADOR_CUSPIDE,
        "descripcion":   "Tasa Aduanera del 35%",
        "color":         0x9B59B6,  # Púrpura Imperial
        "min":           TIER_CUSPIDE_MIN
    },
    "elite": {
        "nombre":        "Élite",
        "emoji":         "💎",
        "multiplicador": MULTIPLICADOR_ELITE,
        "descripcion":   "Impuesto de Operación del 15%",
        "color":         0xE74C3C,  # Rojo
        "min":           TIER_ELITE_MIN
    },
    "medio": {
        "nombre":        "Clase Media",
        "emoji":         "⚖️",
        "multiplicador": MULTIPLICADOR_MEDIO,
        "descripcion":   "Licencia de Libre Comercio (0%)",
        "color":         0xF39C12,  # Naranja
        "min":           TIER_MEDIO_MIN
    },
    "pueblo": {
        "nombre":        "Pueblo",
        "emoji":         "🌱",
        "multiplicador": MULTIPLICADOR_PUEBLO,
        "descripcion":   "Incentivo de Desarrollo (+15%)",
        "color":         0x2ECC71,  # Verde
        "min":           0
    },
    "neutro": {
        "nombre":        "Sin Registro",
        "emoji":         "❓",
        "multiplicador": MULTIPLICADOR_NEUTRO,
        "descripcion":   "Sin modificador",
        "color":         0x95A5A6,
        "min":           None
    }
}


def _clasificar(user_id: int) -> str:
    """Clasifica al usuario según su balance global centralizado."""
    total = balance_global(user_id)

    if total is None:
        return "neutro"
    if total >= TIER_CUSPIDE_MIN:
        return "cuspide"
    if total >= TIER_ELITE_MIN:
        return "elite"
    if total >= TIER_MEDIO_MIN:
        return "medio"
    return "pueblo"


def get_tier_info(user_id: int) -> dict:
    """Devuelve la metadata completa del tier del usuario."""
    return TIERS[_clasificar(user_id)]


def aplicar_impuesto_adaptativo(user_id: int, premio_base: int, instancia_actual: str, es_evento_especial: bool = False) -> tuple[int, float, bool, bool]:
    """
    Calcula el premio final basándose en los Tiers económicos y el estado del usuario.
    Si 'es_evento_especial' es True, el usuario es inmune al sabotaje de la maldición.
    """
    tier_key = _clasificar(user_id)
    tier = TIERS[tier_key]
    multiplicador = tier["multiplicador"]

    # 1. ALGORITMO DE ATENUACIÓN INTER-INSTANCIA (Igual)
    if tier_key in ("cuspide", "elite"):
        desglose_local = balance_por_instancia(user_id)
        balance_local = desglose_local.get(instancia_actual, 0)
        if balance_local < TIER_MEDIO_MIN:
            multiplicador = round(1.0 - ((1.0 - multiplicador) / 2), 2)

    # 2. SISTEMA DE MALDICIONES: TORPEZA
    se_activo_maldicion = False
    
    # 🚨 EL BLINDAJE: Solo procesamos la maldición si NO es un evento especial
    if not es_evento_especial:
        cargas_maldicion = obtener_cargas_maldicion(user_id)
        if cargas_maldicion > 0:
            # Consumimos una carga de torpeza de todas formas
            modificar_cargas_maldicion(user_id, -1)
            
            # Tiramos el dado del 50%
            if random() < 0.50:
                se_activo_maldicion = True
                return 0, 0.0, False, True
    else:
        logging.info(f"🛡️ ECONOMÍA: Bypass de maldición activado para {user_id} por Evento Especial.")

    # 3. SISTEMA DE BUFFS: BENDICIÓN DE FORTUNA (La fortuna SÍ se puede usar en eventos especiales)
    se_uso_fortuna = False
    cargas_fortuna = obtener_cargas_fortuna(user_id)
    
    if cargas_fortuna > 0:
        multiplicador = round(multiplicador + 0.15, 2)
        se_uso_fortuna = True
        modificar_cargas_fortuna(user_id, -1)

    premio_final = round(premio_base * multiplicador)
    return premio_final, multiplicador, se_uso_fortuna, False