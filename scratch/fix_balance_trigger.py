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
    
    # 1. Improved function to update balance and set balance_after
    cur.execute("""
    CREATE OR REPLACE FUNCTION handle_transaction_balance()
    RETURNS TRIGGER AS $$
    DECLARE
        v_new_balance DECIMAL(15,2);
    BEGIN
        -- Only process if status is changing to 'completed' or inserted as 'completed'
        IF (TG_OP = 'INSERT' AND NEW.status = 'completed') OR 
           (TG_OP = 'UPDATE' AND OLD.status = 'pending' AND NEW.status = 'completed') THEN
            
            -- 1. Update the account balance
            IF NEW.transaction_type = 'deposit' THEN
                UPDATE accounts SET balance = balance + NEW.amount
                WHERE account_id = NEW.account_id
                RETURNING balance INTO v_new_balance;
            ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
                UPDATE accounts SET balance = balance - NEW.amount
                WHERE account_id = NEW.account_id
                RETURNING balance INTO v_new_balance;
            END IF;
            
            -- 2. Update the transaction record with the snapshot
            -- We use a separate UPDATE here because NEW.balance_after can't be set in AFTER trigger
            -- but we use TG_TABLE_NAME to handle partitions correctly if needed
            EXECUTE format('UPDATE %I SET balance_after = $1 WHERE transaction_id = $2', TG_TABLE_NAME)
            USING v_new_balance, NEW.transaction_id;
            
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    # 2. Re-create triggers on the main table (they will propagate to partitions)
    print("Dropping old triggers...")
    cur.execute("DROP TRIGGER IF EXISTS trg_update_balance ON transactions")
    cur.execute("DROP TRIGGER IF EXISTS trg_update_balance_on_approve ON transactions")
    
    print("Creating new unified balance trigger...")
    # NOTE: In Postgres partitions, triggers should ideally be on the child tables
    # but since we have a small number, we can apply to them directly or the parent.
    # To be safe, we apply to the parent and ensures it's AFTER.
    cur.execute("""
    CREATE TRIGGER trg_balance_management
    AFTER INSERT OR UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION handle_transaction_balance();
    """)
    
    # 3. Backfill balance_after for existing completed transactions
    # We'll just set it to the current balance for now as a "state of truth"
    print("Backfilling balance_after for existing transactions...")
    cur.execute("""
    UPDATE transactions t
    SET balance_after = a.balance
    FROM accounts a
    WHERE t.account_id = a.account_id 
      AND t.status = 'completed' 
      AND t.balance_after IS NULL;
    """)
    
    conn.commit()
    conn.close()
    print("Patch and backfill complete.")

if __name__ == "__main__":
    patch()
