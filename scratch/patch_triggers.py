import psycopg2
from config import Config

def patch():
    conn = psycopg2.connect(
        user=Config.POSTGRES_USER,
        password=Config.POSTGRES_PASSWORD,
        host=Config.POSTGRES_HOST,
        port=Config.POSTGRES_PORT,
        database=Config.POSTGRES_DB
    )
    cur = conn.cursor()
    
    # 1. update_balance_after_txn
    cur.execute("""
    CREATE OR REPLACE FUNCTION update_balance_after_txn()
    RETURNS TRIGGER AS $$
    DECLARE
        v_new_balance DECIMAL(15,2);
    BEGIN
        IF NEW.status = 'completed' THEN
            IF NEW.transaction_type = 'deposit' THEN
                UPDATE accounts SET balance = balance + NEW.amount
                WHERE account_id = NEW.account_id
                RETURNING balance INTO v_new_balance;
            ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
                UPDATE accounts SET balance = balance - NEW.amount
                WHERE account_id = NEW.account_id
                RETURNING balance INTO v_new_balance;
            END IF;
            NEW.balance_after := v_new_balance;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    cur.execute("DROP TRIGGER IF EXISTS trg_update_balance ON transactions")
    cur.execute("CREATE TRIGGER trg_update_balance BEFORE INSERT ON transactions FOR EACH ROW EXECUTE FUNCTION update_balance_after_txn()")
    
    # 2. update_balance_after_txn_update
    cur.execute("""
    CREATE OR REPLACE FUNCTION update_balance_after_txn_update()
    RETURNS TRIGGER AS $$
    DECLARE
        v_new_balance DECIMAL(15,2);
    BEGIN
        IF OLD.status = 'pending' AND NEW.status = 'completed' THEN
            IF NEW.transaction_type = 'deposit' THEN
                UPDATE accounts SET balance = balance + NEW.amount
                WHERE account_id = NEW.account_id
                RETURNING balance INTO v_new_balance;
            ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
                UPDATE accounts SET balance = balance - NEW.amount
                WHERE account_id = NEW.account_id
                RETURNING balance INTO v_new_balance;
            END IF;
            UPDATE transactions SET balance_after = v_new_balance WHERE transaction_id = NEW.transaction_id;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    conn.commit()
    conn.close()
    print("Patch complete.")

if __name__ == "__main__":
    patch()
