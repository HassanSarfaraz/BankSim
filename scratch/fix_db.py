import psycopg2
from config import Config

def update_db():
    try:
        conn = psycopg2.connect(
            user=Config.POSTGRES_USER,
            password=Config.POSTGRES_PASSWORD,
            host=Config.POSTGRES_HOST,
            port=Config.POSTGRES_PORT,
            database=Config.POSTGRES_DB
        )
        cur = conn.cursor()
        
        # 1. Update accounts constraint
        try:
            cur.execute("ALTER TABLE accounts DROP CONSTRAINT accounts_account_type_check;")
        except Exception as e:
            print("Constraint drop error (might not exist):", e)
            conn.rollback()
        
        try:
            cur.execute("ALTER TABLE accounts ADD CONSTRAINT accounts_account_type_check CHECK (account_type IN ('checking','savings','credit','loan','business'));")
        except Exception as e:
            print("Constraint add error:", e)
            conn.rollback()

        # 2. Add previous_login to users
        try:
            cur.execute("ALTER TABLE users ADD COLUMN previous_login TIMESTAMP;")
        except Exception as e:
            print("Column add error (might exist):", e)
            conn.rollback()
            
        # 3. Update view
        try:
            cur.execute("DROP VIEW active_accounts_view;")
            conn.commit()
        except:
            conn.rollback()

        cur.execute("""
        CREATE OR REPLACE VIEW active_accounts_view AS
        SELECT 
            c.customer_id,
            c.first_name || ' ' || c.last_name AS customer_name,
            a.account_number,
            a.account_type,
            a.balance,
            a.status,
            u.is_active,
            u.user_id,
            u.last_login,
            u.profile_image,
            u.previous_login
        FROM users u
        JOIN customers c ON u.user_id = c.user_id
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE a.status = 'active';
        """)

        conn.commit()
        print("Database updated successfully.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_db()
