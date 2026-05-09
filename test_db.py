import psycopg2
from config import Config

def test_db_connection():
    print("--- Testing PostgreSQL Connection ---")
    try:
        conn = psycopg2.connect(
            dbname=Config.POSTGRES_DB,
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT
        )
        print("SUCCESS: Connected to PostgreSQL!")
        cur = conn.cursor()
        cur.execute("SELECT version();")
        version = cur.fetchone()
        print(f"Database version: {version[0]}")
        cur.close()
        conn.close()
    except Exception as e:
        print(f"FAILED: {str(e)}")

if __name__ == "__main__":
    test_db_connection()
