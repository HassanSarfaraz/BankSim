CREATE OR REPLACE FUNCTION intercept_large_transaction()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.amount >= 10000 THEN
        NEW.status := 'pending';
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_intercept_large_txn ON transactions;
CREATE TRIGGER trg_intercept_large_txn
BEFORE INSERT ON transactions
FOR EACH ROW EXECUTE FUNCTION intercept_large_transaction();

CREATE OR REPLACE FUNCTION update_balance_after_txn()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.status = 'completed' THEN
        IF NEW.transaction_type IN ('deposit','transfer_in') THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id;
        ELSE
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE OR REPLACE FUNCTION update_balance_after_txn_update()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status = 'pending' AND NEW.status = 'completed' THEN
        IF NEW.transaction_type IN ('deposit','transfer_in') THEN
            UPDATE accounts SET balance = balance + NEW.amount
            WHERE account_id = NEW.account_id;
        ELSE
            UPDATE accounts SET balance = balance - NEW.amount
            WHERE account_id = NEW.account_id;
        END IF;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_update_balance_on_approve ON transactions;
CREATE TRIGGER trg_update_balance_on_approve
AFTER UPDATE ON transactions
FOR EACH ROW EXECUTE FUNCTION update_balance_after_txn_update();

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
