# =========================
# events.py — Catálogo de eventos
# =========================

EVENTOS_SIMPLES = [
    {
        "tipo":   "simple",
        "titulo": "🤠 Aldeano en Apuros",
        "desc": (
            "*Un aldeano aparece corriendo en el canal, visiblemente nervioso y buscando protección...*\n\n"
            "⚔️ **¿Quién acudirá en su ayuda?**\n"
            "Reacciona con 🐈‍⬛ para intervenir.\n\n"
            "> ⚠️ *Si nadie responde, el aldeano huirá aterrorizado.*"
        ),
        "color":  0xD2B48C,
        "emoji":  "🐈‍⬛",
        "falla":  "💨 *El aldeano huyó aterrado...*",
        "imagen": "https://imgur.com/G6DnMBJ.gif",
        "min_k":  1000,   
        "max_k":  2500,   
    },
    {
        "tipo":   "simple",
        "titulo": "📦 Cofre Misterioso",
        "desc": (
            "*Has encontrado un cofre antiguo sellado con runas ancestrales que vibran con energía mágica...*\n\n"
            "🗝️ **¿Quién intentará forzar la cerradura?**\n"
            "Reacciona con 🔓 para reclamar su contenido.\n\n"
            "> ⚠️ *Si el poder rúnico se agota, el cofre se hundirá en la tierra.*"
        ),
        "color":  0x6F8E65,
        "emoji":  "🔓",
        "falla":  "🌑 *Las runas perdieron su brillo y el cofre se hundió en la tierra...*",
        "imagen": "https://i.imgur.com/IqH18FL.gif",
        "min_k":  1000,   
        "max_k":  2500, 
    },
    {
        "tipo":   "simple",
        "titulo": "💰 Mercader Clandestino",
        "desc": (
            "*Un misterioso mercader encapuchado te hace una seña desde las sombras de un callejón...*\n\n"
            "🤝 **¿Quién hará el trato?**\n"
            "Reacciona con 🪙 para negociar.\n\n"
            "> 🎒 *\"Tengo exceso de equipaje... ¿alguien quiere esto?\"*"
        ),
        "color":  0x465473,
        "emoji":  "🪙",
        "falla":  "🥷 *La guardia de la ciudad apareció y el mercader escapó por los tejados...*",
        "imagen": "https://imgur.com/SSMBwCQ.jpg",
        "min_k":  1500,   
        "max_k":  3000, 
    }
]

EVENTO_MAZMORRA = {
    "tipo":   "mazmorra",  # Usa el resolver genérico, la lógica de modos la maneja resolver_incursion
    "titulo": "⚔️ Llamado de la Mazmorra",
    "desc": (
        "*Las puertas de una mazmorra olvidada se han abierto, liberando rugidos que resuenan en la oscuridad...*\n\n"
        "🗡️ **¿Quién responderá al llamado de la gloria?**\n"
        "Reacciona con ⚔️ para unirte a la expedición.\n\n"
        "> 👥 **Reglas del Gremio:**\n"
        "> • **3+ aventureros**: Activan el **Raid Cooperativo** (botín dividido).\n"
        "> • **2 aventureros**: Activan un **Duelo 1v1** (el ganador cobra el total).\n"
        "> • **1 aventurero**: Activa **Misión Solitaria** (botín reducido)."
    ),
    "color":  0x2C2F33,
    "emoji":  "⚔️",
    "falla":  "🕯️ *Nadie se atrevió a entrar... la mazmorra cerró sus puertas.*",
    "imagen": "https://imgur.com/tJCk9pq.gif"
}

EVENTO_COBRADOR = {
    "tipo": "cobrador",
    "titulo": "👺 ¡ALERTA! El Cobrador de Impuestos de la Corona",
    "desc": (
        "*¡El inspector de la aduana real ha bloqueado el canal exigiendo tributos inmediatos!*\n\n"
        "👺 **Multa de la Corona:** `-1,500` Kakera\n\n"
        "> ⚡ **Mecánica de Clutch:**\n"
        "> Escribe rápidamente el código de soborno exacto en el chat para salvar el canal.\n"
        "> El primero en lograrlo se llevará un botín de `1,000` Kakera de la bolsa del inspector."
    ),
    "emoji": None,
    "color": 0xD51EC7, # Color morado de advertencia
    "falla": "💸 *El chat se quedó paralizado por el pánico. El Cobrador confiscó los fondos sin piedad y huyó...*",
    "imagen": "https://imgur.com/BbK69Do.gif" # Un gif imponente que de aviso de peligro
}

EVENTO_MIMICO = {
    "tipo": "mimico",
    "titulo": "🧰 ¡Un Cofre Antiguo Olvidado!",
    "desc": (
        "*Un cofre con grabados dorados y un aura misteriosa ha aparecido en las profundidades del canal...*\n\n"
        "🧰 **¿Quién reclamará el botín?**\n"
        "Reacciona con 🧰 para intentar abrirlo.\n\n"
        "> ⚠️ *Cuidado: los cofres antiguos no siempre contienen lo que aparentan.*"
    ),
    "emoji": "🧰",
    "color": 0xDCC16C, # Color amarillo dorado
    "falla": "🔒 *El cofre antiguo se desvaneció en la niebla sin que nadie intentara abrirlo...*",
    "imagen": "https://imgur.com/vX4VF2o.jpg" 
}

TODOS_LOS_EVENTOS = EVENTOS_SIMPLES + [EVENTO_MAZMORRA, EVENTO_COBRADOR, EVENTO_MIMICO]
