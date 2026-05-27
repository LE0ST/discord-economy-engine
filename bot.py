import discord
from discord.ext import commands
import asyncio
import random
import time
import logging
import string
import os
import re
from threading import Thread
from flask import Flask
from dotenv import load_dotenv
from typing import Optional
from functools import partial

from config  import (
    CANALES_EVENTOS, ROL_AVISO_ID, ROL_STAFF_ID,
    INCURSION_MIN_K, INCURSION_MAX_K,
    DUELO_MIN_K, DUELO_MAX_K,
    SOLO_MIN_K, SOLO_MAX_K,
    TIEMPO_MIN, TIEMPO_MAX,
    DEV_MODE
)
from economy import aplicar_impuesto_adaptativo, get_tier_info, TIERS
from events  import TODOS_LOS_EVENTOS, EVENTOS_SIMPLES, EVENTO_MAZMORRA, EVENTO_COBRADOR, EVENTO_MIMICO
from embeds  import (
    embed_evento,
    embed_resultado_incursion,
    embed_resultado_duelo,
    embed_resultado_solitario,
    embed_help,
    embed_commands,
    _footer
)
from balance import (
    cargar_balances, guardar_balances,
    balance_global, balance_por_instancia, set_balance_instancia,
    obtener_cargas_fortuna, modificar_cargas_fortuna,
    obtener_cargas_maldicion, modificar_cargas_maldicion,
    ejecutar_castigo_sql,
    INSTANCIAS
)

# =========================
# KEEP ALIVE
# =========================
app = Flask('')

@app.route('/')
def home():
    return "Mercader del Gremio Online"

def run():
    port = int(os.environ.get("PORT", 8080))
    app.run(host='0.0.0.0', port=port)

# =========================
# BOT
# =========================
logging.basicConfig(level=logging.INFO)

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
intents.members = True

bot = commands.Bot(command_prefix="mu!", intents=intents)
bot.remove_command("help")  # Removemos el help por defecto de discord.py

eventos_iniciados = False

# =========================
# HELPERS
# =========================

# Mapeador estricto para detectar en qué entorno se ejecutó el evento automático
MAPA_CANAL_A_INSTANCIA = (
    {
        100000000000000018: "i1",
        100000000000000019: "i2",
        100000000000000011: "i3"
    }
    if DEV_MODE else
    {
        100000000000000017: "i1",
        100000000000000016: "i2",
        100000000000000020: "i3"
    }
)

def obtener_codigo_instancia(canal_id: int) -> str:
    """Devuelve 'i1', 'i2' o 'i3' según el canal, defaltea a 'i1' si es manual."""
    return MAPA_CANAL_A_INSTANCIA.get(canal_id, "i1")


async def obtener_canal(canal_id: int) -> discord.TextChannel | None:
    canal = bot.get_channel(canal_id)
    if not canal:
        try:
            canal = await bot.fetch_channel(canal_id)
        except Exception:
            logging.error(f"❌ No se pudo obtener el canal {canal_id}")
            return None

    if isinstance(canal, discord.TextChannel):
        return canal

    logging.error(f"❌ El canal {canal_id} no es un canal de texto")
    return None

async def en_hilo(fn, *args, **kwargs):
    """
    Ejecuta una función síncrona bloqueante en el ThreadPoolExecutor
    sin congelar el event loop de discord.py.
    Uso: resultado = await en_hilo(balance_global, user_id)
    """
    loop = asyncio.get_running_loop()
    return await loop.run_in_executor(None, partial(fn, *args, **kwargs))

async def recoger_participantes(mensaje: discord.Message, emoji: str) -> list:
    participantes = []
    for reaction in mensaje.reactions:
        if str(reaction.emoji) == emoji:
            async for user in reaction.users():
                if not user.bot:
                    participantes.append(user)

    return participantes

# =========================
# RESOLUCIÓN DE INCURSIONES
# =========================

async def resolver_simple(canal: discord.TextChannel, participantes: list, evento: dict):
    if not participantes:
        await asyncio.sleep(6.0) # Consume el tiempo de calibración restante si nadie reaccionó
        await canal.send(evento["falla"])
        return

    instancia = obtener_codigo_instancia(canal.id)
    ganador     = random.choice(participantes)
    premio_base = random.randint(evento["min_k"], evento["max_k"])
    
    premio_final, multiplicador, se_uso_fortuna, se_activo_maldicion = aplicar_impuesto_adaptativo(ganador.id, premio_base, instancia)
    tier = get_tier_info(ganador.id)

    # 💀 BIFURCACIÓN DE MALDICIÓN: Si el dado del 50% falló
    if se_activo_maldicion:
        cargas_restantes = obtener_cargas_maldicion(ganador.id)
        
        embed_maldito = discord.Embed(
            title="🥀 ¡Torpeza del Destino!",
            description=(
                f"🔮 {ganador.mention} llegó primero al evento, pero las manos le temblaron debido a una **Maldición de Torpeza**.\n"
                f"Se le cayó la bolsa de Kakera al río y no pudo recuperar nada.\n\n"
                f"💀 Cargas de Torpeza restantes: `{cargas_restantes}`"
            ),
            color=0x7F8C8D
        )
        # 🚨 PING A STAFF EN EL FRACASO POR MALDICIÓN
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed_maldito,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.info(f"💀 SABOTAJE: La maldición anidó la victoria de {ganador} en {instancia.upper()}")
        return

    # --- FLUJO TRADICIONAL DE ÉXITO INTEGRADO ---
    cargas_actuales = obtener_cargas_fortuna(ganador.id)

    # Le pasamos las variables de fortuna de Neon al constructor del embed
    embed = embed_resultado_duelo(
        ganador, None, premio_base, premio_final, tier, multiplicador,
        se_uso_fortuna=se_uso_fortuna, cargas_fortuna=cargas_actuales
    )
    
    # 🚨 PING A STAFF EN EL ÉXITO SIMPLE
    await canal.send(
        content=f"<@&{ROL_STAFF_ID}>",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True)
    )
    logging.info(f"🏆 Ganador Simple: {ganador} — Instancia: {instancia.upper()} — Base: {premio_base} | Final: {premio_final}")

async def resolver_incursion(canal: discord.TextChannel, participantes: list, evento: dict):
    n = len(participantes)
    instancia = obtener_codigo_instancia(canal.id)

    if n == 0:
        await canal.send(evento["falla"])
        return

    # --- Modo Incursión Cooperativa (3+) ---
# === MODO COOPERATIVO (3 o más jugadores) ===
    if n >= 3:
        # 1. Generamos el pozo total grande de la mazmorra
        pozo_total_cooperativo = random.randint(INCURSION_MIN_K, INCURSION_MAX_K)
        
        # 2. 🚨 LA CORRECCIÓN: Dividimos el pozo equitativamente entre los participantes
        premio_base_individual = pozo_total_cooperativo // n
        
        resultados_temporales = []
        suma_premios_finales = 0
        
        jugadores_malditos_reporte = []
        jugadores_fortuna_reporte = []

        # Paso 1: Procesamiento económico individual en el backend
        # Paso 1: Procesamiento económico individual en el backend
        for jugador in participantes:
            premio_final, multiplicador, se_uso_fortuna, se_activo_maldicion = aplicar_impuesto_adaptativo(
                jugador.id, premio_base_individual, instancia
            )
            tier = get_tier_info(jugador.id)
            
            if se_activo_maldicion:
                cargas_quedan = obtener_cargas_maldicion(jugador.id)
                jugadores_malditos_reporte.append(f"• **{jugador.display_name}** *(Restan: {cargas_quedan} 💀)*")
            elif se_uso_fortuna:
                jugadores_fortuna_reporte.append(jugador.display_name)

            resultados_temporales.append((jugador, premio_base_individual, premio_final, tier, multiplicador))
            suma_premios_finales += premio_final

            # 🚨 EL ALIVIO: Pausa de 0.1 segundos para liberar el hilo asíncrono
            await asyncio.sleep(0.1)

        # Paso 2: Generar e imprimir el reporte unificado
        # Desempaquetamos las tuplas limpiamente tal como lo requiere tu función nativa
        resultados_finales = [(r[0], r[1], r[2], r[3], r[4]) for r in resultados_temporales]
        
        # Construimos tu embed base con los balances calculados
        embed = embed_resultado_incursion(resultados_finales, pozo_total_cooperativo)

        # 🚨 INYECTAMOS LOS CAMPOS DE ESTADO AL PIE DEL EMBED (Aquí ocurre la magia visual)
        if jugadores_malditos_reporte:
            valor_campo = "Los siguientes jugadores flaquearon debido a su maldición y su botín se redujo a 0:\n" + "\n".join(jugadores_malditos_reporte)
            if len(valor_campo) > 1020:
                valor_campo = valor_campo[:1017] + "..."
            embed.add_field(
                name="🥀 Torpeza en las Filas",
                value=valor_campo,
                inline=False
            )

        if jugadores_fortuna_reporte:
            valor_campo = f"La suerte impulsó los dividendos de: **{', '.join(jugadores_fortuna_reporte)}** (+15% extra)."
            if len(valor_campo) > 1020:
                valor_campo = valor_campo[:1017] + "..."
            embed.add_field(
                name="✨ Bendición de Fortuna",
                value=valor_campo,
                inline=False
            )

        # Paso 3: Sorteo orgánico de nuevas cargas de Fortuna (Mérito Cooperativo)
        usuarios_bendecidos = []
        for jugador in participantes:
            if random.random() < 0.15: # 15% de drop rate base
                await en_hilo(modificar_cargas_fortuna, jugador.id, 1)
                usuarios_bendecidos.append(jugador.display_name)

        if usuarios_bendecidos:
            embed.add_field(
                name="🎲 Azar del Gremio",
                value=f"¡Los dioses del casino sonreído a **{', '.join(usuarios_bendecidos)}** otorgándoles `+1 Carga de Fortuna`!",
                inline=False
            )

        # Enviamos un solo mensaje contundente con toda la información integrada
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.info(f"⚔️ Mazmorra Grupal Completada en {instancia.upper()} — Total Neto: {suma_premios_finales} KA")
    # --- Modo Duelo Competitivo (2) ---
    elif n == 2:
        ganador  = random.choice(participantes)
        perdedor = next(u for u in participantes if u != ganador)
        premio_base = random.randint(DUELO_MIN_K, DUELO_MAX_K)
        
        premio_final, multiplicador, se_uso_fortuna, se_activo_maldicion = aplicar_impuesto_adaptativo(ganador.id, premio_base, instancia)
        tier = get_tier_info(ganador.id)

        if se_activo_maldicion:
            cargas_restantes = obtener_cargas_maldicion(ganador.id)
            embed_maldito_duelo = discord.Embed(
                title="⚔️ ¡Torpeza en el Duelo!",
                description=f"⚔️ **{ganador.mention}** venció a {perdedor.mention} en duelo, pero al intentar saquearlo se tropezó torpemente perdiendo el botín... \n\n💀 Cargas restantes: `{cargas_restantes}`",
                color=0x7F8C8D
            )
            await canal.send(
                content=f"<@&{ROL_STAFF_ID}>",
                embed=embed_maldito_duelo,
                allowed_mentions=discord.AllowedMentions(roles=True)
            )
            return

        cargas_actuales = obtener_cargas_fortuna(ganador.id)

        # Pasamos las banderas de Fortuna al embed
        embed = embed_resultado_duelo(
            ganador, perdedor, premio_base, premio_final, tier, multiplicador,
            se_uso_fortuna=se_uso_fortuna, cargas_fortuna=cargas_actuales
        )

        # 🚨 PING A STAFF EN EL RESULTADO DEL DUELO
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.info(f"⚔️ Duelo en {instancia.upper()} — Ganador: {ganador} — Base: {premio_base} | Final: {premio_final}")

    # --- Modo Solitario (1) ---
    else:
        jugador = participantes[0]
        premio_base = random.randint(SOLO_MIN_K, SOLO_MAX_K)
        
        premio_final, multiplicador, se_uso_fortuna, se_activo_maldicion = aplicar_impuesto_adaptativo(jugador.id, premio_base, instancia)
        tier = get_tier_info(jugador.id)

        if se_activo_maldicion:
            cargas_restantes = obtener_cargas_maldicion(jugador.id)
            embed_maldito_solo = discord.Embed(
                title="🗡️ Torpeza en Misión Solitaria",
                description=f"🗡️ {jugador.mention} completó la misión solitaria, pero su **Maldición de Torpeza** hizo que rompiera el tesoro sin querer... El botín es 0. \n\n💀 Cargas restantes: `{cargas_restantes}`",
                color=0x7F8C8D
            )
            await canal.send(
                content=f"<@&{ROL_STAFF_ID}>",
                embed=embed_maldito_solo,
                allowed_mentions=discord.AllowedMentions(roles=True)
            )
            return

        # Consumimos el constructor específico de exploración en solitario
        embed = embed_resultado_solitario(
            jugador, premio_base, premio_final, tier, multiplicador
        )
        
        # 🚨 PING A STAFF EN EL RESULTADO SOLITARIO
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.info(f"🗡️ Solitario en {instancia.upper()} — {jugador} — Base: {premio_base} | Final: {premio_final}")

async def resolver_cobrador(canal: discord.TextChannel, evento: dict):
    instancia = obtener_codigo_instancia(canal.id)
    codigo_random = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
    
    segundos_limite = 45
    timestamp_limite = int(time.time()) + 45
    embed = embed_evento(evento, timestamp_limite)
    
    # 🚨 PING A EVENTOS AL HACER EL SPAWN DEL COBRADOR
    await canal.send(
        content=f"<@&{ROL_AVISO_ID}>", 
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True)
    )
    
    mensaje_codigo = await canal.send(f"👺 **CÓDIGO DE SOBORNO REQUERIDO:** `{codigo_random}`")
    logging.info(f"👺 Evento Cobrador: Código generado [{codigo_random}] en #{canal.name}")

    def check_tipeo(m: discord.Message):
        return m.channel == canal and not m.author.bot and m.content.strip() == codigo_random

    try:
        mensaje_ganador = await bot.wait_for("message", check=check_tipeo, timeout=float(segundos_limite))
        ganador = mensaje_ganador.author
        
        premio_final, multiplicador, se_uso_fortuna, _ = aplicar_impuesto_adaptativo(
            ganador.id, 1000, instancia, es_evento_especial=True
        )
        tier = get_tier_info(ganador.id)
        
        desglose = await en_hilo(balance_por_instancia, ganador.id)
        nuevo_balance = desglose.get(instancia, 0) + premio_final
        
        await en_hilo(set_balance_instancia, ganador.id, instancia, nuevo_balance)
        await en_hilo(modificar_cargas_fortuna, ganador.id, 1)
        cargas_totales = await en_hilo(obtener_cargas_fortuna, ganador.id)

        # Rediseño visual en caja del éxito del cobrador
        embed_clutch = discord.Embed(
            title="🗃️ ¡Engañado con éxito! — Clutch del Gremio",
            description=(
                f"🎉 **{ganador.mention}** interceptó al inspector a tiempo escribiendo el código.\n"
                f"│ Logró falsificar los papeles de aduana de la instancia y\n"
                f"└── le arrebató su bolsa de viáticos personales.\n\n"
                f"📊 **REPORTE DE GANANCIAS:**\n"
                f"├─ {tier['emoji']} Tier: **{tier['nombre']}** *(×{multiplicador})*\n"
                f"├─ 💰 Recompensa robada: `+{premio_final:,} Kakera`\n"
                f"└─ ✨ Bonus de velocidad: `+1 Carga de Fortuna` *(Total: {cargas_totales})*"
            ),
            color=0x2ECC71
        )
        if se_uso_fortuna:
            desc_actual = embed_clutch.description or ""
            embed_clutch.description = desc_actual + "\n✨ *(¡Se consumió una carga de Fortuna para un +15% adicional!)*"
            
        # 🚨 PING A STAFF AL ENTRAR EL CÓDIGO CORRECTO
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed_clutch,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.info(f"⚡ CLUTCH: {ganador} salvó el canal y ganó {premio_final} KA en {instancia.upper()}")

    except asyncio.TimeoutError:
        await ejecutar_castigo_cobrador(canal, instancia, evento["falla"])

async def ejecutar_castigo_cobrador(canal: discord.TextChannel, instancia: str, texto_falla: str):
    usuario_afectado_id = await en_hilo(ejecutar_castigo_sql, instancia)

    if usuario_afectado_id:
        miembro = canal.guild.get_member(usuario_afectado_id)
        nombre_victima = miembro.mention if miembro else f"Aventurero ({usuario_afectado_id})"
        
        await en_hilo(modificar_cargas_maldicion, usuario_afectado_id, 2)

        # Rediseño visual en caja del castigo
        embed_castigo = discord.Embed(
            title="💸 ¡Fondos Confiscados por la Corona!",
            description=(
                f"⚖️ **El tiempo de soborno expiró...**\n"
                f"│ El inspector bloqueó los libros contables del canal y\n"
                f"└── seleccionó un evasor fiscal de forma aleatoria:\n\n"
                f"👤 **VÍCTIMA AFECTADA:** {nombre_victima}\n"
                f"├─ 📉 Multa de aduana: `-1,500 Kakera` *(Instancia: {instancia.upper()})*\n"
                f"└─ 💀 Estatus Penal: **+2 Cargas de Torpeza**"
            ),
            color=0xE74C3C
        )
        # 🚨 PING A STAFF AL CONFISCAR DINERO DE FORMA AUTOMÁTICA
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed_castigo,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.warning(f"👺 IMPUESTO: El Cobrador le quitó 1500 KA a {usuario_afectado_id} en {instancia.upper()}")
    else:
        await canal.send(
            f"{texto_falla}\n\n"
            f"*Por suerte, el inspector no encontró ninguna bolsa con suficiente valor y se marchó con las manos vacías.*"
        )

async def resolver_mimico(canal: discord.TextChannel, participantes: list, evento: dict):
    if not participantes:
        await canal.send("🔒 *El cofre antiguo se desvaneció en la niebla sin que nadie intentara abrirlo...*")
        return

    instancia = obtener_codigo_instancia(canal.id)
    ganador = random.choice(participantes)
    
    num1 = random.randint(10, 30)
    num2 = random.randint(5, 20)
    num3 = random.randint(2, 12)
    
    operacion_texto = f"{num1} + {num2} - {num3}"
    respuesta_correcta = num1 + num2 - num3
    
    # Rediseño visual del jumpscare
    embed_trampa = discord.Embed(
        title="🚨 ¡MÍMICO DETECTADO! 🚨",
        description=(
            f"⚠️ **Incidente en las Profundidades**\n"
            f"│ {ganador.mention} intentó abrir el cofre, ¡pero las fauces\n"
            f"│ del monstruo se cerraron sobre sus manos!\n"
            f"└── El **Mímico** te tiene atrapado en su abrazo.\n\n"
            f"⚔️ **CONJURA EL CONTRAHECHIZO EN 12s:**\n"
            f"📊 Operación Requerida: `{operacion_texto}`\n\n"
            f"*Escribe el número entero exacto en el chat para romper las cadenas.*"
        ),
        color=0xE74C3C
    )
    embed_trampa.set_image(url="https://imgur.com/9obFUfG.gif")
    await canal.send(content=ganador.mention, embed=embed_trampa)
    logging.info(f"🧰 Mímico activado para {ganador} en #{canal.name}. Respuesta requerida: [{respuesta_correcta}]")

    def check_matematico(m: discord.Message):
        if m.channel != canal or m.author.id != ganador.id or m.author.bot:
            return False
        try:
            return int(m.content.strip()) == respuesta_correcta
        except ValueError:
            return False

    try:
        await bot.wait_for("message", check=check_matematico, timeout=12.0)
        
        premio_base = random.randint(1200, 2000)
        premio_final, multiplicador, se_uso_fortuna, _ = aplicar_impuesto_adaptativo(
            ganador.id, premio_base, instancia, es_evento_especial=True
        )
        tier = get_tier_info(ganador.id)
        
        desglose = await en_hilo(balance_por_instancia, ganador.id)
        nuevo_balance = desglose.get(instancia, 0) + premio_final
        await en_hilo(set_balance_instancia, ganador.id, instancia, nuevo_balance)
        cargas_actuales = await en_hilo(obtener_cargas_fortuna, ganador.id)
        
        # Rediseño visual de victoria del mímico
        embed_victoria = discord.Embed(
            title="⚔️ ¡Mímico Aniquilado!",
            description=(
                f"🎉 {ganador.mention} respondió con precisión milimétrica,\n"
                f"│ destruyendo al monstruo desde sus entrañas.\n"
                f"└── Las fauces colapsaron y escupieron el botín.\n\n"
                f"📊 **REPORTE DE SAQUEO:**\n"
                f"├─ {tier['emoji']} Rango: **{tier['nombre']}** *(×{multiplicador})*\n"
                f"└─ 💰 Botín Extraído: `+{premio_final:,} Kakera`"
            ),
            color=0x2ECC71
        )
        if se_uso_fortuna:
            embed_victoria.description = (embed_victoria.description or "") + f"\n✨ *(¡Se consumió una carga de Fortuna! Quedan: `{cargas_actuales}`)*"
            
        # 🚨 PING A STAFF EN LA VICTORIA DEL MÍMICO
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed_victoria,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.info(f"🧰 VICTORIA MÍMICO: {ganador} ganó {premio_final} KA en {instancia.upper()}")

    except asyncio.TimeoutError:
        desglose = await en_hilo(balance_por_instancia, ganador.id)
        balance_actual = desglose.get(instancia, 0)
        
        multa = random.randint(800, 1200)
        nuevo_balance = max(0, balance_actual - multa)
        await en_hilo(set_balance_instancia, ganador.id, instancia, nuevo_balance)
        
        if balance_actual > 0:
            await en_hilo(modificar_cargas_maldicion, ganador.id, 3)
            estatus_penal = "+3 Cargas de Torpeza"
        else:
            estatus_penal = "Sin cambios (Inmune por 0 balance)"
        
        # Rediseño visual de derrota del mímico
        embed_derrota = discord.Embed(
            title="💀 ¡Devorado por el Mímico!",
            description=(
                f"⏱️ **El contrahechizo colapsó...**\n"
                f"│ El tiempo expiró o la respuesta fue errónea.\n"
                f"└── El monstruo masticó la mochila de {ganador.mention}.\n\n"
                f"📉 **ESTADO DE LA VÍCTIMA:**\n"
                f"├─ 💸 Confiscación: `- {multa:,} Kakera` *(Instancia: {instancia.upper()})*\n"
                f"└─ 💀 Estatus Penal: **{estatus_penal}**"
            ),
            color=0xC0392B
        )
        # 🚨 PING A STAFF EN LA DERROTA DEL MÍMICO
        await canal.send(
            content=f"<@&{ROL_STAFF_ID}>",
            embed=embed_derrota,
            allowed_mentions=discord.AllowedMentions(roles=True)
        )
        logging.warning(f"🧰 DERROTA MÍMICO: {ganador} perdió {multa} KA en {instancia.upper()}")
        
# =========================
# LANZADOR CENTRAL
# =========================

async def lanzar_evento(canal: discord.TextChannel, evento: dict | None = None):
    """Orquesta el ciclo completo de un evento en el canal dado."""
    if evento is None:
        evento = random.choice(TODOS_LOS_EVENTOS)

    if evento["tipo"] == "cobrador":
        await resolver_cobrador(canal, evento)
        return

    # --- CONFIGURACIÓN DE LATENCIA DINÁMICA ---
    tiempo_reaccion_real = 45
    
    if evento["tipo"] == "mazmorra":
        latencia_compensada = 15
    else:
        latencia_compensada = 8

    # El reloj visual muestra la suma exacta para que el bot tome la foto a los 45s
    segundos_visuales = tiempo_reaccion_real + latencia_compensada
    timestamp = int(time.time()) + segundos_visuales
    embed     = embed_evento(evento, timestamp)

    # 🚨 PING A EVENTOS EN EL ANUNCIO INICIAL DE COFRES Y MAZMORRAS
    mensaje = await canal.send(
        content=f"<@&{ROL_AVISO_ID}>",
        embed=embed,
        allowed_mentions=discord.AllowedMentions(roles=True)
    )
    await mensaje.add_reaction(evento["emoji"])
    logging.info(f"📨 Evento '{evento['titulo']}' lanzado. Ventana real de clics: {tiempo_reaccion_real}s.")

    # El bot duerme los segundos visuales completos para permitir reacciones de acuerdo al timer
    await asyncio.sleep(segundos_visuales)

    try:
        mensaje = await canal.fetch_message(mensaje.id)
    except discord.NotFound:
        return

    participantes = await recoger_participantes(mensaje, evento["emoji"])
    
    # Compensación si el canal estuvo muerto (ya se esperaron los segundos visuales)
    if not participantes:
        if evento["tipo"] == "mazmorra":
            await canal.send("🏰 La mazmorra se derrumbó... Ningún héroe se atrevió a cruzar sus puertas.")
        else:
            await canal.send(evento["falla"])
        return

    # Resoluciones (Todas las de adentro ya tienen sus pings a Staff listos)
    if evento["tipo"] == "mazmorra":
        await resolver_incursion(canal, participantes, evento)
    elif evento["tipo"] == "mimico":
        await resolver_mimico(canal, participantes, evento)
    else:
        await resolver_simple(canal, participantes, evento)

# =========================
# LOOP AUTOMÁTICO
# =========================

async def sistema_eventos():
    await bot.wait_until_ready()
    logging.info("✅ Sistema de eventos iniciado")

    while not bot.is_closed():
        try:
            tiempo_espera = random.randint(TIEMPO_MIN, TIEMPO_MAX)
            if DEV_MODE:
                logging.info(f"⏳ [DEV] Próximo evento en {tiempo_espera} segundos")
            else:
                logging.info(f"⏳ Próximo evento en {round(tiempo_espera / 3600, 2)} horas")
            await asyncio.sleep(tiempo_espera)

            canal_id = random.choice(CANALES_EVENTOS)
            canal    = await obtener_canal(canal_id)
            if canal:
                await lanzar_evento(canal)

        except discord.Forbidden:
            logging.error("❌ Sin permisos en ese canal")
        except discord.HTTPException as e:
            logging.error(f"⚠️ Error HTTP: {e}")
        except Exception as e:
            logging.error(f"⚠️ Error en el loop: {e}")
            await asyncio.sleep(10)

# =========================
# COMANDOS
# =========================

@bot.command(name="spawn")
@commands.has_role(ROL_STAFF_ID)
async def spawn(ctx, tipo: Optional[str] = None):
    """
    Invoca un evento manualmente sin alterar el reloj automático.
    Uso:
      mu!spawn              → evento aleatorio
      mu!spawn simple       → evento simple aleatorio
      mu!spawn mazmorra     → evento de mazmorra
    """
    await ctx.message.delete()

    if tipo == "mazmorra":
        evento = EVENTO_MAZMORRA
    elif tipo == "cobrador":
        evento = EVENTO_COBRADOR
    elif tipo == "mimico":
        evento = EVENTO_MIMICO
    elif tipo == "simple":
        evento = random.choice(EVENTOS_SIMPLES)
    else:
        evento = random.choice(TODOS_LOS_EVENTOS)

    await lanzar_evento(ctx.channel, evento)

@bot.command(name="setinstancia")
@commands.has_role(ROL_STAFF_ID)
async def set_instancia(ctx, instancia: str):
    """
    Carga todos los balances de una instancia pegando el output de Mudae.
    Uso: mu!setinstancia i1
    (luego pegás la lista de Mudae en el mismo mensaje, en líneas separadas)
    Formato esperado por línea:
    username (user_id) - kakera_actual / kakera_total
    """
    if instancia not in INSTANCIAS:
        await ctx.send(f"⚠️ Instancia inválida. Usa `i1`, `i2` o `i3`.", delete_after=8)
        return

    # Extraemos el contenido después del comando
    contenido = ctx.message.content
    lineas = contenido.split("\n")[1:]  # Saltamos la primera línea (el comando)

    if not lineas:
        await ctx.send(
            f"⚠️ No se encontraron datos. Pega la lista de Mudae debajo del comando.\n"
            f"Ejemplo:\n```mu!setinstancia i1\n PlayerOne (100000000000000012) - 37.557 / 144.807```",
            delete_after=15
        )
        return

    # Regex: captura (user_id) y el kakera TOTAL (segundo número)
    patron = re.compile(r'\((\d+)\).*?/\s*([\d.]+)')
    registrados = []
    errores = []

    for linea in lineas:
        linea = linea.strip()
        if not linea:
            continue

        match = patron.search(linea)
        if not match:
            errores.append(f"❌ No se pudo parsear: `{linea[:50]}`")
            continue

        user_id = int(match.group(1))
        # Los puntos son separadores de miles en el output de Mudae
        kakera = int(match.group(2).replace(".", ""))

        # [OPTIMIZACIÓN] Esta operación es de carga masiva en el inicio, se ejecuta síncrona
        # pero como es ejecutada por el Staff en un comando específico, el bloqueo es mínimo.
        set_balance_instancia(user_id, instancia, kakera)
        tier = get_tier_info(user_id)

        # Intentamos obtener el nombre del usuario desde Discord
        miembro = ctx.guild.get_member(user_id)
        nombre = miembro.display_name if miembro else str(user_id)

        registrados.append(f"{tier['emoji']} **{nombre}** → `{kakera:,}` {instancia.upper()}")

    # Embed de resultado
    embed = discord.Embed(
        title=f"💾 Instancia {instancia.upper()} actualizada",
        color=0x465473
    )

    if registrados:
        chunks = [registrados[x:x+15] for x in range(0, len(registrados), 15)]
        for i, chunk in enumerate(chunks):
            embed.add_field(
                name=f"✅ Usuarios Registrados (Parte {i+1})" if i == 0 else "\u200b",
                value="\n".join(chunk),
                inline=False
            )

    if errores:
        embed.add_field(
            name=f"⚠️ {len(errores)} líneas no parseadas",
            value="\n".join(errores),
            inline=False
        )

    _footer(embed) # <--- Llamamos a tu función _footer
    await ctx.send(embed=embed)
    logging.info(f"💾 Instancia {instancia} — {len(registrados)} usuarios cargados")

@bot.command(name="givebuff")
@commands.has_role(ROL_STAFF_ID)
async def give_buff(ctx, miembro: discord.Member, cantidad: int):
    """
    Otorga cargas de la Bendición de Fortuna a un usuario de forma directa en SQL.
    Uso: mu!givebuff @usuario 3
    """
    # [OPTIMIZACIÓN] Ejecutado asíncronamente en hilo secundario
    await en_hilo(modificar_cargas_fortuna, miembro.id, cantidad)
    total_cargas = await en_hilo(obtener_cargas_fortuna, miembro.id)
    
    await ctx.send(
        f"✨ **{miembro.display_name}** ha recibido `{cantidad}` cargas de la **Bendición de Fortuna**.\n"
        f"🔮 Cargas totales en la nube de Neon: `{total_cargas}`"
    )
    logging.info(f"✨ STAFF: {ctx.author} le dio {cantidad} cargas de fortuna a {miembro}")

@bot.command(name="givecurse")
@commands.has_role(ROL_STAFF_ID)
async def give_curse(ctx, miembro: discord.Member, cantidad: int):
    """Otorga cargas de la Maldición de Torpeza a un usuario en Neon SQL."""
    await en_hilo(modificar_cargas_maldicion, miembro.id, cantidad)
    total_cargas = await en_hilo(obtener_cargas_maldicion, miembro.id)
    
    await ctx.send(
        f"💀 **{miembro.display_name}** ha recibido `{cantidad}` cargas de la **Maldición de Torpeza**.\n"
        f"🔮 Cargas totales en la nube de Neon: `{total_cargas}`"
    )

@bot.command(name="setbalance")
@commands.has_role(ROL_STAFF_ID)
async def set_balance(ctx, miembro: discord.Member, instancia: str, cantidad: int):
    """
    Actualiza el balance de una instancia específica de un usuario.
    Uso: mu!setbalance @usuario <i1|i2|i3> <cantidad>
    Ejemplo: mu!setbalance @PlayerOne i1 144577
    """
    if instancia not in INSTANCIAS:
        await ctx.send(
            f"⚠️ Instancia inválida. Usá `i1`, `i2` o `i3`.",
        )
        return

    # [OPTIMIZACIÓN] Escritura persistente asíncrona
    await en_hilo(set_balance_instancia, miembro.id, instancia, cantidad)

    # [CORREGIDO] Cambiado 'objetivo.id' por 'miembro.id' para resolver el error de Pylance
    total = await en_hilo(balance_global, miembro.id)
    tier  = get_tier_info(miembro.id)
    desglose = await en_hilo(balance_por_instancia, miembro.id)

    await ctx.send(
        f"✅ **{miembro.display_name}** — {instancia.upper()} actualizada a `{cantidad:,} Kakera`\n"
        f"📊 Global: `{total:,}` "
        f"(I1: {desglose['i1']:,} · I2: {desglose['i2']:,} · I3: {desglose['i3']:,})\n"
        f"Tier: {tier['emoji']} **{tier['nombre']}** (×{tier['multiplicador']})",
    )
    logging.info(f"💾 {miembro} → {instancia}={cantidad:,} | global={total:,}")


@bot.command(name="balance")
async def ver_balance(ctx, miembro: Optional[discord.Member] = None):
    """
    Muestra el balance por instancia y tier económico de un usuario.
    Uso: mu!balance [@usuario]
    """
    objetivo = miembro or ctx.author
    # [OPTIMIZACIÓN] Consulta global asíncrona
    total    = await en_hilo(balance_global, objetivo.id)

    if total is None:
        await ctx.send(
            f"⚠️ **{objetivo.display_name}** no tiene balance registrado. "
            f"Un Staff puede usar `mu!setbalance @usuario <i1|i2|i3> <cantidad>`.",
        )
        return

    tier     = get_tier_info(objetivo.id)
    # [OPTIMIZACIÓN] Consulta de desglose asíncrona
    desglose = await en_hilo(balance_por_instancia, objetivo.id)

    await ctx.send(
        f"🏦 **{objetivo.display_name}**\n"
        f"I1: `{desglose['i1']:,}` · I2: `{desglose['i2']:,}` · I3: `{desglose['i3']:,}`\n"
        f"📊 Global: `{total:,} Kakera`\n"
        f"Tier: {tier['emoji']} **{tier['nombre']}** — {tier['descripcion']} (×{tier['multiplicador']})",
    )


@bot.command(name="help")
async def ayuda(ctx):
    """Muestra el Manual del Aventurero con las mecánicas del juego."""
    await ctx.send(embed=embed_help())


@bot.command(name="commands")
async def comandos(ctx):
    """Muestra la tabla de referencia de comandos."""
    await ctx.send(embed=embed_commands())


# =========================
# ON READY
# =========================

@bot.event
async def on_ready():
    global eventos_iniciados
    logging.info(f"✅ Bot conectado como {bot.user}")
    if not eventos_iniciados:
        bot.loop.create_task(sistema_eventos())
        eventos_iniciados = True

# =========================
# INICIO
# =========================

cargar_balances()

t = Thread(target=run)
t.daemon = True
t.start()

token = os.getenv("TOKEN")
if token is None:
    raise RuntimeError("Environment variable TOKEN is required")

bot.run(token)