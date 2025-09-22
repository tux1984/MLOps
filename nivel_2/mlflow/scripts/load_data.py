import pandas as pd
from sqlalchemy import create_engine, text

# Configuración de conexión (ajústala si corres localmente en vez de dentro de Docker)
DB_URI = "postgresql://mlflow_user:mlflow_pass@postgres:5432/mlflowdb"

CSV_PATH = "data/sample_data.csv"
TABLE_NAME = "credit_data"

print("📥 Starting data load process...")

try:
    # Conectar a PostgreSQL
    engine = create_engine(DB_URI)
    conn = engine.connect()

    # Borrar la tabla si ya existe
    conn.execute(text(f"DROP TABLE IF EXISTS {TABLE_NAME};"))
    print(f"🗑️  Existing table '{TABLE_NAME}' dropped (if existed).")

    # Cargar CSV
    df = pd.read_csv(CSV_PATH)
    print(f"📊 CSV loaded successfully with {len(df)} records.")

    # Insertar en PostgreSQL (pandas crea la tabla automáticamente)
    df.to_sql(TABLE_NAME, engine, if_exists="replace", index=False)
    print(f"✅ Table '{TABLE_NAME}' created and populated with {len(df)} records.")

except Exception as e:
    print("❌ Error during load:", e)

finally:
    conn.close()
    engine.dispose()
    print("🔌 Connection closed.")
