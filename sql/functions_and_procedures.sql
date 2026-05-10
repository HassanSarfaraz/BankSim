-- functions_and_procedures.sql

-- FUNCTION: Calculate EMI
CREATE OR REPLACE FUNCTION calculate_emi(
    principal DECIMAL,
    annual_rate DECIMAL,
    tenure_months INT
) RETURNS DECIMAL AS $$
DECLARE
    monthly_rate DECIMAL;
    emi DECIMAL;
BEGIN
    monthly_rate := annual_rate / 12.0;
    emi := principal * monthly_rate * POWER(1 + monthly_rate, tenure_months)
           / (POWER(1 + monthly_rate, tenure_months) - 1);
    RETURN ROUND(emi, 2);
END;
$$ LANGUAGE plpgsql;

-- PROCEDURE: Transfer funds atomically
CREATE OR REPLACE PROCEDURE transfer_funds(
    p_from_account BIGINT,
    p_to_account BIGINT,
    p_amount DECIMAL,
    p_description TEXT
)
LANGUAGE plpgsql AS $$
DECLARE
    v_balance DECIMAL;
BEGIN
    -- Lock source row
    SELECT balance INTO v_balance FROM accounts
    WHERE account_id = p_from_account FOR UPDATE;

    IF v_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds: balance is %', v_balance;
    END IF;

    -- Debit
    INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
    VALUES (p_from_account, 'withdrawal', p_amount, p_description, NOW());

    -- Credit
    INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
    VALUES (p_to_account, 'deposit', p_amount, p_description, NOW());

    -- Note: Procedures in PL/pgSQL can't have COMMIT if called within an atomic context, 
    -- but here we assume it's the top-level call or handled by Flask.
END;
$$;

-- PROCEDURE: Monthly interest posting
CREATE OR REPLACE PROCEDURE post_monthly_interest()
LANGUAGE plpgsql AS $$
DECLARE
    acc RECORD;
    interest_amount DECIMAL;
BEGIN
    FOR acc IN 
        SELECT account_id, balance, interest_rate 
        FROM accounts 
        WHERE account_type = 'savings' AND status = 'active'
    LOOP
        interest_amount := ROUND(acc.balance * (acc.interest_rate / 12), 2);
        INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
        VALUES (acc.account_id, 'deposit', interest_amount, 'Monthly interest credit', NOW());
    END LOOP;
END;
$$;

-- PROCEDURE: generate_statement (Using Explicit Cursor)
CREATE OR REPLACE PROCEDURE generate_statement(p_account_id BIGINT)
LANGUAGE plpgsql AS $$
DECLARE
    txn_cursor CURSOR FOR
        SELECT transaction_id, transaction_type, amount, transaction_date, description
        FROM transactions
        WHERE account_id = p_account_id
          AND transaction_date >= DATE_TRUNC('month', CURRENT_DATE)
        ORDER BY transaction_date;
    txn_row RECORD;
BEGIN
    OPEN txn_cursor;
    LOOP
        FETCH txn_cursor INTO txn_row;
        EXIT WHEN NOT FOUND;
        RAISE NOTICE 'Txn %: % | Amount: % | Date: %',
            txn_row.transaction_id,
            txn_row.transaction_type,
            txn_row.amount,
            txn_row.transaction_date;
    END LOOP;
    CLOSE txn_cursor;
END;
$$;




-- Fix the duplicate key bug: add ON CONFLICT DO NOTHING + recursion guard
CREATE OR REPLACE FUNCTION flag_large_transaction()
RETURNS TRIGGER AS $$
BEGIN
    -- Only run at depth 1 to prevent double-firing on partitioned tables
    IF pg_trigger_depth() > 1 THEN
        RETURN NEW;
    END IF;

    IF NEW.amount >= 10000 THEN
        INSERT INTO fraud_alerts(transaction_id, account_id, alert_type, severity, status)
        VALUES (NEW.transaction_id, NEW.account_id, 'large_transaction', 'high', 'open')
        ON CONFLICT DO NOTHING;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;



-- 1. Update the function to set balance_after directly
CREATE OR REPLACE FUNCTION handle_transaction_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_new_balance DECIMAL(15,2);
BEGIN
    -- Process if status is 'completed'
    IF (TG_OP = 'INSERT' AND NEW.status = 'completed') OR 
       (TG_OP = 'UPDATE' AND OLD.status = 'pending' AND NEW.status = 'completed') THEN
        
        -- Update the account balance and get the NEW balance
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id
            RETURNING balance INTO v_new_balance;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id
            RETURNING balance INTO v_new_balance;
        END IF;
        
        -- Set the snapshot for this transaction row
        NEW.balance_after := v_new_balance;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- 2. Change it to a BEFORE trigger (much more reliable)
DROP TRIGGER IF EXISTS trg_balance_management ON transactions;
CREATE TRIGGER trg_balance_management
BEFORE INSERT OR UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION handle_transaction_balance();



-- This syncs the snapshot with the current account balance for the most recent transaction
UPDATE transactions t
SET balance_after = a.balance
FROM accounts a
WHERE t.account_id = a.account_id
  AND t.balance_after IS NULL;
