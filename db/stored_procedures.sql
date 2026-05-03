-- ===========================================================================
-- SecureBank - Stored Procedure: sp_transfer
-- Atomic fund transfer with row-level locking (SELECT FOR UPDATE).
-- Demonstrates CS232: Transactions, Concurrency Control, ACID.
-- ===========================================================================

DROP PROCEDURE IF EXISTS sp_transfer;

CREATE OR REPLACE PROCEDURE sp_transfer(
    IN  p_from_account  INTEGER,
    IN  p_to_account    INTEGER,
    IN  p_amount        DECIMAL(15,2),
    IN  p_performed_by  INTEGER,
    IN  p_description   TEXT,
    OUT p_success       BOOLEAN,
    OUT p_message       TEXT,
    OUT p_txn_id        INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_from_balance  DECIMAL(15,2);
    v_daily_limit   DECIMAL(15,2);
    v_daily_spent   DECIMAL(15,2);
    v_from_status   VARCHAR(20);
    v_to_status     VARCHAR(20);
BEGIN
    -- -----------------------------------------------------------------------
    -- 1. Acquire row-level exclusive locks in a deterministic order
    --    (lower ID first) to prevent deadlocks.
    -- -----------------------------------------------------------------------
    IF p_from_account < p_to_account THEN
        SELECT balance, daily_limit, status
          INTO v_from_balance, v_daily_limit, v_from_status
          FROM accounts WHERE account_id = p_from_account FOR UPDATE;

        SELECT status INTO v_to_status
          FROM accounts WHERE account_id = p_to_account FOR UPDATE;
    ELSE
        SELECT status INTO v_to_status
          FROM accounts WHERE account_id = p_to_account FOR UPDATE;

        SELECT balance, daily_limit, status
          INTO v_from_balance, v_daily_limit, v_from_status
          FROM accounts WHERE account_id = p_from_account FOR UPDATE;
    END IF;

    -- -----------------------------------------------------------------------
    -- 2. Business rule validations
    -- -----------------------------------------------------------------------
    IF v_from_status != 'active' THEN
        p_success := FALSE;
        p_message := 'Source account is not active';
        RETURN;
    END IF;

    IF v_to_status != 'active' THEN
        p_success := FALSE;
        p_message := 'Destination account is not active';
        RETURN;
    END IF;

    IF v_from_balance < p_amount THEN
        p_success := FALSE;
        p_message := 'Insufficient funds';
        RETURN;
    END IF;

    -- Check daily limit
    SELECT COALESCE(SUM(amount), 0) INTO v_daily_spent
      FROM transactions
     WHERE from_account = p_from_account
       AND DATE(timestamp) = CURRENT_DATE
       AND status = 'completed';

    IF (v_daily_spent + p_amount) > v_daily_limit THEN
        p_success := FALSE;
        p_message := FORMAT('Daily limit of PKR %s exceeded. Already spent: PKR %s',
                            v_daily_limit::TEXT, v_daily_spent::TEXT);
        RETURN;
    END IF;

    -- -----------------------------------------------------------------------
    -- 3. Execute the atomic debit/credit
    -- -----------------------------------------------------------------------
    UPDATE accounts SET balance = balance - p_amount WHERE account_id = p_from_account;
    UPDATE accounts SET balance = balance + p_amount WHERE account_id = p_to_account;

    -- -----------------------------------------------------------------------
    -- 4. Record the immutable transaction log
    -- -----------------------------------------------------------------------
    INSERT INTO transactions (from_account, to_account, amount, txn_type, status, description, performed_by)
    VALUES (p_from_account, p_to_account, p_amount, 'transfer', 'completed',
            COALESCE(p_description, 'Fund transfer'), p_performed_by)
    RETURNING txn_id INTO p_txn_id;

    p_success := TRUE;
    p_message := 'Transfer completed successfully';

EXCEPTION
    WHEN OTHERS THEN
        p_success := FALSE;
        p_message := 'Internal error: ' || SQLERRM;
        p_txn_id  := NULL;
END;
$$;


-- ===========================================================================
-- Stored Procedure: sp_deposit
-- ===========================================================================
DROP PROCEDURE IF EXISTS sp_deposit;

CREATE OR REPLACE PROCEDURE sp_deposit(
    IN  p_account_id    INTEGER,
    IN  p_amount        DECIMAL(15,2),
    IN  p_performed_by  INTEGER,
    IN  p_description   TEXT,
    OUT p_success       BOOLEAN,
    OUT p_message       TEXT,
    OUT p_txn_id        INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_status VARCHAR(20);
BEGIN
    SELECT status INTO v_status FROM accounts WHERE account_id = p_account_id FOR UPDATE;

    IF v_status IS NULL THEN
        p_success := FALSE; p_message := 'Account not found'; RETURN;
    END IF;

    IF v_status != 'active' THEN
        p_success := FALSE; p_message := 'Account is not active'; RETURN;
    END IF;

    UPDATE accounts SET balance = balance + p_amount WHERE account_id = p_account_id;

    INSERT INTO transactions (to_account, amount, txn_type, status, description, performed_by)
    VALUES (p_account_id, p_amount, 'deposit', 'completed',
            COALESCE(p_description, 'Cash deposit'), p_performed_by)
    RETURNING txn_id INTO p_txn_id;

    p_success := TRUE;
    p_message := 'Deposit successful';
EXCEPTION
    WHEN OTHERS THEN
        p_success := FALSE; p_message := SQLERRM; p_txn_id := NULL;
END;
$$;


-- ===========================================================================
-- Stored Procedure: sp_withdrawal
-- ===========================================================================
DROP PROCEDURE IF EXISTS sp_withdrawal;

CREATE OR REPLACE PROCEDURE sp_withdrawal(
    IN  p_account_id    INTEGER,
    IN  p_amount        DECIMAL(15,2),
    IN  p_performed_by  INTEGER,
    IN  p_description   TEXT,
    OUT p_success       BOOLEAN,
    OUT p_message       TEXT,
    OUT p_txn_id        INTEGER
)
LANGUAGE plpgsql
AS $$
DECLARE
    v_balance    DECIMAL(15,2);
    v_daily_limit DECIMAL(15,2);
    v_daily_spent DECIMAL(15,2);
    v_status     VARCHAR(20);
BEGIN
    SELECT balance, daily_limit, status
      INTO v_balance, v_daily_limit, v_status
      FROM accounts WHERE account_id = p_account_id FOR UPDATE;

    IF v_status != 'active' THEN
        p_success := FALSE; p_message := 'Account is not active'; RETURN;
    END IF;

    IF v_balance < p_amount THEN
        p_success := FALSE; p_message := 'Insufficient funds'; RETURN;
    END IF;

    SELECT COALESCE(SUM(amount), 0) INTO v_daily_spent
      FROM transactions
     WHERE from_account = p_account_id AND DATE(timestamp) = CURRENT_DATE AND status = 'completed';

    IF (v_daily_spent + p_amount) > v_daily_limit THEN
        p_success := FALSE;
        p_message := 'Daily withdrawal limit exceeded';
        RETURN;
    END IF;

    UPDATE accounts SET balance = balance - p_amount WHERE account_id = p_account_id;

    INSERT INTO transactions (from_account, amount, txn_type, status, description, performed_by)
    VALUES (p_account_id, p_amount, 'withdrawal', 'completed',
            COALESCE(p_description, 'Cash withdrawal'), p_performed_by)
    RETURNING txn_id INTO p_txn_id;

    p_success := TRUE;
    p_message := 'Withdrawal successful';
EXCEPTION
    WHEN OTHERS THEN
        p_success := FALSE; p_message := SQLERRM; p_txn_id := NULL;
END;
$$;
