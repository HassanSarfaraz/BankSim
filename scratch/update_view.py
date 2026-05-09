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
            u.profile_image
        FROM users u
        JOIN customers c ON u.user_id = c.user_id
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE a.status = 'active';
        """)
        conn.commit()
        print("View updated successfully with user_id.")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    update_view()
