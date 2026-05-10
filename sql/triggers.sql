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
    IF NEW.amount >= 10000 AND NEW.description != 'Admin-Approved Cash Deposit' THEN
        NEW.status := 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_intercept_large_txn
BEFORE INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION intercept_large_transaction();

-- 3. Unified Balance Management (Updates balance and captures snapshot)
CREATE OR REPLACE FUNCTION handle_transaction_balance()
RETURNS TRIGGER AS $$
DECLARE
    v_new_balance DECIMAL(15,2);
BEGIN
    -- Recursion protection
    IF (pg_trigger_depth() > 1) THEN
        RETURN NEW;
    END IF;

    -- Process if status is 'completed'
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

CREATE TRIGGER trg_balance_management
AFTER INSERT OR UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION handle_transaction_balance();

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
