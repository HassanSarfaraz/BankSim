-- ===========================================================================
-- SecureBank — Triggers for Data Integrity
-- ===========================================================================

-- Prevent negative balance (defence-in-depth on top of CHECK constraint)
CREATE OR REPLACE FUNCTION fn_check_balance()
RETURNS TRIGGER AS $$
BEGIN
    IF NEW.balance < 0 THEN
        RAISE EXCEPTION 'Account % balance cannot go negative (attempted: %)',
                        NEW.account_id, NEW.balance;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_check_balance ON accounts;
CREATE TRIGGER trg_check_balance
    BEFORE UPDATE OF balance ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION fn_check_balance();


-- Log status changes on accounts (frozen/active/closed)
CREATE OR REPLACE FUNCTION fn_log_account_status()
RETURNS TRIGGER AS $$
BEGIN
    IF OLD.status IS DISTINCT FROM NEW.status THEN
        RAISE NOTICE 'Account % status changed: % → %',
                     NEW.account_id, OLD.status, NEW.status;
    END IF;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trg_account_status ON accounts;
CREATE TRIGGER trg_account_status
    AFTER UPDATE OF status ON accounts
    FOR EACH ROW
    EXECUTE FUNCTION fn_log_account_status();
