import os
import sys
import psycopg2
from psycopg2.extras import RealDictCursor
from dotenv import load_dotenv

# Reconfigurar salida para admitir emojis en consola de Windows
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Asegurar que el directorio raíz está en el path para poder importar config
project_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if project_dir not in sys.path:
    sys.path.insert(0, project_dir)

from config import TIER_CUSPIDE_MIN, TIER_ELITE_MIN, TIER_MEDIO_MIN

# Cargamos el archivo .env del proyecto
dotenv_path = os.path.join(project_dir, ".env")
load_dotenv(dotenv_path)

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("Error: DATABASE_URL no encontrada en el archivo .env")
    exit(1)

try:
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor(cursor_factory=RealDictCursor)
    
    # 1. Total usuarios
    cursor.execute("SELECT COUNT(*) as total FROM usuarios_balances;")
    total_usuarios = cursor.fetchone()['total']
    
    # 2. Suma total de balances
    cursor.execute("SELECT SUM(i1) as sum_i1, SUM(i2) as sum_i2, SUM(i3) as sum_i3 FROM usuarios_balances;")
    sumas = cursor.fetchone()
    
    # 3. Distribución por Tiers (dinámica con los valores de config.py)
    query_tiers = """
        SELECT 
            COUNT(CASE WHEN (i1 + i2 + i3) >= %s THEN 1 END) as cuspide,
            COUNT(CASE WHEN (i1 + i2 + i3) >= %s AND (i1 + i2 + i3) < %s THEN 1 END) as elite,
            COUNT(CASE WHEN (i1 + i2 + i3) >= %s AND (i1 + i2 + i3) < %s THEN 1 END) as medio,
            COUNT(CASE WHEN (i1 + i2 + i3) < %s THEN 1 END) as pueblo
        FROM usuarios_balances;
    """
    cursor.execute(query_tiers, (
        TIER_CUSPIDE_MIN,
        TIER_ELITE_MIN, TIER_CUSPIDE_MIN,
        TIER_MEDIO_MIN, TIER_ELITE_MIN,
        TIER_MEDIO_MIN
    ))
    distribution = cursor.fetchone()
    
    # 4. Top 10 más ricos
    cursor.execute("""
        SELECT user_id, i1, i2, i3, (i1 + i2 + i3) as total
        FROM usuarios_balances
        ORDER BY total DESC
        LIMIT 10;
    """)
    top_10 = cursor.fetchall()
    
    print("--- ESTADISTICAS DE LA BASE DE DATOS ---")
    print(f"Total Usuarios Registrados: {total_usuarios}")
    print(f"Total Kakera i1: {sumas['sum_i1'] or 0:,}")
    print(f"Total Kakera i2: {sumas['sum_i2'] or 0:,}")
    print(f"Total Kakera i3: {sumas['sum_i3'] or 0:,}")
    print("\n--- DISTRIBUCION DE TIERS ---")
    print(f"👑 Cúspide (>={TIER_CUSPIDE_MIN//1000}k): {distribution['cuspide']} usuarios")
    print(f"💎 Élite ({TIER_ELITE_MIN//1000}k-{TIER_CUSPIDE_MIN//1000}k): {distribution['elite']} usuarios")
    print(f"⚖️ Clase Media ({TIER_MEDIO_MIN//1000}k-{TIER_ELITE_MIN//1000}k): {distribution['medio']} usuarios")
    print(f"🌱 Pueblo (<{TIER_MEDIO_MIN//1000}k): {distribution['pueblo']} usuarios")
    
    print("\n--- TOP 10 RIQUEZA GLOBAL ---")
    for idx, row in enumerate(top_10, 1):
        print(f"{idx}. ID: {row['user_id']} | Total: {row['total']:,} | i1: {row['i1']:,} | i2: {row['i2']:,} | i3: {row['i3']:,}")
        
except Exception as e:
    print(f"Error de base de datos: {e}")
finally:
    if 'conn' in locals() and conn:
        conn.close()
