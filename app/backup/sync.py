"""
BankSim Sync Module
====================
Cloud-first architecture:
- On startup: Pull from Firebase -> Postgres
- On every write: Push change to Firebase immediately
- Manual full sync buttons on admin dashboard still available
"""
from ..firebase.firestore import db_firestore
from ..models.db import get_db_conn
import psycopg2.extras
from datetime import datetime, date
from decimal import Decimal
import logging

logger = logging.getLogger(__name__)

# Tables synced to Firebase (in FK dependency order for restore)
# IMPORTANT: transactions is PARTITIONED — sync the child tables directly, NOT the parent.
# Syncing the parent would cause every row to appear in all children on restore.
SYNC_TABLES = ['users', 'customers', 'accounts', 'transactions_2025', 'transactions_2026',
               'loans', 'deposit_requests', 'account_requests', 'fraud_alerts']

# Primary key for each table
TABLE_PKS = {
    'users': 'user_id',
    'customers': 'customer_id',
    'accounts': 'account_id',
    'transactions': 'transaction_id',
    'transactions_2025': 'transaction_id',
    'transactions_2026': 'transaction_id',
    'loans': 'loan_id',
    'deposit_requests': 'request_id',
    'account_requests': 'request_id',
    'fraud_alerts': 'alert_id',
}

# Columns that MUST not be null/overwritten blindly from Firebase
REQUIRED_COLUMNS = {
    'transactions': ['account_id', 'transaction_type', 'amount'],
    'accounts': ['account_number', 'customer_id'],
    'users': ['username', 'email', 'password_hash'],
}


def _serialize(v):
    """Convert Python types to Firebase-safe strings."""
    if v is None:
        return None
    if isinstance(v, (datetime, date)):
        return v.isoformat()
    if isinstance(v, Decimal):
        return str(v)
    if isinstance(v, bool):
        return v  # keep booleans as-is
    if isinstance(v, (int, float)):
        return v  # keep numbers as-is
    return str(v)


def _deserialize_row(data, db_cols):
    """Convert Firebase string data back to appropriate Python types for Postgres."""
    result = {}
    for k, v in data.items():
        if k not in db_cols:
            continue
        if v == 'None' or v == '':
            result[k] = None
        else:
            result[k] = v
    return result


def push_record(table, record_id, data):
    """Push a single record change to Firebase immediately after any DB write."""
    if db_firestore is None:
        return
    try:
        doc_data = {k: _serialize(v) for k, v in data.items()}
        db_firestore.collection(table).document(str(record_id)).set(doc_data, merge=True)
    except Exception as e:
        logger.warning(f"Firebase push failed for {table}/{record_id}: {e}")


def postgres_to_firebase():
    """Full backup: Postgres -> Firestore. Pushes ALL data."""
    if db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    sync_results = {}
    BATCH_SIZE = 400  # Firestore batch limit is 500

    for table in SYNC_TABLES:
        try:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            col_ref = db_firestore.collection(table)
            count = 0
            batch = db_firestore.batch()
            batch_count = 0

            for row in rows:
                pk_col = TABLE_PKS.get(table, list(row.keys())[0])
                doc_data = {k: _serialize(v) for k, v in row.items()}
                doc_ref = col_ref.document(str(row[pk_col]))
                batch.set(doc_ref, doc_data)
                count += 1
                batch_count += 1

                if batch_count >= BATCH_SIZE:
                    batch.commit()
                    batch = db_firestore.batch()
                    batch_count = 0

            if batch_count > 0:
                batch.commit()

            sync_results[table] = count
        except Exception as e:
            logger.error(f"Error syncing {table} to Firebase: {e}")
            sync_results[table] = f"error: {e}"

    return {"status": "success", "synced": sync_results}


def firebase_to_postgres():
    """Full restore: Firestore -> Postgres. Cloud is source of truth.
    Uses UPSERT logic. Skips rows with null required columns.
    Disables triggers during restore to avoid double-balance-updates."""
    if db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}

    conn = get_db_conn()
    cur = conn.cursor()

    # Disable triggers to prevent double balance calculation during restore
    cur.execute("SET session_replication_role = 'replica';")
    conn.commit()

    restore_results = {}

    for table in SYNC_TABLES:
        try:
            # Get actual columns that exist in the local DB
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s AND table_schema = 'public'",
                (table,)
            )
            db_cols = {row[0] for row in cur.fetchall()}
            if not db_cols:
                restore_results[table] = "skipped (table not found locally)"
                continue

            pk_col = TABLE_PKS.get(table)
            required = REQUIRED_COLUMNS.get(table, [])

            docs = db_firestore.collection(table).stream()
            count = 0

            for doc in docs:
                data = doc.to_dict()
                if not data:
                    continue

                # Filter to columns that exist in local DB
                row = _deserialize_row(data, db_cols)

                if not row or pk_col not in row or row.get(pk_col) is None:
                    continue

                # Skip rows where required columns are None (corrupted Firebase data)
                skip = False
                for req_col in required:
                    if req_col in db_cols and (req_col not in row or row.get(req_col) is None):
                        skip = True
                        break
                if skip:
                    continue

                columns = list(row.keys())

                # Check if record already exists
                cur.execute(f'SELECT 1 FROM {table} WHERE "{pk_col}" = %s', (row[pk_col],))
                exists = cur.fetchone()

                try:
                    if exists:
                        set_parts = [f'"{col}" = %({col})s' for col in columns if col != pk_col]
                        if set_parts:
                            sql = f'UPDATE {table} SET {", ".join(set_parts)} WHERE "{pk_col}" = %({pk_col})s'
                            cur.execute(sql, row)
                    else:
                        cols_str = ', '.join([f'"{c}"' for c in columns])
                        vals_str = ', '.join([f'%({c})s' for c in columns])
                        sql = f'INSERT INTO {table} ({cols_str}) VALUES ({vals_str})'
                        cur.execute(sql, row)
                    count += 1
                except Exception as row_err:
                    conn.rollback()
                    logger.warning(f"Skipping row in {table}: {row_err}")
                    cur.execute("SET session_replication_role = 'replica';")
                    continue

            conn.commit()
            restore_results[table] = count

        except Exception as e:
            conn.rollback()
            logger.error(f"Error restoring {table}: {e}")
            restore_results[table] = f"error: {e}"
            cur.execute("SET session_replication_role = 'replica';")

    # Re-enable triggers
    cur.execute("SET session_replication_role = 'origin';")
    conn.commit()

    return {"status": "success", "restored": restore_results}
