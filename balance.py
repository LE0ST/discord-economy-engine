# =========================
# balance.py — Persistencia en la Nube
# =========================

import os
import logging
from dotenv import load_dotenv

try:
    import psycopg2
    from psycopg2 import sql
    from psycopg2.extras import RealDictCursor
except ImportError as exc:
    logging.error("❌ ERROR CRÍTICO: psycopg2 no está instalado. Instale psycopg2 o psycopg2-binary.")
    raise ImportError(
        "psycopg2 es necesario para ejecutar balance.py. Instale con 'pip install psycopg2-binary'."
    ) from exc

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    logging.error("❌ ERROR CRÍTICO: No se encontró DATABASE_URL en las variables de entorno.")
    raise ValueError("DATABASE_URL faltante")

INSTANCIAS = ("i1", "i2", "i3")

def _obtener_conexion():
    """Crea y devuelve una conexión fresca a la base de datos PostgreSQL."""
    return psycopg2.connect(DATABASE_URL)


def cargar_balances():
    """
    Verifica la conexión a PostgreSQL y crea la tabla automáticamente
    si es la primera vez que se ejecuta en el entorno.
    """
    conn = None
    try:
        conn = _obtener_conexion()
        cursor = conn.cursor()
        
        # Sentencia SQL para inicializar la tabla de forma segura si no existe
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS usuarios_balances (
                user_id VARCHAR(30) PRIMARY KEY,
                i1 INT DEFAULT 0,
                i2 INT DEFAULT 0,
                i3 INT DEFAULT 0,
                cargas_fortuna INT DEFAULT 0,
                maldito_hasta INT DEFAULT 0,
                ojo_ladron_usos INT DEFAULT 0
            );
        """)
        conn.commit()
        cursor.close()
        logging.info("💾 Estructura de PostgreSQL verificada y sincronizada de forma segura.")
    except Exception as e:
        logging.error(f"⚠️ Error al conectar o inicializar PostgreSQL: {e}")
        if conn:
            conn.rollback()
    finally:
        if conn:
            conn.close()


def guardar_balances():
    """Función de compatibilidad heredada. SQL persiste en tiempo real."""
    pass


def balance_global(user_id: int) -> int | None:
    """Suma los balances de todas las instancias del usuario desde SQL."""
    uid = str(user_id)
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT i1, i2, i3 FROM usuarios_balances WHERE user_id = %s;", (uid,))
    fila = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if fila is None:
        return None
        
    return sum(fila)


def balance_por_instancia(user_id: int) -> dict[str, int]:
    """Devuelve el desglose por instancia mapeando la fila SQL a un diccionario."""
    uid = str(user_id)
    conn = _obtener_conexion()
    # RealDictCursor nos permite mapear las columnas directo a nombres de llave
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    cursor.execute("SELECT i1, i2, i3 FROM usuarios_balances WHERE user_id = %s;", (uid,))
    fila = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if fila is None:
        return {inst: 0 for inst in INSTANCIAS}
        
    return {inst: fila.get(inst, 0) for inst in INSTANCIAS}


def set_balance_instancia(user_id: int, instancia: str, cantidad: int):
    """
    Actualiza el balance local usando la sintaxis UPSERT (ON CONFLICT) de PostgreSQL.
    Si el usuario no existe, lo inserta; si ya existe, actualiza solo la instancia dada.
    """
    uid = str(user_id)
    
    # Validamos preventivamente que la columna solicitada sea una instancia real
    if instancia not in INSTANCIAS:
        return

    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    # Inyección segura usando placeholders de psycopg2 (%s) e identificadores sql.Identifier para evitar ataques de inyección SQL
    query = sql.SQL("""
        INSERT INTO usuarios_balances (user_id, {instancia})
        VALUES (%s, %s)
        ON CONFLICT (user_id)
        DO UPDATE SET {instancia} = EXCLUDED.{instancia};
    """).format(instancia=sql.Identifier(instancia))
    
    try:
        cursor.execute(query, (uid, cantidad))
        conn.commit()
        logging.info(f"💾 SQL Upsert exitoso para {uid} en {instancia.upper()} -> {cantidad:,}")
    except Exception as e:
        conn.rollback()
        logging.error(f"❌ Error al ejecutar set_balance en SQL: {e}")
    finally:
        cursor.close()
        conn.close()

# =========================
# GESTIÓN DE EFECTOS DE ESTADO (BUFFS/DEBUFFS) - SQL
# =========================

def modificar_cargas_fortuna(user_id: int, cantidad: int):
    """
    Suma o resta cargas de la Bendición de Fortuna a un usuario.
    cantidad puede ser positiva (dar cargas) o negativa (consumir carga).
    """
    uid = str(user_id)
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    # Usamos COALESCE para evitar problemas si el registro está vacío, defalteando a 0
    query = """
        INSERT INTO usuarios_balances (user_id, cargas_fortuna)
        VALUES (%s, LEAST(GREATEST(0, %s), 5))
        ON CONFLICT (user_id)
        DO UPDATE SET cargas_fortuna = LEAST(GREATEST(0, COALESCE(usuarios_balances.cargas_fortuna, 0) + %s), 5);
    """
    try:
        cursor.execute(query, (uid, cantidad, cantidad))
        conn.commit()
        logging.info(f"✨ SQL: Cargas de fortuna modificadas para {uid} en {cantidad}")
    except Exception as e:
        conn.rollback()
        logging.error(f"❌ Error al modificar cargas de fortuna en SQL: {e}")
    finally:
        cursor.close()
        conn.close()


def obtener_cargas_fortuna(user_id: int) -> int:
    """Devuelve la cantidad actual de cargas de fortuna que tiene el jugador."""
    uid = str(user_id)
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT cargas_fortuna FROM usuarios_balances WHERE user_id = %s;", (uid,))
    fila = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if fila is None:
        return 0
    return fila[0]

def modificar_cargas_maldicion(user_id: int, cantidad: int):
    """
    Suma o resta cargas de la Maldición de Torpeza a un usuario en la columna 'maldito_hasta'.
    'cantidad' puede ser positiva (añadir de daño) o negativa (limpiar cargas al jugar).
    """
    uid = str(user_id)
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    # Usamos COALESCE para tratar la columna maldito_hasta como un contador de cargas (defaltea a 0)
    query = """
        INSERT INTO usuarios_balances (user_id, maldito_hasta)
        VALUES (%s, LEAST(GREATEST(0, %s), 5))
        ON CONFLICT (user_id)
        DO UPDATE SET maldito_hasta = LEAST(GREATEST(0, COALESCE(usuarios_balances.maldito_hasta, 0) + %s), 5);
    """
    try:
        cursor.execute(query, (uid, cantidad, cantidad))
        conn.commit()
        logging.info(f"💀 SQL: Cargas de maldición modificadas para {uid} en {cantidad}")
    except Exception as e:
        conn.rollback()
        logging.error(f"❌ Error al modificar cargas de maldición en SQL: {e}")
    finally:
        cursor.close()
        conn.close()


def obtener_cargas_maldicion(user_id: int) -> int:
    """Devuelve la cantidad actual de cargas de torpeza que tiene el jugador."""
    uid = str(user_id)
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    cursor.execute("SELECT maldito_hasta FROM usuarios_balances WHERE user_id = %s;", (uid,))
    fila = cursor.fetchone()
    
    cursor.close()
    conn.close()
    
    if fila is None or fila[0] is None:
        return 0
    return int(fila[0])

# =========================
# CASTIGO DEL COBRADOR DE IMPUESTOS
# =========================

def ejecutar_castigo_sql(instancia: str) -> int | None:
    """
    Selecciona al azar un usuario con al menos 2,000 Kakera en la instancia dada,
    le confisca 1,500 Kakera y devuelve su user_id.
    Retorna None si no hay ningún usuario elegible.
    """
    if instancia not in INSTANCIAS:
        return None

    conn = None
    try:
        conn = _obtener_conexion()
        cursor = conn.cursor()

        # Selección aleatoria de víctima con fondos suficientes
        query_select = sql.SQL(
            "SELECT user_id FROM usuarios_balances WHERE {instancia} >= 2000 ORDER BY RANDOM() LIMIT 1;"
        ).format(instancia=sql.Identifier(instancia))
        cursor.execute(query_select)
        fila = cursor.fetchone()

        if fila is None:
            return None

        user_id = int(fila[0])

        # Confiscación: restamos 1,500, con piso en 0
        query_update = sql.SQL("""
            UPDATE usuarios_balances
            SET {instancia} = GREATEST(0, {instancia} - 1500)
            WHERE user_id = %s;
        """).format(instancia=sql.Identifier(instancia))
        cursor.execute(query_update, (str(user_id),))
        conn.commit()
        logging.info(f"👺 SQL: Castigo del Cobrador ejecutado sobre {user_id} en {instancia.upper()}")
        return user_id

    except Exception as e:
        logging.error(f"❌ Error en ejecutar_castigo_sql: {e}")
        if conn:
            conn.rollback()
        return None
    finally:
        if conn:
            conn.close()


def actualizar_balances_lote(datos_usuarios: list[tuple[int, int]], instancia: str) -> list[str]:
    """
    Actualiza masivamente los balances de una lista de usuarios en una única transacción SQL.
    datos_usuarios: lista de tuplas (user_id, cantidad)
    instancia: nombre de la columna ('i1', 'i2', 'i3')
    """
    if instancia not in INSTANCIAS:
        return []

    logs = []
    conn = None
    try:
        conn = _obtener_conexion()
        cursor = conn.cursor()

        # Inyección segura usando identificadores psycopg2.sql
        query = sql.SQL("""
            INSERT INTO usuarios_balances (user_id, {instancia})
            VALUES (%s, %s)
            ON CONFLICT (user_id)
            DO UPDATE SET {instancia} = EXCLUDED.{instancia};
        """).format(instancia=sql.Identifier(instancia))

        for user_id, cantidad in datos_usuarios:
            uid = str(user_id)
            cursor.execute(query, (uid, cantidad))
            logs.append(f"💾 SQL Upsert masivo exitoso para {uid} en {instancia.upper()} -> {cantidad:,}")

        conn.commit()
        logging.info(f"💾 Transacción por lote finalizada con éxito. {len(datos_usuarios)} registros guardados en {instancia.upper()}.")
    except Exception as e:
        if conn:
            conn.rollback()
        logging.error(f"❌ Error al ejecutar actualización por lote en SQL: {e}")
        raise e
    finally:
        if conn:
            cursor.close()
            conn.close()

    return logs


def obtener_balances_globales_lote(user_ids: list[int]) -> dict[int, int]:
    """
    Obtiene los balances globales de una lista de usuarios en una única consulta SQL.
    """
    if not user_ids:
        return {}
        
    uids = [str(uid) for uid in user_ids]
    conn = _obtener_conexion()
    cursor = conn.cursor()
    
    # Usamos placeholders dinámicos para evitar inyección en la lista
    placeholders = ", ".join(["%s"] * len(uids))
    query = f"SELECT user_id, (COALESCE(i1, 0) + COALESCE(i2, 0) + COALESCE(i3, 0)) FROM usuarios_balances WHERE user_id IN ({placeholders});"
    
    try:
        cursor.execute(query, tuple(uids))
        filas = cursor.fetchall()
        return {int(row[0]): row[1] for row in filas}
    except Exception as e:
        logging.error(f"Error en obtener_balances_globales_lote: {e}")
        return {}
    finally:
        cursor.close()
        conn.close()