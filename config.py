# =========================
# config.py — Configuración central del bot
# =========================

import os
from dotenv import load_dotenv

load_dotenv()

DEV_MODE = os.getenv("ENV") == "dev"

# =========================
# CANALES
# =========================

CANALES_EVENTOS = (
    [
        100000000000000018,
        100000000000000019,
        100000000000000011   
    ]
    if DEV_MODE else
    [
        100000000000000017,
        100000000000000016,
        100000000000000020
    ]
)

# =========================
# ROLES
# =========================

ROL_AVISO_ID = (
    100000000000000021         
    if DEV_MODE else
    100000000000000014
)

ROL_STAFF_ID = (
    100000000000000013         
    if DEV_MODE else
    100000000000000015
)

# =========================
# TIEMPOS DE ESPERA (REDUCIDOS)
# =========================
TIEMPO_MIN = 10    if DEV_MODE else 5400   # dev: 10s  | prod: 1.5 horas
TIEMPO_MAX = 20    if DEV_MODE else 10800  # dev: 20s  | prod: 3.0 horas

# =========================
# ESTÉTICA
# =========================

FOOTER_TEXT  = "Copyright (©) Casino Club"
FOOTER_ICON  = "https://i.imgur.com/ytopJtE.gif"
EMOJI_KAKERA = "<:ka_amarillo:100000000000000010>"


# Evita que Pylance marque los constantes como "no accedidas" al analizarlas localmente.
# `__all__` debería ser suficiente para exportarlas, pero algunos analizadores siguen
# mostrando la advertencia si no detectan uso interno; esta tupla cuenta como uso.
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
# Ajustamos los mínimos para expandir la clase media y capturar la oligarquía real
TIER_CUSPIDE_MIN = 120_000  # Captura a los dueños absolutos del server en el clúster
TIER_ELITE_MIN   =  50_000  # Controla a los farmeadores fuertes antes del monopolio
TIER_MEDIO_MIN   =  15_000  # El piso real del jugador promedio activo en i2 e i3
                             # < 15k → Pueblo / Recién llegados

# Multiplicadores suavizados (Psicología de progresión sana)
MULTIPLICADOR_CUSPIDE = 0.65  # Impuesto aduanero del 35% (Retiene sin deprimir)
MULTIPLICADOR_ELITE   = 0.85  # Impuesto moderado del 15%
MULTIPLICADOR_MEDIO   = 1.00  # Libre comercio (0% cambios)
MULTIPLICADOR_PUEBLO  = 1.15  # Subsidio controlado del +15% (Evita explotación de alts)
MULTIPLICADOR_NEUTRO  = 1.00  # Sin registro → Sin modificaciones (Evita abuso de cuentas nuevas)

# Lista pública de símbolos exportados — ayuda a linters/analizadores estáticos
__all__ = [
    "CANALES_EVENTOS",
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
