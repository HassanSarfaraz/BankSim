-- CS232 - Database Management System
-- Project: SecureBank Management System
-- Triggers and Stored Procedures

-- 1. Trigger Function to Update Account Balance after Transaction
CREATE OR REPLACE FUNCTION update_account_balance()
RETURNS TRIGGER AS $$
BEGIN
    -- If it's a deposit or loan disbursement, increase to_account balance
    IF NEW.txn_type IN ('deposit', 'loan_disbursement') THEN
        IF NEW.to_account IS NOT NULL THEN
            UPDATE accounts SET balance = balance + NEW.amount WHERE account_id = NEW.to_account;
        END IF;
    
    -- If it's a withdrawal or loan repayment, decrease from_account balance
    ELSIF NEW.txn_type IN ('withdrawal', 'loan_repayment') THEN
        IF NEW.from_account IS NOT NULL THEN
            UPDATE accounts SET balance = balance - NEW.amount WHERE account_id = NEW.from_account;
        END IF;
    
    -- If it's a transfer, decrease from_account and increase to_account
    ELSIF NEW.txn_type = 'transfer' THEN
        IF NEW.from_account IS NOT NULL AND NEW.to_account IS NOT NULL THEN
            UPDATE accounts SET balance = balance - NEW.amount WHERE account_id = NEW.from_account;
            UPDATE accounts SET balance = balance + NEW.amount WHERE account_id = NEW.to_account;
        END IF;
    END IF;
    
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger for Transactions
CREATE TRIGGER trg_after_transaction_insert
AFTER INSERT ON transactions
FOR EACH ROW
EXECUTE FUNCTION update_account_balance();

-- 2. Stored Procedure for Atomic Transfers
CREATE OR REPLACE PROCEDURE sp_transfer(
    p_from_account INTEGER,
    p_to_account INTEGER,
    p_amount DECIMAL,
    p_description TEXT
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_from_balance DECIMAL;
BEGIN
    -- Check if from_account exists and get balance with lock
    SELECT balance INTO v_from_balance FROM accounts WHERE account_id = p_from_account FOR UPDATE;
    
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Source account % not found', p_from_account;
    END IF;
    
    -- Check for sufficient funds
    IF v_from_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds in account %', p_from_account;
    END IF;
    
    -- Check if to_account exists
    PERFORM 1 FROM accounts WHERE account_id = p_to_account;
    IF NOT FOUND THEN
        RAISE EXCEPTION 'Destination account % not found', p_to_account;
    END IF;
    
    -- Insert transaction (the trigger will handle balance updates)
    INSERT INTO transactions (from_account, to_account, amount, txn_type, description)
    VALUES (p_from_account, p_to_account, p_amount, 'transfer', p_description);
    
    COMMIT;
END;
$$;
