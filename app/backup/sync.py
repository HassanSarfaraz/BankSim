"""
BankSim Sync Module
====================
Cloud-first architecture:
- On startup: Pull from Firebase -> Postgres
- On every write: Push change to Firebase immediately
- Manual full sync buttons on admin dashboard still available
"""
from ..firebase import firestore
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
               'loans', 'deposit_requests', 'account_requests', 'fraud_alerts', 'support_tickets']

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
    'support_tickets': 'ticket_id',
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
    if firestore.db_firestore is None:
        return
    try:
        doc_data = {k: _serialize(v) for k, v in data.items()}
        firestore.db_firestore.collection(table).document(str(record_id)).set(doc_data, merge=True)
    except Exception as e:
        logger.warning(f"Firebase push failed for {table}/{record_id}: {e}")


def postgres_to_firebase():
    """Full backup: Postgres -> Firestore. Pushes ALL data."""
    if firestore.db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    sync_results = {}
    BATCH_SIZE = 400  # Firestore batch limit is 500

    for table in SYNC_TABLES:
        try:
            cur.execute(f"SELECT * FROM {table}")
            rows = cur.fetchall()
            col_ref = firestore.db_firestore.collection(table)
            
            # Batch upload
            for i in range(0, len(rows), BATCH_SIZE):
                batch = firestore.db_firestore.batch()
                chunk = rows[i:i + BATCH_SIZE]
                for row in chunk:
                    pk_col = TABLE_PKS[table]
                    doc_id = str(row[pk_col])
                    doc_data = {k: _serialize(v) for k, v in row.items()}
                    batch.set(col_ref.document(doc_id), doc_data, merge=True)
                batch.commit()
            
            sync_results[table] = len(rows)
        except Exception as e:
            logger.error(f"Error syncing {table}: {e}")

    return {"status": "success", "synced": sync_results}


def firebase_to_postgres():
    """Full restore: Firestore -> Postgres. Pulls ALL data."""
    if firestore.db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}

    conn = get_db_conn()
    cur = conn.cursor()

    restore_results = {}
    
    # Disable triggers temporarily
    cur.execute("SET session_replication_role = 'replica';")

    for table in SYNC_TABLES:
        try:
            docs = firestore.db_firestore.collection(table).stream()
            count = 0
            
            # Get DB columns for this table
            cur.execute("SELECT column_name FROM information_schema.columns WHERE table_name = %s", (table,))
            db_cols = [r[0] for r in cur.fetchall()]
            
            for doc in docs:
                data = doc.to_dict()
                row = _deserialize_row(data, db_cols)
                if not row: continue
                
                columns = list(row.keys())
                values = list(row.values())
                pk = TABLE_PKS[table]
                
                placeholders = ", ".join(["%s"] * len(values))
                update_set = ", ".join([f'"{col}" = EXCLUDED."{col}"' for col in columns if col != pk])
                
                query = f'INSERT INTO {table} ({", ".join([f"\"{c}\"" for c in columns])}) VALUES ({placeholders}) ON CONFLICT ("{pk}") DO UPDATE SET {update_set}'
                cur.execute(query, values)
                count += 1
            
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


# ─── PER-USER SYNC (used on login / logout) ───────────────────────────────────

# Tables whose rows are owned by / related to a single user_id.
# Each entry: (table_name, pk_col, user_filter_sql)
# The filter must produce a WHERE clause fragment that accepts (user_id,) as param.
_USER_TABLES = [
    # (table,               pk,               join/where to reach user_id)
    ('users',           'user_id',   'WHERE user_id = %s'),
    ('customers',       'customer_id', 'WHERE user_id = %s'),
    # accounts & transactions are reached via customer_id → user_id
    ('accounts',        'account_id',
     'WHERE customer_id IN (SELECT customer_id FROM customers WHERE user_id = %s)'),
    ('transactions_2026', 'transaction_id',
     'WHERE account_id IN (SELECT a.account_id FROM accounts a JOIN customers c ON a.customer_id=c.customer_id WHERE c.user_id=%s)'),
    ('transactions_2025', 'transaction_id',
     'WHERE account_id IN (SELECT a.account_id FROM accounts a JOIN customers c ON a.customer_id=c.customer_id WHERE c.user_id=%s)'),
    ('deposit_requests', 'request_id',
     'WHERE account_id IN (SELECT a.account_id FROM accounts a JOIN customers c ON a.customer_id=c.customer_id WHERE c.user_id=%s)'),
    ('loans',           'loan_id',
     'WHERE customer_id IN (SELECT customer_id FROM customers WHERE user_id=%s)'),
    ('support_tickets', 'ticket_id', 'WHERE user_id = %s'),
]


def firebase_to_postgres_for_user(user_id):
    """
    PULL: Firebase → Postgres for one user (called on login).
    Only inserts records that are genuinely missing from local DB.
    Local state is always authoritative — we never overwrite existing rows.
    Returns {'added': N} where N is the number of new rows inserted.
    """
    if firestore.db_firestore is None:
        return {"added": 0, "message": "Firebase not initialized"}

    conn = get_db_conn()
    cur = conn.cursor()
    # Check if admin (role_id=3)
    cur.execute("SELECT role_id FROM users WHERE user_id = %s", (user_id,))
    res = cur.fetchone()
    if res and res[0] == 3:
        return {"added": 0, "message": "Admin user: sync skipped"}

    cur.execute("SET session_replication_role = 'replica';")

    total_added = 0

    for table, pk, _where_sql in _USER_TABLES:
        try:
            # ── Collect ALL existing PKs in the full table ────────────────────────
            # CRITICAL: do NOT filter by user ownership here.
            # Admin users have no customer record, so a user-filtered query returns
            # empty set — making every Firebase doc look "missing" and causing
            # stale 'pending' records to be re-inserted on every admin login.
            cur.execute(f'SELECT "{pk}" FROM {table}')
            local_pks = {str(r[0]) for r in cur.fetchall()}

            # Get DB column list
            cur.execute(
                "SELECT column_name FROM information_schema.columns WHERE table_name = %s",
                (table,)
            )
            db_cols = [r[0] for r in cur.fetchall()]

            # Stream Firebase — skip anything that already exists locally
            docs = firestore.db_firestore.collection(table).stream()
            for doc in docs:
                if doc.id in local_pks:
                    continue  # Already in local DB — local state wins, never overwrite

                data = doc.to_dict()
                row = _deserialize_row(data, db_cols)
                if not row:
                    continue

                columns = list(row.keys())
                values = list(row.values())
                placeholders = ", ".join(["%s"] * len(values))
                query = (
                    f'INSERT INTO {table} ({", ".join([f"{chr(34)}{c}{chr(34)}" for c in columns])})'
                    f' VALUES ({placeholders})'
                    f' ON CONFLICT ("{pk}") DO NOTHING'
                )
                try:
                    cur.execute(query, values)
                    total_added += 1
                except Exception as row_err:
                    conn.rollback()
                    logger.warning(f"Skipping Firebase row {table}/{doc.id}: {row_err}")
                    cur.execute("SET session_replication_role = 'replica';")

        except Exception as e:
            logger.error(f"firebase_to_postgres_for_user error on {table}: {e}")

    cur.execute("SET session_replication_role = 'origin';")
    conn.commit()
    return {"added": total_added}


def postgres_to_firebase_for_user(user_id):
    """
    PUSH: Postgres → Firebase for one user (called on logout).
    Uploads all rows belonging to this user to Firestore.
    """
    if firestore.db_firestore is None:
        return {"status": "error", "message": "Firebase not initialized"}

    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)

    BATCH_SIZE = 400
    sync_results = {}

    for table, pk, where_sql in _USER_TABLES:
        try:
            cur.execute(f"SELECT * FROM {table} {where_sql}", (user_id,))
            rows = cur.fetchall()
            col_ref = firestore.db_firestore.collection(table)

            for i in range(0, len(rows), BATCH_SIZE):
                batch = firestore.db_firestore.batch()
                for row in rows[i:i + BATCH_SIZE]:
                    doc_id = str(row[pk])
                    doc_data = {k: _serialize(v) for k, v in row.items()}
                    batch.set(col_ref.document(doc_id), doc_data, merge=True)
                batch.commit()

            sync_results[table] = len(rows)
        except Exception as e:
            logger.error(f"postgres_to_firebase_for_user error on {table}: {e}")
            sync_results[table] = f"error: {e}"

    return {"status": "success", "synced": sync_results}
