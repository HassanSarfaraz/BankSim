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
    
    # Improved function with recursion protection
    cur.execute("""
    CREATE OR REPLACE FUNCTION handle_transaction_balance()
    RETURNS TRIGGER AS $$
    DECLARE
        v_new_balance DECIMAL(15,2);
    BEGIN
        -- Recursion protection: don't run if this is already an internal update to set balance_after
        IF (pg_trigger_depth() > 1) THEN
            RETURN NEW;
        END IF;

        -- Process if status is changing to 'completed' or inserted as 'completed'
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
            
            -- 2. Update the transaction record snapshot
            IF v_new_balance IS NOT NULL THEN
                UPDATE transactions SET balance_after = v_new_balance WHERE transaction_id = NEW.transaction_id;
            END IF;
        END IF;
        RETURN NEW;
    END;
    $$ LANGUAGE plpgsql;
    """)
    
    conn.commit()
    conn.close()
    print("Trigger protection logic updated.")

if __name__ == "__main__":
    patch()
