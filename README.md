# Discord Economy & Automation Engine

A Python and `discord.py` automation service featuring multi-instance virtual economy balancing, progressive taxation domain logic, interactive community events, and PostgreSQL persistence.

---

## 📌 Project Context

This application was developed as a companion system for a private Discord community originally administered by the author since 2021. In mid-2026, as community activity resurged, the server utilized the popular bot **Mudae** as the cornerstone of its virtual collection economy. However, as accumulated currency grew disparate among players, the community required an external mechanism to stimulate engagement, introduce cooperative and competitive minigames, and help balance disparities in accumulated virtual currency.

In May 2026, this companion engine was built and deployed to:
- Ingest periodic economy snapshots across three separate server instances (`i1`, `i2`, `i3`).
- Implement an adaptive tier-based taxation and subsidy model based on player wealth tiers.
- Run scheduled, interactive minigames (raids, reaction challenges, puzzle-solving) with dynamic rewards.
- Maintain persistent player status effects (buffs and debuffs) across gameplay sessions.

The system was deployed on **Render** with **PostgreSQL** hosted on **Neon** during its active operational period (May–July 2026). Following the community's natural conclusion in July 2026, the application is no longer actively deployed or serving live users. It is currently preserved, documented, and tested as a software engineering portfolio project demonstrating domain modeling, asynchronous event handling, transactional database operations, and automated test design.

---

## ✨ Key Features

- **Multi-Instance State Tracking**: Manages player balances across three independent game instances (`i1`, `i2`, `i3`) plus a consolidated global wealth metric.
- **Adaptive Progressive Economy**: Implements four discrete economic tiers with progressive tax rates (up to -35%) and entry-level subsidies (+15%) to maintain economic health.
- **Inter-Instance Tax Mitigation**: Automatically halves tax penalties for wealthy players competing within an instance where their local holdings remain low.
- **Persistent Gameplay State**: Tracks status modifiers in PostgreSQL, including *Blessing of Fortune* (reward multiplier bonus) and *Curse of Clumsiness* (probabilistic reward sabotage).
- **Interactive Event Engine**: Automates recurring channel minigames with randomized timers (1.5h to 3h), demonstrating time-bounded message collection and reaction-driven interaction.
- **Batch Data Ingestion**: Parses raw textual leaderboard dumps using regular expressions and persists updates in a single PostgreSQL transaction (`UPSERT`).
- **Offline Automated Test Suite**: 35 unit tests verifying economic domain formulas, status effects, and string formatting without requiring external network access or credentials.
- **Import-Safe Modular Architecture**: Decoupled initialization allowing modules to be loaded into testing frameworks or CLI utilities without triggering side-effects or network connections.

---

## 🏗️ System Architecture

The application runs as an asynchronous event-driven process connected to the Discord Gateway, backed by a relational database for state persistence:

```mermaid
flowchart TD
    subgraph DiscordPlatform["Discord Platform"]
        Members["Community Members / Staff"]
    end

    subgraph Runtime["Application Runtime (Python / discord.py)"]
        GW["Discord Gateway Client (commands.Bot)"]
        Router["Command & Event Dispatcher"]
        Scheduler["Background Event Scheduler (sistema_eventos)"]

        subgraph Domain["Domain & Business Logic"]
            Economy["Economy Engine (economy.py)"]
            Events["Event Catalog & Logic (events.py)"]
            Embeds["UI & Embed Formatters (embeds.py)"]
        end

        subgraph Concurrency["Concurrency Bridge"]
            Executor["run_in_executor (en_hilo)"]
        end

        subgraph KeepAlive["Hosting Auxiliary"]
            Flask["Flask HTTP Ping Listener (port 8080)"]
        end
    end

    subgraph Persistence["Persistence Layer"]
        PG[("PostgreSQL (Neon)")]
    end

    Members <-->|"WebSocket / Gateway Events"| GW
    GW --> Router
    Scheduler -->|"Dispatches minigames at 1.5h-3h intervals"| GW
    Router --> Economy
    Router --> Events
    Router --> Embeds
    Router -->|"Heavy I/O (batch upserts, curse mutations)"| Executor
    Router -.->|"Synchronous queries (legacy paths)"| PG
    Executor -->|"Thread pool worker"| PG
```

### Architectural Highlights
1. **Asynchronous Discord Core**: Interaction handling is built on `discord.py` and `asyncio`, utilizing an event-driven loop for incoming Gateway events.
2. **Worker Thread Offloading**: Intensive database operations (such as multi-user batch imports and raid reward mutations) are delegated to Python's default thread pool via `loop.run_in_executor` (`en_hilo`), reducing the risk of blocking Discord's event loop.
3. **HTTP Keep-Alive Thread**: A lightweight daemon thread runs a minimal Flask HTTP listener (`GET /`) answering external health checks to keep free-tier container instances active during operational periods.

---

## 📊 Economy Engine

The economy engine ([economy.py](economy.py)) implements domain logic to balance virtual currency disparities across participants with substantially different accumulated holdings.

### 1. Progressive Economic Tiers

Global wealth is calculated as the sum of a player's balances across all three instances ($\text{Total} = i_1 + i_2 + i_3$). Based on configured thresholds ([config.py](config.py)), players are classified into four discrete tiers:

| Tier | Wealth Threshold | Base Multiplier | Economic Effect | Objective |
| :--- | :---: | :---: | :---: | :--- |
| **👑 Cúspide** | $\ge 300,000$ | `×0.65` | **-35% Customs Tax** | Damps reward accumulation for top-tier balances |
| **💎 Élite** | $\ge 120,000$ | `×0.85` | **-15% Moderate Tax** | Moderate wealth damping for active participants |
| **⚖️ Clase Media** | $\ge 40,000$ | `×1.00` | **±0% Free Trade** | Baseline equilibrium for average active players |
| **🌱 Pueblo** | $< 40,000$ | `×1.15` | **+15% Development Subsidy** | Catch-up stimulus for casual or newer members |
| **❓ Unregistered** | Not in DB | `×1.00` | **±0% Neutral** | Safe default preventing exploit accounts |

### 2. Inter-Instance Tax Mitigation

A player might hold massive wealth globally (e.g., in instance $i_1$) while being virtually broke in instance $i_2$. Penalizing them with a full 35% tax in an instance where they cannot compete would discourage multi-instance participation.

When a **Cúspide** or **Élite** player wins an event in an instance where their local balance is below the `Clase Media` floor ($< 40,000$), the system dynamically **cuts their tax rate in half**:

$$\text{Mitigated Multiplier} = 1.0 - \frac{1.0 - \text{Base Multiplier}}{2}$$

* **Élite Example**: Base multiplier `0.85` (15% tax) becomes $1.0 - \frac{0.15}{2} = 0.925 \approx \mathbf{0.93}$ (tax reduced to 7%).
* **Cúspide Example**: Base multiplier `0.65` (35% tax) becomes $1.0 - \frac{0.35}{2} = 0.825 \approx \mathbf{0.82}$ (tax reduced to 18%, evaluated via Python's standard round-half-to-even behavior).

### 3. Persistent Gameplay Status Modifiers

Players can acquire temporary status modifiers stored directly in PostgreSQL, capped at a maximum of 5 stacks:
- **Blessing of Fortune (`cargas_fortuna`)**: Adds a flat `+0.15` to the reward multiplier. 1 stack is consumed upon reward calculation.
- **Curse of Clumsiness (`maldito_hasta`)**: Imposes a 50% probability (`random() < 0.50`) of total reward sabotage (reducing the payout to 0). 1 stack is consumed per event attempt.
- **Special Event Immunity**: High-stakes special encounters flag `es_evento_especial = True`, completely bypassing the curse check so players are never sabotaged during milestone challenges, while still allowing fortune bonuses to apply.

---

## ⚔️ Interactive Events & Minigames

The application includes an event engine ([events.py](events.py)) driven by a background task scheduler that periodically dispatches interactive minigames to designated Discord channels:

- **Asynchronous Interaction Handling**: Events utilize `discord.py` reaction listeners and time-bounded message collection (`bot.wait_for`) to capture player input asynchronously without blocking the gateway.
- **Dynamic Reward Resolution**: All event outcomes route through `aplicar_impuesto_adaptativo()`, ensuring that rewards dynamically reflect each participant's global tier, local balance mitigation, and active status effects.
- **Representative Event Modes**:
  - **Cooperative & Competitive Raids (`EVENTO_MAZMORRA`)**: Dynamically scales based on participant count—cooperative raids divide a shared prize pool across participants and award probabilistic Fortune buffs, while two-player encounters resolve as winner-takes-all duels.
  - **Timed Verification Challenges (`EVENTO_COBRADOR`, `EVENTO_MIMICO`)**: Time-constrained prompts (such as typing verification codes or solving arithmetic operations within a short countdown window) that distribute rewards or apply fines and curse debuffs upon expiration or failure.
  - **Reaction Encounters**: Lightweight reaction-based bounties designed for rapid community participation.

---

## 💾 Persistence Layer

The application utilizes **PostgreSQL** (hosted on **Neon** during deployment) to maintain state across restarts.

### Database Schema

State is stored in the `usuarios_balances` table:

```sql
CREATE TABLE IF NOT EXISTS usuarios_balances (
    user_id VARCHAR(30) PRIMARY KEY,
    i1 INT DEFAULT 0,                 -- Balance in Instance 1
    i2 INT DEFAULT 0,                 -- Balance in Instance 2
    i3 INT DEFAULT 0,                 -- Balance in Instance 3
    cargas_fortuna INT DEFAULT 0,     -- Fortune Blessing charges (Max: 5)
    maldito_hasta INT DEFAULT 0,      -- Curse charges (Max: 5)
    ojo_ladron_usos INT DEFAULT 0     -- Reserved attribute
);
```

### Synthetic Data Representation

```sql
-- Synthetic example illustrating state representation (fictional IDs and artificial balances)
INSERT INTO usuarios_balances (user_id, i1, i2, i3, cargas_fortuna, maldito_hasta, ojo_ladron_usos)
VALUES 
    ('100000000000000001', 350000, 42000, 15000, 2, 0, 0), -- Cúspide tier
    ('100000000000000002',  80000, 95000,     0, 0, 1, 0), -- Élite tier
    ('100000000000000003',  25000, 18000,  5000, 0, 0, 0); -- Pueblo tier
```

> [!NOTE]
> The historical deployment persisted economy and gameplay state for 50+ user records across three instances.

### Atomic Upserts & Batch Operations
- **Single UPSERT**: `set_balance_instancia` uses PostgreSQL `INSERT ... ON CONFLICT (user_id) DO UPDATE SET` formatted with `psycopg2.sql.Identifier` to guarantee parameterized SQL injection safety.
- **Transactional Batch Ingestion (`actualizar_balances_lote`)**: When staff import leaderboard snapshots with `mu!setinstancia`, parsing dozens of entries, all records are executed inside a single transaction block (`with conn: with conn.cursor():`). This replaces multiple separate network handshakes with a single atomic transaction.
- **Batch Read (`obtener_balances_globales_lote`)**: Retrieves consolidated totals for all imported users in a single `SELECT ... WHERE user_id IN %s` query for instant in-memory tier classification.

---

## ⚡ Concurrency & Asynchronous Design

Connecting an asynchronous event loop (`discord.py`) to a synchronous database driver (`psycopg2`) introduces potential blocking risks if database network calls stall the main loop.

To manage this:
- **`en_hilo` Bridge**: A utility function wraps synchronous database routines in `loop.run_in_executor(None, partial(func, *args, **kwargs))`.
- **Targeted Offloading**: Heavy batch processing (`mu!setinstancia`), curse state updates (`mu!givecurse`), mimic minigame resolutions, and raid fortune rolls are delegated to worker threads.
- **Technical Debt & Honesty**: Certain secondary command handlers (e.g., `mu!balance`, `mu!givebuff`, and `mu!setbalance`) still call `psycopg2` synchronously on the main thread. While adequate for the community's historical concurrency, migrating these remaining paths to a fully asynchronous driver (such as `asyncpg`) represents a designated future architectural improvement.

---

## 🧪 Automated Testing

The repository contains an offline automated test suite written using Python's standard `unittest` library and fully compatible with `pytest`. The test suite runs with **zero external dependencies**, requiring no active Discord connection and no live database.

```bash
# Run tests via Python's standard test runner
python -m unittest discover tests

# Or run tests using pytest
pytest -v
```

### Test Coverage Highlights (35 Passed Tests)
- **Tier Classification (`tests/test_economy.py`)**: Boundary value testing for all threshold cutoffs (`0`, `39,999`, `40,000`, `119,999`, `120,000`, `299,999`, `300,000`, and `1,000,000`) and unrecorded users (`None`).
- **Metadata Integrity**: Validates presence of required keys, visual emojis, and color assignments across all tiers.
- **Taxation & Subsidy Calculation**: Verifies multipliers and math for Pueblo (+15%), Clase Media (±0%), Élite (-15%), Cúspide (-35%), and Neutral.
- **Inter-Instance Mitigation**: Verifies the halved tax formula for Cúspide (yielding `0.82` with round-half-to-even) and Élite (`0.93`) when local balance is $< 40,000$.
- **Gameplay Buffs & Debuffs**: Mocked probabilistic verification of Curse sabotage ($< 50\%$ zeroes payout, $\ge 50\%$ consumes charge safely) and Fortune bonuses ($+0.15$ multiplier).
- **Special Event Bypass**: Verifies that special events bypass curse checks without modifying or consuming curse charges.
- **UI Formatting (`tests/test_formatting.py`)**: Receipt string generation, multiplier formatting (`+15%`, `-15%`, `±0%`), and environment variable ID parser resilience.

---

## 💻 Tech Stack

- **Language**: Python 3.10+
- **Platform Framework**: `discord.py` 2.3+ (Async gateway client)
- **Database & Driver**: PostgreSQL / `psycopg2-binary` (relational storage, atomic upserts)
- **Hosting / Deployment (Historical)**: Render (Web Service) + Neon (Serverless PostgreSQL)
- **Auxiliary HTTP Server**: Flask 3.x (keep-alive health endpoint)
- **Environment & Configuration**: `python-dotenv`
- **Testing**: `unittest` (standard library), `pytest`

---

## 📁 Project Structure

```text
.
├── .env.example              # Template containing all environment variable placeholders
├── .gitignore                # Excludes secrets, caches, virtualenvs, and database dumps
├── README.md                 # Complete system documentation
├── requirements.txt          # Pinned dependency ranges
├── balance.py                # PostgreSQL persistence layer, connection handling, and batch operations
├── bot.py                    # Discord bot entry point, command routing, and background loop
├── config.py                 # Central configuration, tier constants, and environment parsing
├── economy.py                # Core domain logic: tier classification, taxation, buffs, and curses
├── embeds.py                 # Discord embed visual builders and formatted receipt generators
├── events.py                 # Event catalog definitions (simple encounters, raids, special minigames)
├── scripts/
│   └── get_db_stats.py       # Standalone CLI administrative script for database inspection
└── tests/
    ├── __init__.py           # Package marker for automated tests
    ├── test_economy.py       # Unit tests for economic domain formulas and status modifiers
    └── test_formatting.py    # Unit tests for UI receipts and configuration parsers
```

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- A PostgreSQL database instance (local or hosted like Neon/Supabase)

### 1. Clone the Repository
```bash
git clone https://github.com/LE0ST/AldeanoGremioRender.git
cd AldeanoGremioRender
```

### 2. Set Up a Virtual Environment
```bash
# Create virtual environment
python -m venv venv

# Activate on Windows (PowerShell)
.\venv\Scripts\Activate.ps1

# Activate on Linux/macOS
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Copy `.env.example` to `.env` and fill in your credentials:
```bash
cp .env.example .env
```

Required variables:
```env
# Discord Bot Credentials
TOKEN=your_discord_bot_token_here

# PostgreSQL Connection String
DATABASE_URL=postgresql://user:password@localhost:5432/dbname?sslmode=disable

# Environment Mode ('dev' for rapid 10s-20s event loops, 'prod' for 1.5h-3h intervals)
ENV=dev

# Channel IDs for Event Spawns (Numeric Snowflake IDs)
CANAL_I1_ID=0
CANAL_I2_ID=0
CANAL_I3_ID=0

# Staff and Alert Role IDs
ROL_AVISO_ID=0
ROL_STAFF_ID=0
```

### 5. Run the Application
```bash
python bot.py
```
*(On initial startup, `cargar_balances()` automatically validates the PostgreSQL connection and creates the `usuarios_balances` table if it does not exist).*

### 6. Run the Test Suite
```bash
# Run using standard library unittest
python -m unittest discover tests

# Or run using pytest
pytest -v
```

---

## 📸 Screenshots & Demonstrations

<!--
TODO: Add 2-4 anonymized screenshots demonstrating:
1. An economy breakdown embed (`mu!balance`).
2. An interactive raid outcome with receipt details (`EVENTO_MAZMORRA`).
3. An administrative batch sync result (`mu!setinstancia`).
4. An interactive minigame prompt (e.g., Mimic arithmetic challenge or Tax Collector).
Ensure all screenshots crop out private server names, user IDs, or personal chat history before publication.
-->

| Feature | Visual Demonstration | Description |
| :--- | :---: | :--- |
| **Economy Receipt** | *[Placeholder: Screenshot of `mu!balance` embed]* | Displays instance breakdown, total global wealth, and active tier modifier |
| **Dungeon Raid Resolution** | *[Placeholder: Screenshot of Raid results]* | Shows cooperative prize division, individual tax deductions, and Fortune procs |
| **Interactive Minigame** | *[Placeholder: Screenshot of Mimic/Tax event]* | Demonstrates real-time reaction/puzzle prompts in Discord chat |

---

## 💡 Engineering Lessons Learned

1. **Modeling Complex Domain Logic Outside Frameworks**: Isolating the economy calculations in `economy.py` from Discord-specific structures allowed the business logic to remain deterministic, easily testable, and completely decoupled from network clients.
2. **Bridging Asynchronous and Synchronous Architectures**: Integrating `psycopg2` with `discord.py` highlighted the criticality of event loop hygiene. Identifying which operations warrant thread offloading (`loop.run_in_executor`) versus which can remain in-line prevents UI freezing without premature overengineering.
3. **Database Performance via Batch Transactions**: Transitioning bulk leaderboard updates from individual queries to a single transactional `UPSERT` demonstrated how reducing network round-trips is often a vastly more impactful optimization than micro-optimizing application code.
4. **Resilience Through Graceful Degradation**: Implementing defaults for missing or unrecorded users (falling back to neutral multipliers and fallback Unicode emojis) prevents catastrophic runtime crashes when external inputs diverge from expected formats.

---

## 📈 Project Status & Potential Improvements

### Current Status
The underlying Discord community concluded its active lifecycle in July 2026. The application is no longer deployed or actively maintained for new gameplay features. The codebase is maintained as an educational reference and portfolio demonstration of backend Python development.

### Potential Future Improvements
- **Fully Asynchronous Database Driver**: Migrate from `psycopg2` to `asyncpg` to achieve non-blocking I/O across 100% of database paths without relying on thread pools.
- **Connection Pooling**: Introduce connection pooling (`asyncpg.create_pool` or `psycopg2.pool.ThreadedConnectionPool`) to reuse TCP connections rather than opening individual connections per routine.
- **Integration Test Suite**: Add integration tests using `testcontainers` or an ephemeral PostgreSQL instance to test real database triggers alongside mock tests.
- **CI Pipeline**: Implement a GitHub Actions workflow running `pytest` and linter checks (`ruff`/`flake8`) on pull requests.
