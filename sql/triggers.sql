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

-- 2. Update balance after every transaction
CREATE OR REPLACE FUNCTION update_balance_after_txn()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.transaction_type IN ('deposit','transfer_in') THEN
        UPDATE accounts SET balance = balance + NEW.amount
        WHERE account_id = NEW.account_id;
    ELSE
        UPDATE accounts SET balance = balance - NEW.amount
        WHERE account_id = NEW.account_id;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_balance
AFTER INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION update_balance_after_txn();

-- 3. Auto-flag large transactions for compliance
CREATE OR REPLACE FUNCTION flag_large_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount > 10000 THEN
        INSERT INTO fraud_alerts(transaction_id, account_id, alert_type, severity)
        VALUES (NEW.transaction_id, NEW.account_id, 'large_transaction', 'medium');
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_flag_large_txn
AFTER INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION flag_large_transaction();
