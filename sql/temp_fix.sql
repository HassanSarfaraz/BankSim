-- Fix transfer_funds procedure
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
    SELECT balance INTO v_balance FROM accounts
    WHERE account_id = p_from_account FOR UPDATE;

    IF v_balance < p_amount THEN
        RAISE EXCEPTION 'Insufficient funds: balance is %, need %', v_balance, p_amount;
    END IF;

    -- Debit sender (balance trigger deducts if status=completed)
    INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
    VALUES (p_from_account, 'withdrawal', p_amount, p_description, NOW());

    -- Credit receiver (balance trigger adds if status=completed)
    -- For large amounts the intercept trigger sets both to status=pending
    INSERT INTO transactions(account_id, transaction_type, amount, description, transaction_date)
    VALUES (p_to_account, 'deposit', p_amount, p_description, NOW());
END;
$$;

-- Fix balance trigger to handle deposit/withdrawal correctly
CREATE OR REPLACE FUNCTION update_balance_after_txn()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' THEN
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Fix approval trigger - same logic for updates
CREATE OR REPLACE FUNCTION update_balance_after_txn_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'pending' AND NEW.status = 'completed' THEN
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;
