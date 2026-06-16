# Mercader del Gremio (Mercader DEV) 🪙

`Mercader DEV` es un bot de Discord de acompañamiento económico desarrollado en Python con **discord.py** y **PostgreSQL** (alojado en Neon.tech). Su propósito es servir como un sistema auxiliar para dinamizar la economía de un servidor basada en el bot **Mudae**, permitiendo importar snapshots de balances de Kakera, calcular multiplicadores, aplicar impuestos adaptativos, y disparar eventos RPG interactivos para los jugadores.

---

## 📖 Tabla de Contenidos
1. [Arquitectura y Concepto de Diseño](#-arquitectura-y-concepto-de-diseño)
2. [Estructura de la Base de Datos (PostgreSQL)](#-estructura-de-la-base-de-datos-postgresql)
3. [Mecánicas del Juego y Economía Adaptativa](#-mecánicas-del-juego-y-economía-adaptativa)
   - [Tiers Económicos (Sistema Anti-Monopolio)](#tiers-económicos-sistema-anti-monopolio)
   - [Algoritmo de Atenuación Inter-Instancia](#algoritmo-de-atenuación-inter-instancia)
   - [Efectos de Estado (Buffs/Debuffs)](#efectos-de-estado-buffsdebuffs)
4. [Eventos RPG del Gremio](#-eventos-rpg-del-gremio)
5. [Guía de Comandos](#-guía-de-comandos)
6. [Optimizaciones de Rendimiento y Asincronía](#-optimizaciones-de-rendimiento-y-asincronía)
7. [Instalación y Configuración](#-instalación-y-configuración)

---

## 🌐 Arquitectura y Concepto de Diseño

> [!IMPORTANT]
> **La fuente de verdad absoluta de los balances de Kakera es el bot 'Mudae'.**
> Este bot actúa únicamente como un visor histórico (snapshot diario) que el Staff sincroniza manualmente. Por lo tanto, las mecánicas de este bot (mazmorras, duelos, etc.) **no persisten balances directos en la base de datos**. Solo el Staff altera los balances en Neon con `mu!setinstancia` o `mu!setbalance`.

* **Event Loop Asíncrono:** Todas las consultas SQL bloqueantes a la base de datos PostgreSQL se delegan a un pool de hilos secundario mediante la función helper `en_hilo` (`loop.run_in_executor`), garantizando que la conexión de red a Neon.tech no bloquee el hilo principal de Discord ni tire la sesión del bot.
* **Keep-Alive:** Implementa un microservidor Flask de fondo que corre en un hilo secundario para mantener el puerto `8080` abierto y evitar que los hostings gratuitos apaguen el bot por inactividad.

---

## 💾 Estructura de la Base de Datos (PostgreSQL)

El bot utiliza una tabla única llamada `usuarios_balances` para persistir el estado de los jugadores:

```sql
CREATE TABLE IF NOT EXISTS usuarios_balances (
    user_id VARCHAR(30) PRIMARY KEY,
    i1 INT DEFAULT 0,                 -- Balance en Instancia 1
    i2 INT DEFAULT 0,                 -- Balance en Instancia 2
    i3 INT DEFAULT 0,                 -- Balance en Instancia 3
    cargas_fortuna INT DEFAULT 0,     -- Buff de Bendición (Máx: 5)
    maldito_hasta INT DEFAULT 0,      -- Debuff de Maldición (Máx: 5)
    ojo_ladron_usos INT DEFAULT 0     -- Usos de Ojo de Ladrón (Reservado)
);
```

---

## 📊 Mecánicas del Juego y Economía Adaptativa

### Tiers Económicos (Sistema Anti-Monopolio)
Para evitar que los usuarios más ricos acaparen la economía, los premios obtenidos en los eventos se multiplican dinámicamente según la **riqueza global** acumulada del usuario (Suma de `i1 + i2 + i3`):

| Rango / Tier | Umbral (Kakera) | Multiplicador | Impuesto / Subsidio |
| :--- | :--- | :---: | :--- |
| **👑 Cúspide** | $\ge 300,000$ | `×0.65` | **35% de Impuesto aduanero** (retención anti-inflación) |
| **💎 Élite** | $\ge 120,000$ | `×0.85` | **15% de Impuesto moderado** |
| **⚖️ Clase Media** | $\ge 40,000$ | `×1.00` | **Libre comercio (0% cambios)** |
| **🌱 Pueblo** | $< 40,000$ | `×1.15` | **+15% de Subsidio de desarrollo** |
| **❓ Sin Registro** | No existe en BD | `×1.00` | Neutro |

### Algoritmo de Atenuación Inter-Instancia
Si un jugador pertenece globalmente a un rango alto (**Cúspide** o **Élite**), pero gana un evento en una instancia específica donde posee fondos bajos ($< \text{Clase Media}$ / $40,000$), el bot **mitiga el impuesto a la mitad** en tiempo de ejecución mediante la fórmula:

$$\text{Multiplicador Final} = 1.0 - \frac{1.0 - \text{Multiplicador Base}}{2}$$

*Ejemplo:* Un rango Élite (`x0.85` base) jugando en una instancia donde tiene menos de $40,000$ Kakera recibirá un multiplicador atenuado de `x0.93` (reduciendo la tasa impositiva del $15\%$ al $7.5\%$, redondeado).

### Efectos de Estado (Buffs/Debuffs)
Los estados se aplican a través de los eventos o comandos de administración y se limitan estrictamente a un **máximo de 5 cargas** para evitar abusos:
* **Bendición de Fortuna (`cargas_fortuna`):** Aumenta el multiplicador del siguiente premio en un **+15%** (se consume 1 carga por victoria).
* **Maldición de Torpeza (`maldito_hasta`):** Otorga un **50% de probabilidad** de que el premio de un evento se reduzca a **0** (se consume 1 carga por intento).

---

## ⚔️ Eventos RPG del Gremio

El bot lanza eventos de forma automática en intervalos configurables (1.5 a 3 horas en producción) o mediante invocación manual por Staff. Los eventos se configuran con una estética limpia adaptada a dispositivos móviles.

1. **Mazmorras y Exploración (Raids):**
   * **Cooperativo (3+ jugadores):** Se genera un pozo total grande y se divide equitativamente. Cada participante es procesado por el motor de impuestos de forma asíncrona. Existe un 15% de probabilidad de recibir una Carga de Fortuna al completarla.
   * **Duelo (2 jugadores):** Un ganador aleatorio se lleva el botín. El perdedor no gana nada.
   * **Solitario (1 jugador):** Misión de exploración con recompensa reducida.
2. **El Cobrador de Impuestos (Spawn Especial):**
   * Exige un código alfanumérico aleatorio de 5 dígitos en el chat en un límite de **45 segundos**.
   * **Éxito (Clutch):** El primero en escribirlo gana $1,000$ Kakera y $+1$ Carga de Fortuna.
   * **Fallo (Expiración):** El inspector multa a un jugador aleatorio que posea $\ge 2,000$ Kakera en esa instancia quitándole $1,500$ Kakera y aplicándole $+2$ Cargas de Torpeza.
3. **El Mímico (Cofre Trampa):**
   * Selecciona a un jugador al azar de los que reaccionaron y le exige resolver una operación aritmética rápida (ej: `18 + 12 - 5`) en un plazo estricto de **12 segundos**.
   * **Éxito:** Elimina al monstruo y gana entre $1,200$ y $2,000$ Kakera.
   * **Fallo:** Pierde entre $800$ y $1,200$ Kakera y recibe $+3$ Cargas de Torpeza (inmune si su balance en la instancia es 0).

---

## ⌨️ Guía de Comandos

### Comandos del Staff (Requieren rol de Staff configurado)
* `mu!setinstancia <i1|i2|i3>`: Carga balances masivamente pegando el volcado directo de texto de Mudae.
* `mu!setbalance @usuario <i1|i2|i3> <cantidad>`: Establece el balance de un usuario en una instancia específica.
* `mu!givebuff @usuario <cargas>`: Otorga cargas de Bendición de Fortuna directas en Neon SQL.
* `mu!givecurse @usuario <cargas>`: Otorga cargas de Maldición de Torpeza directas en Neon SQL.
* `mu!spawn <simple|mazmorra|cobrador|mimico>`: Fuerza el inicio de un evento específico en el canal.

### Comandos Públicos (Disponibles para todos)
* `mu!balance [@usuario]`: Muestra el desglose de Kakera en las 3 instancias, el balance global consolidado y la descripción de su Tier fiscal actual.
* `mu!help`: Muestra el Lore del Gremio y guías introductorias de mecánicas (Fortuna, Torpeza, Cobrador y Mímico).
* `mu!commands`: Muestra la lista y sintaxis de comandos disponibles del bot.

---

## ⚡ Optimizaciones de Rendimiento y Asincronía

Para solucionar fallos críticos de bloqueo en producción con Neon.tech (que causaban desconexión por lag del Gateway de Discord), se rediseñó el flujo de datos:
1. **UPSERT Transaccional por Lotes (`actualizar_balances_lote`):** Procesa listas enteras de usuarios de Mudae (ej: 40+ usuarios) en una única transacción SQL abriendo una sola conexión TCP. Reduce las operaciones de red de $O(N)$ a exactamente **1 transacción**.
2. **SELECT masivo IN (`obtener_balances_globales_lote`):** Consulta la riqueza de todos los usuarios importados en una única sentencia, permitiendo clasificar los Tiers directamente en memoria de forma instantánea.

---

## 🚀 Instalación y Configuración

### 1. Requisitos
* Python 3.10 o superior
* Base de datos PostgreSQL (local o en la nube como Neon.tech)

### 2. Variables de Entorno
Crea un archivo `.env` en la raíz del proyecto con la siguiente estructura:

```env
TOKEN=Tu_Discord_Bot_Token
DATABASE_URL=postgres://usuario:contraseña@servidor.neon.tech/dbname?sslmode=require
ENV=prod # o 'dev' para activar modo de desarrollo (tiempos rápidos y canales de prueba)
```

### 3. Instalación de Dependencias
Activa tu entorno virtual e instala los paquetes indicados en `requirements.txt`:

```bash
# Crear entorno virtual
python -m venv venv

# Activar en Windows PowerShell
.\venv\Scripts\Activate.ps1

# Instalar dependencias
pip install -r requirements.txt
```

### 4. Lanzar el Bot
```bash
python bot.py
```
*(El bot verificará automáticamente la existencia de la tabla en PostgreSQL en su primer inicio y creará los esquemas necesarios).*
