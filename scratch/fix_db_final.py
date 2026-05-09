import psycopg2
from config import Config

def fix():
    conn = psycopg2.connect(
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT,
        database=Config.POSTGRES_DB
    )
    cur = conn.cursor()
    
    try:
        # 0. Drop views that depend on profile_image
        print("Dropping views...")
        cur.execute("DROP VIEW IF EXISTS active_accounts_view CASCADE")
        
        # 1. Convert profile_image to VARCHAR
        print("Altering profile_image to VARCHAR...")
        cur.execute("ALTER TABLE users ALTER COLUMN profile_image TYPE VARCHAR(255) USING NULL")
        
        # 2. Update account numbers to use PK99-BANK format consistently
        print("Standardizing account numbers...")
        cur.execute("UPDATE accounts SET account_number = REPLACE(account_number, 'PK-BANK', 'PK99-BANK')")
        
        # 3. Set test profile images for default users
        print("Setting test profile images...")
        cur.execute("UPDATE users SET profile_image = 'profile_pics/default.png' WHERE user_id = 1")
        cur.execute("UPDATE users SET profile_image = 'profile_pics/2.jpg' WHERE user_id = 2")
        
        conn.commit()
        
        # 4. Recreate views from views.sql
        print("Recreating views...")
        with open('sql/views.sql', 'r') as f:
            sql = f.read()
        cur.execute(sql)
        conn.commit()
        
        print("Done!")
    except Exception as e:
        conn.rollback()
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    fix()
