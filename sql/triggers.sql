-- triggers.sql

-- 1. Auto-lock after 5 failed logins
CREATE OR REPLACE FUNCTION check_login_attempts()
RETURNS TRIGGER AS $$
BEGIN
    IF (SELECT COUNT(*) FROM login_attempts
        WHERE user_id = NEW.user_id
          AND success = FALSE
          AND attempt_time > NOW() - INTERVAL '15 minutes') >= 5 THEN
        UPDATE users SET is_active = FALSE WHERE user_id = NEW.user_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_login_lockout
AFTER INSERT ON login_attempts
FOR EACH ROW EXECUTE FUNCTION check_login_attempts();

-- 2. Intercept large transactions to require approval
CREATE OR REPLACE FUNCTION intercept_large_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount >= 10000 THEN
        NEW.status := 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_intercept_large_txn
BEFORE INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION intercept_large_transaction();

-- 3. Update balance ONLY if transaction is completed (and set balance_after)
CREATE OR REPLACE FUNCTION update_balance_after_txn()
RETURNS TRIGGER AS $$
DECLARE
    v_new_balance DECIMAL(15,2);
BEGIN
    IF NEW.status = 'completed' THEN
        -- Calculate and update account balance
        IF NEW.transaction_type = 'deposit' THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id
            RETURNING balance INTO v_new_balance;
        ELSIF NEW.transaction_type IN ('withdrawal', 'transfer', 'payment', 'fee') THEN
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id
            RETURNING balance INTO v_new_balance;
        END IF;
        
        -- Store the snapshot in the transaction record
        NEW.balance_after := v_new_balance;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_balance
BEFORE INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION update_balance_after_txn();

-- 4. Update balance when a pending transaction is approved (and set balance_after)
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
        
        -- Update the transaction record with the new balance snapshot
        UPDATE transactions SET balance_after = v_new_balance WHERE transaction_id = NEW.transaction_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_balance_on_approve
AFTER UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION update_balance_after_txn_update();

-- 5. Auto-flag large transactions for compliance
CREATE OR REPLACE FUNCTION flag_large_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount >= 10000 THEN
        INSERT INTO fraud_alerts(transaction_id, account_id, alert_type, severity, status)
        VALUES (NEW.transaction_id, NEW.account_id, 'large_transaction', 'high', 'open');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_flag_large_txn
AFTER INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION flag_large_transaction();
