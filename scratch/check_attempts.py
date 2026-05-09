import psycopg2
from config import Config

def check_attempts():
    try:
        conn = psycopg2.connect(
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DB
        )
        cur = conn.cursor()
        cur.execute("""
            SELECT u.username, COUNT(l.attempt_id) 
            FROM users u
            LEFT JOIN login_attempts l ON u.user_id = l.user_id
            WHERE l.success = FALSE AND l.attempt_time > NOW() - INTERVAL '15 minutes'
            GROUP BY u.username;
        """)
        counts = cur.fetchall()
        print("Failed attempts in last 15 mins:")
        for name, count in counts:
            print(f"- {name}: {count}")
            
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_attempts()
