# =========================
# config.py — Configuración central del bot
# =========================

import os
from dotenv import load_dotenv

load_dotenv()

DEV_MODE = os.getenv("ENV") == "dev"

def _get_env_id(key: str, default: int = 0) -> int:
    """Parsea un ID numérico de Discord desde las variables de entorno de forma segura."""
    val = os.getenv(key)
    if val and val.strip().isdigit():
        return int(val.strip())
    return default

# =========================
# CANALES
# =========================
if DEV_MODE:
    CANAL_I1_ID = _get_env_id("DEV_CANAL_I1_ID", _get_env_id("CANAL_I1_ID", 0))
    CANAL_I2_ID = _get_env_id("DEV_CANAL_I2_ID", _get_env_id("CANAL_I2_ID", 0))
    CANAL_I3_ID = _get_env_id("DEV_CANAL_I3_ID", _get_env_id("CANAL_I3_ID", 0))
else:
    CANAL_I1_ID = _get_env_id("CANAL_I1_ID", 0)
    CANAL_I2_ID = _get_env_id("CANAL_I2_ID", 0)
    CANAL_I3_ID = _get_env_id("CANAL_I3_ID", 0)

CANALES_EVENTOS = [c for c in (CANAL_I1_ID, CANAL_I2_ID, CANAL_I3_ID) if c != 0]

MAPA_CANAL_A_INSTANCIA = {
    CANAL_I1_ID: "i1",
    CANAL_I2_ID: "i2",
    CANAL_I3_ID: "i3",
}

# =========================
# ROLES
# =========================
if DEV_MODE:
    ROL_AVISO_ID = _get_env_id("DEV_ROL_AVISO_ID", _get_env_id("ROL_AVISO_ID", 0))
    ROL_STAFF_ID = _get_env_id("DEV_ROL_STAFF_ID", _get_env_id("ROL_STAFF_ID", 0))
else:
    ROL_AVISO_ID = _get_env_id("ROL_AVISO_ID", 0)
    ROL_STAFF_ID = _get_env_id("ROL_STAFF_ID", 0)

# =========================
# TIEMPOS DE ESPERA (REDUCIDOS)
# =========================
TIEMPO_MIN = 10    if DEV_MODE else 5400   # dev: 10s  | prod: 1.5 horas
TIEMPO_MAX = 20    if DEV_MODE else 10800  # dev: 20s  | prod: 3.0 horas

# =========================
# ESTÉTICA
# =========================

FOOTER_TEXT  = os.getenv("FOOTER_TEXT", "Copyright (©) Casino Club")
FOOTER_ICON  = os.getenv("FOOTER_ICON", "https://i.imgur.com/ytopJtE.gif")
EMOJI_KAKERA = os.getenv("EMOJI_KAKERA", "🪙")

_ = (FOOTER_TEXT, FOOTER_ICON, EMOJI_KAKERA)

# =========================
# PREMIOS POR MODO
# =========================

INCURSION_MIN_K = 3000   # Cooperativa (3+ jugadores) — botín total
INCURSION_MAX_K = 8000

DUELO_MIN_K     = 1500   # Duelo 1v1 — premio para el ganador
DUELO_MAX_K     = 2500

SOLO_MIN_K      = 600    # Solitario — premio reducido
SOLO_MAX_K      = 1200

# =========================
# SISTEMA ANTI-MONOPOLIO (4 TIERS ADAPTATIVOS)
# =========================
TIER_CUSPIDE_MIN = 300_000  # Nivel Cúspide: grandes acumuladores de riqueza
TIER_ELITE_MIN   = 120_000  # Jugadores muy activos en el clúster
TIER_MEDIO_MIN   =  40_000  # El piso del jugador promedio activo
                             # < 40k → Pueblo / Casuales / Inactivos

# Multiplicadores suavizados (Psicología de progresión sana)
MULTIPLICADOR_CUSPIDE = 0.65  # Impuesto aduanero del 35% (Retiene sin deprimir)
MULTIPLICADOR_ELITE   = 0.85  # Impuesto moderado del 15%
MULTIPLICADOR_MEDIO   = 1.00  # Libre comercio (0% cambios)
MULTIPLICADOR_PUEBLO  = 1.15  # Subsidio controlado del +15% (Evita explotación de alts)
MULTIPLICADOR_NEUTRO  = 1.00  # Sin registro → Sin modificaciones (Evita abuso de cuentas nuevas)

# Lista pública de símbolos exportados — ayuda a linters/analizadores estáticos
__all__ = [
    "CANALES_EVENTOS",
    "CANAL_I1_ID",
    "CANAL_I2_ID",
    "CANAL_I3_ID",
    "MAPA_CANAL_A_INSTANCIA",
    "ROL_AVISO_ID",
    "ROL_STAFF_ID",
    "TIEMPO_MIN",
    "TIEMPO_MAX",
    "FOOTER_TEXT",
    "FOOTER_ICON",
    "EMOJI_KAKERA",
    "INCURSION_MIN_K",
    "INCURSION_MAX_K",
    "DUELO_MIN_K",
    "DUELO_MAX_K",
    "SOLO_MIN_K",
    "SOLO_MAX_K",
    "TIER_CUSPIDE_MIN",
    "TIER_ELITE_MIN",
    "TIER_MEDIO_MIN",
    "MULTIPLICADOR_CUSPIDE",
    "MULTIPLICADOR_ELITE",
    "MULTIPLICADOR_MEDIO",
    "MULTIPLICADOR_PUEBLO",
    "MULTIPLICADOR_NEUTRO",
]
