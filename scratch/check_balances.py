import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def check_balances():
    try:
        conn = psycopg2.connect(
            dbname=os.environ.get('POSTGRES_DB', 'banksim'),
            user=os.environ.get('POSTGRES_USER', 'postgres'),
            password=os.environ.get('POSTGRES_PASSWORD', 'password'),
            host=os.environ.get('POSTGRES_HOST', 'localhost'),
            port=os.environ.get('POSTGRES_PORT', 5432),
        )
        cur = conn.cursor()
        cur.execute("SELECT transaction_id, amount, balance_after, status FROM transactions ORDER BY transaction_id DESC LIMIT 10;")
        rows = cur.fetchall()
        print("Last 10 transactions:")
        for r in rows:
            print(f"ID: {r[0]}, Amount: {r[1]}, Balance After: {r[2]}, Status: {r[3]}")
        conn.close()
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    check_balances()
