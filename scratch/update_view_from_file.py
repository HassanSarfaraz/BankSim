import psycopg2
from config import Config

def update_view():
    try:
        conn = psycopg2.connect(
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DB
        )
        cur = conn.cursor()
        
        with open('sql/views.sql', 'r') as f:
            sql = f.read()
            
        # Execute the first view creation (active_accounts_view)
        # To be safe, we'll just execute the whole file
        cur.execute(sql)
        conn.commit()
        print("Views updated successfully from views.sql.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_view()
