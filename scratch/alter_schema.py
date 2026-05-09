import psycopg2
from config import Config

def update_schema():
    try:
        conn = psycopg2.connect(
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DB
        )
        cur = conn.cursor()
        cur.execute("ALTER TABLE users ALTER COLUMN profile_image TYPE VARCHAR(255) USING NULL;")
        conn.commit()
        print("Schema altered successfully.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_schema()
