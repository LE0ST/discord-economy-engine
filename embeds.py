# =========================
# embeds.py — Constructores de embeds
# =========================

import discord
from config import (
    FOOTER_TEXT, FOOTER_ICON, EMOJI_KAKERA,
    TIER_CUSPIDE_MIN, TIER_ELITE_MIN, TIER_MEDIO_MIN
)


def _footer(embed: discord.Embed) -> discord.Embed:
    embed.set_footer(text=FOOTER_TEXT, icon_url=FOOTER_ICON)
    return embed

def _formato_multiplicador(multiplicador: float) -> str:
    """Devuelve una cadena legible del modificador económico."""
    if multiplicador > 1:
        return f"+{round((multiplicador - 1) * 100)}%"
    elif multiplicador < 1:
        return f"-{round((1 - multiplicador) * 100)}%"
    else:
        return "±0%"

def _generar_texto_recibo(premio_base: int, premio_final: int, multiplicador: float) -> str:
    """Genera el texto detallado del cálculo económico."""
    mod_str = _formato_multiplicador(multiplicador)
    if multiplicador == 1.0:
        return f"💎 **A Cobrar:** `{premio_final:,} Kakera` {EMOJI_KAKERA}"
    elif multiplicador > 1.0:
        bono = premio_final - premio_base
        return (f"💎 Base: `{premio_base:,}`\n"
                f"📈 Subsidio ({mod_str}): `+{bono:,}`\n"
                f"💰 **A Cobrar:** `{premio_final:,} Kakera` {EMOJI_KAKERA}")
    else:
        impuesto = premio_base - premio_final
        return (f"💎 Base: `{premio_base:,}`\n"
                f"📉 Impuesto ({mod_str}): `-{impuesto:,}`\n"
                f"💰 **A Cobrar:** `{premio_final:,} Kakera` {EMOJI_KAKERA}")

# =========================
# EMBED DE EVENTO (ANUNCIO)
# =========================

def embed_evento(evento: dict, timestamp: int) -> discord.Embed:
    desc_final = (
        f"{evento['desc']}\n\n"
        f"⏳ **Finaliza:** <t:{timestamp}:R>"
    )

    embed = discord.Embed(
        title=evento["titulo"],
        description=desc_final,
        color=evento["color"]
    )
    embed.set_image(url=evento["imagen"])
    return _footer(embed)

# =========================
# EMBEDS DE RESULTADO
# =========================

def embed_resultado_incursion(resultados: list, botín_total: int) -> discord.Embed:
    """
    resultados: lista de (member, premio_final, tier_info, multiplicador)
    """
    lines = []
    for jugador, p_base, p_final, tier, mult in resultados:
        mod_str = _formato_multiplicador(mult)
        if mult == 1.0:
            detalle = f"`{p_final:,} KA`"
        else:
            detalle = f"`{p_base:,}` → `{p_final:,} KA` *({mod_str})*"

        lines.append(f"{tier['emoji']} {jugador.mention}: {detalle}")

    desc = (
        f"🛡️ **{len(resultados)} aventureros** saquearon la mazmorra.\n"
        f"💰 Botín total: `{botín_total:,} Kakera` — dividido entre el grupo.\n\n"
        + "\n".join(lines)
    )

    embed = discord.Embed(
        title="🏆 ¡Incursión Completada!",
        description=desc,
        color=0x57F287
    )
    return _footer(embed)


def embed_resultado_duelo(
    ganador, 
    perdedor, 
    premio_base: int, 
    premio_final: int, 
    tier: dict, 
    multiplicador: float,
    se_uso_fortuna: bool = False,
    cargas_fortuna: int = 0
):
    texto_recibo = _generar_texto_recibo(premio_base, premio_final, multiplicador)

    # 🔮 CONSTRUCCIÓN DEL BLOQUE DE ESTADOS ALTERADOS (BENDICIONES)
    texto_estados = ""
    if se_uso_fortuna:
        texto_estados = (
            f"\n✨ **ESTADOS ACTIVOS:**\n"
            f"├─ Bendición: `Fortuna Activa` *(+15% botín)*\n"
            f"└─ Inventario: `{cargas_fortuna}` cargas restantes\n"
        )

    # Bifurcación si es Duelo Competitivo (n=2) o Evento Simple (n=1)
    if perdedor:
        desc = (
            f"⚔️ **Anales del Combate:**\n"
            f"│ Dos aventureros chocaron espadas en la arena.\n"
            f"└── **{ganador.mention}** venció a {perdedor.mention} en un choque crítico.\n\n"
            f"📊 **ESTADÍSTICAS DEL GANADOR:**\n"
            f"├─ Rango: {tier['emoji']} **{tier['nombre']}**\n"
            f"└─ Multiplicador Base: `×{multiplicador}`\n"
            f"{texto_estados}\n"
            f"{texto_recibo}"
        )
        titulo = "⚔️ ¡Duelo Resuelto!"
    else:
        desc = (
            f"🎲 **El destino ha hablado:**\n"
            f"│ Un cazador de fortunas reclamó el evento antes que nadie.\n"
            f"└── 🎉 **{ganador.mention}** aseguró el botín.\n\n"
            f"📊 **ESTADÍSTICAS DEL USUARIO:**\n"
            f"├─ Rango: {tier['emoji']} **{tier['nombre']}**\n"
            f"└─ Multiplicador Base: `×{multiplicador}`\n"
            f"{texto_estados}\n"
            f"{texto_recibo}"
        )
        titulo = "✨ ¡Misión Completada!"

    embed = discord.Embed(title=titulo, description=desc, color=tier["color"])
    embed.set_thumbnail(url=ganador.display_avatar.url)
    return _footer(embed)

def embed_resultado_solitario(jugador, premio_base: int, premio_final: int, tier: dict, multiplicador: float) -> discord.Embed:
    texto_recibo = _generar_texto_recibo(premio_base, premio_final, multiplicador)
    
    desc = (
        f"🕯️ **{jugador.mention}** exploró en solitario...\n"
        f"Sobrevivió y regresó con algo de valor.\n\n"
        f"{tier['emoji']} Tier: **{tier['nombre']}**\n\n"
        f"{texto_recibo}"
    )

    embed = discord.Embed(
        title="🗡️ ¡Exploración Completada!",
        description=desc,
        color=tier["color"]
    )
    embed.set_thumbnail(url=jugador.display_avatar.url)
    return _footer(embed)

# =========================
# EMBED DE AYUDA (RPG)
# =========================

def embed_help() -> discord.Embed:
    embed = discord.Embed(
        title="📜 Manual del Aventurero",
        description=(
            "*Bienvenido al Gremio de Mercaderes. Aquí se forjan las leyendas y se amasan grandes fortunas en Kakera, "
            "pero también abundan los peligros en las profundidades de la mazmorra...*\n\n"
            "⚖️ **El Ciclo de la Economía**\n"
            "El Gremio aplica impuestos y subsidios adaptativos según tu balance global de Kakera:\n"
            f"> • 👑 **Cúspide** (>{TIER_CUSPIDE_MIN // 1000}k Kakera) — Impuesto aduanero del `35%` (`x0.65` botín).\n"
            f"> • 💎 **Élite** ({TIER_ELITE_MIN // 1000}k–{TIER_CUSPIDE_MIN // 1000}k Kakera) — Impuesto moderado del `15%` (`x0.85` botín).\n"
            f"> • ⚖️ **Clase Media** ({TIER_MEDIO_MIN // 1000}k–{TIER_ELITE_MIN // 1000}k Kakera) — Libre comercio (`x1.00` botín).\n"
            f"> • 🌱 **Pueblo** (<{TIER_MEDIO_MIN // 1000}k Kakera) — Subsidio de desarrollo del `+15%` (`x1.15` botín).\n\n"
            "✨ **Bendiciones y Maldiciones**\n"
            "Tus andanzas pueden alterar tu suerte con efectos temporales:\n"
            "> • 🔮 **Bendición de Fortuna**: Otorga un `+15%` extra de botín (máx. 5 cargas).\n"
            "> • 💀 **Maldición de Torpeza**: 50% de probabilidad de perder todo el botín del evento (máx. 5 cargas).\n\n"
            "⚠️ **Peligros del Gremio**\n"
            "> • 👺 **El Cobrador de Impuestos**: Si aparece en el canal y expira el tiempo de soborno, confiscará `1,500` Kakera y aplicará `+2` cargas de Torpeza a una víctima al azar.\n"
            "> • 🧰 **El Mímico**: Cuidado al abrir cofres antiguos. Si te atrapa y fallas el contrahechizo, perderás balance local y recibirás `+3` cargas de Torpeza."
        ),
        color=0x465473
    )
    return _footer(embed)


def embed_commands() -> discord.Embed:
    embed = discord.Embed(
        title="⚔️ Tabla de Referencia de Comandos",
        description=(
            "Aquí tienes la referencia rápida de los comandos del Gremio. "
            "Los comandos administrativos están restringidos al Staff.\n\n"
            "👤 **Comandos del Gremio** *(Disponibles para todos)*\n"
            "> • `mu!help` — Abre el Manual del Aventurero con las leyes del gremio.\n"
            "> • `mu!commands` — Muestra esta lista de comandos disponibles.\n"
            "> • `mu!balance [@usuario]` — Muestra tu balance global, por instancia (I1, I2, I3) y tu tier económico.\n\n"
            "🛠️ **Comandos del Staff** *(Solo Staff)*\n"
            "> • `mu!spawn [tipo]` — Invoca un evento de forma manual (`simple`, `mazmorra`, `cobrador`, `mimico`).\n"
            "> • `mu!givebuff @usuario <cantidad>` — Otorga cargas de la Bendición de Fortuna a un jugador.\n"
            "> • `mu!givecurse @usuario <cantidad>` — Otorga cargas de la Maldición de Torpeza a un jugador.\n"
            "> • `mu!setbalance @usuario <instancia> <cantidad>` — Ajusta el balance local de un usuario.\n"
            "> • `mu!setinstancia <i1|i2|i3>` — Carga masiva del Ladder importado de Mudae."
        ),
        color=0x465473
    )
    return _footer(embed)
