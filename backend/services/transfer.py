"""
Transfer and banking operation services.
All DB operations call PostgreSQL stored procedures via psycopg2 raw connection
to guarantee stored-procedure-level atomicity and row-level locking.
"""
import os
from sqlalchemy import text
from backend.extensions import db
from backend.mongo.audit import log_audit_event


def _call_proc(proc_sql: str, params: dict):
    """Execute a stored procedure and return (success, message, extra_id)."""
    with db.engine.connect() as conn:
        with conn.begin():
            result = conn.execute(text(proc_sql), params)
            row = result.fetchone()
            return row


def transfer_funds(from_acc: int, to_acc: int, amount: float,
                   performed_by: int, description: str = "Fund transfer"):
    """
    Atomic transfer via sp_transfer stored procedure.
    Returns (success: bool, message: str, txn_id: int | None)
    """
    try:
        sql = text("""
            DO $$
            DECLARE
                v_success BOOLEAN;
                v_message TEXT;
                v_txn_id  INTEGER;
            BEGIN
                CALL sp_transfer(:from_acc, :to_acc, :amount, :performed_by, :desc,
                                 v_success, v_message, v_txn_id);
                IF NOT v_success THEN
                    RAISE EXCEPTION '%', v_message;
                END IF;
            END $$;
        """)
        with db.engine.connect() as conn:
            with conn.begin():
                conn.execute(sql, {
                    "from_acc": from_acc, "to_acc": to_acc,
                    "amount": amount, "performed_by": performed_by,
                    "desc": description
                })

        log_audit_event(performed_by, 'TRANSFER',
                        f"Transferred PKR {amount} from acc#{from_acc} to acc#{to_acc}")
        return True, "Transfer successful", None

    except Exception as e:
        err = str(e)
        # Extract the custom message from PostgreSQL RAISE EXCEPTION
        if 'ERROR:' in err:
            err = err.split('ERROR:')[-1].strip().split('\n')[0]
        return False, err, None


def cash_deposit(account_id: int, amount: float, performed_by: int, description: str = "Cash deposit"):
    try:
        sql = text("""
            DO $$
            DECLARE v_success BOOLEAN; v_message TEXT; v_txn_id INTEGER;
            BEGIN
                CALL sp_deposit(:acc, :amount, :by, :desc, v_success, v_message, v_txn_id);
                IF NOT v_success THEN RAISE EXCEPTION '%', v_message; END IF;
            END $$;
        """)
        with db.engine.connect() as conn:
            with conn.begin():
                conn.execute(sql, {"acc": account_id, "amount": amount,
                                   "by": performed_by, "desc": description})
        log_audit_event(performed_by, 'DEPOSIT', f"Deposited PKR {amount} to acc#{account_id}")
        return True, "Deposit successful"
    except Exception as e:
        err = str(e)
        if 'ERROR:' in err:
            err = err.split('ERROR:')[-1].strip().split('\n')[0]
        return False, err


def cash_withdrawal(account_id: int, amount: float, performed_by: int, description: str = "Cash withdrawal"):
    try:
        sql = text("""
            DO $$
            DECLARE v_success BOOLEAN; v_message TEXT; v_txn_id INTEGER;
            BEGIN
                CALL sp_withdrawal(:acc, :amount, :by, :desc, v_success, v_message, v_txn_id);
                IF NOT v_success THEN RAISE EXCEPTION '%', v_message; END IF;
            END $$;
        """)
        with db.engine.connect() as conn:
            with conn.begin():
                conn.execute(sql, {"acc": account_id, "amount": amount,
                                   "by": performed_by, "desc": description})
        log_audit_event(performed_by, 'WITHDRAWAL', f"Withdrew PKR {amount} from acc#{account_id}")
        return True, "Withdrawal successful"
    except Exception as e:
        err = str(e)
        if 'ERROR:' in err:
            err = err.split('ERROR:')[-1].strip().split('\n')[0]
        return False, err
