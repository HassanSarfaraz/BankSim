import psycopg2
from config import Config

def check_trigger():
    try:
        conn = psycopg2.connect(
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DB
        )
        cur = conn.cursor()
        cur.execute("SELECT trigger_name FROM information_schema.triggers WHERE event_object_table = 'login_attempts';")
        triggers = cur.fetchall()
        print("Triggers on 'login_attempts' table:")
        for tg in triggers:
            print(f"- {tg[0]}")
        
        # Also check current count for a test user if possible
        cur.execute("SELECT username, is_active FROM users LIMIT 5;")
        users = cur.fetchall()
        print("\nSample Users Status:")
        for u in users:
            print(f"- {u[0]}: active={u[1]}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_trigger()
