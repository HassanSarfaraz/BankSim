from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from ..models.db import get_db_conn
from ..backup.sync import postgres_to_firebase, firebase_to_postgres, push_record

admin_bp = Blueprint('admin', __name__)


def _require_admin():
    return 'user_id' not in session or session.get('role_id') != 3


@admin_bp.route('/dashboard')
def dashboard():
    if _require_admin():
        return redirect(url_for('auth.login'))

    conn = get_db_conn()
    cur = conn.cursor()

    # ── Fraud Alerts (large/suspicious transactions awaiting approval) ──────────
    # Only show alerts for transactions that are PENDING (need approval)
    cur.execute("""
        SELECT fa.alert_id, fa.alert_type, fa.severity, fa.created_at,
               a.account_number, t.description, t.amount, c.user_id, t.transaction_id, t.status
        FROM fraud_alerts fa
        JOIN accounts a ON fa.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        LEFT JOIN transactions t ON fa.transaction_id = t.transaction_id
        WHERE fa.status = 'open'
        ORDER BY fa.created_at DESC
    """)
    alerts = cur.fetchall()

    # ── System-Wide Accounts ────────────────────────────────────────────────────
    cur.execute("""
        SELECT c.customer_id, c.first_name || ' ' || c.last_name,
               a.account_number, a.account_type, a.balance, a.status, u.is_active, u.user_id
        FROM users u
        JOIN customers c ON u.user_id = c.user_id
        JOIN accounts a ON c.customer_id = a.customer_id
        ORDER BY c.customer_id
        LIMIT 100
    """)
    active_accounts = cur.fetchall()

    # ── Global Transactions (only completed ones in main table) ─────────────────
    txn_limit = request.args.get('txn_limit', 50, type=int)
    limit_clause = f"LIMIT {txn_limit}" if txn_limit > 0 else ""
    cur.execute(f"""
        SELECT t.transaction_id, t.transaction_type, t.amount, t.transaction_date,
               t.description, a.account_number, t.status
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        WHERE t.status = 'completed'
        ORDER BY t.transaction_date DESC
        {limit_clause}
    """)
    global_transactions = cur.fetchall()

    # ── Pending Deposit Requests ────────────────────────────────────────────────
    cur.execute("""
        SELECT dr.request_id, a.account_number, dr.amount, dr.created_at,
               c.first_name || ' ' || c.last_name
        FROM deposit_requests dr
        JOIN accounts a ON dr.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE dr.status = 'pending'
        ORDER BY dr.created_at DESC
    """)
    deposit_requests = cur.fetchall()

    # ── Pending Account Requests ────────────────────────────────────────────────
    cur.execute("""
        SELECT request_id, username, email, first_name, last_name, created_at
        FROM account_requests
        WHERE status = 'pending'
        ORDER BY created_at DESC
    """)
    account_requests = cur.fetchall()

    return render_template(
        'dashboard/admin.html',
        alerts=alerts,
        active_accounts=active_accounts,
        global_transactions=global_transactions,
        deposit_requests=deposit_requests,
        account_requests=account_requests,
        txn_limit=txn_limit
    )


@admin_bp.route('/toggle_lock/<int:user_id>', methods=['POST'])
def toggle_lock(user_id):
    if _require_admin():
        return redirect(url_for('auth.login'))
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=None)
    try:
        cur.execute(
            "UPDATE users SET is_active = NOT is_active WHERE user_id = %s RETURNING is_active, username, email, role_id, created_at",
            (user_id,)
        )
        row = cur.fetchone()
        new_status = row[0]
        conn.commit()
        # Push change to Firebase
        push_record('users', user_id, {
            'user_id': user_id, 'is_active': new_status,
            'username': row[1], 'email': row[2], 'role_id': row[3]
        })
        flash(f"Account {'unlocked' if new_status else 'locked'}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/handle_fraud/<int:alert_id>/<action>', methods=['POST'])
def handle_fraud(alert_id, action):
    if _require_admin():
        return redirect(url_for('auth.login'))
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT transaction_id, account_id FROM fraud_alerts WHERE alert_id = %s", (alert_id,))
        res = cur.fetchone()
        if not res or not res[0]:
            flash("Alert or transaction not found.", "danger")
            return redirect(url_for('admin.dashboard'))

        txn_id, account_id = res

        # Get the transaction details
        cur.execute("SELECT transaction_type, amount, description FROM transactions WHERE transaction_id = %s", (txn_id,))
        txn = cur.fetchone()
        if not txn:
            flash("Linked transaction not found.", "danger")
            return redirect(url_for('admin.dashboard'))

        txn_type, txn_amount, txn_desc = txn

        new_txn_status = 'completed' if action == 'approve' else 'failed'
        new_alert_status = 'resolved' if action == 'approve' else 'rejected'

        # Update this transaction
        cur.execute("UPDATE transactions SET status = %s WHERE transaction_id = %s", (new_txn_status, txn_id))
        cur.execute("UPDATE fraud_alerts SET status = %s WHERE alert_id = %s", (new_alert_status, alert_id))

        # Find and resolve the paired transaction (the other half of a transfer with same desc+amount)
        # This prevents the paired fraud alert from remaining open as a duplicate
        if txn_type == 'withdrawal':
            paired_type = 'deposit'
        elif txn_type == 'deposit':
            paired_type = 'withdrawal'
        else:
            paired_type = None

        if paired_type:
            cur.execute("""
                SELECT t.transaction_id FROM transactions t
                JOIN fraud_alerts fa ON fa.transaction_id = t.transaction_id
                WHERE t.transaction_type = %s
                  AND t.amount = %s
                  AND t.description = %s
                  AND t.status = 'pending'
                  AND fa.status = 'open'
                  AND t.transaction_id != %s
                LIMIT 1
            """, (paired_type, txn_amount, txn_desc, txn_id))
            paired = cur.fetchone()
            if paired:
                paired_txn_id = paired[0]
                cur.execute("UPDATE transactions SET status = %s WHERE transaction_id = %s", (new_txn_status, paired_txn_id))
                cur.execute("UPDATE fraud_alerts SET status = %s WHERE transaction_id = %s AND status = 'open'", (new_alert_status, paired_txn_id))

        conn.commit()
        push_record('fraud_alerts', alert_id, {'alert_id': str(alert_id), 'status': new_alert_status})

        if action == 'approve':
            flash("Transaction approved — balance updated for both sender and receiver.", "success")
        else:
            flash("Transaction rejected and blocked for both parties.", "info")

    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/undo_transaction/<int:transaction_id>', methods=['POST'])
def undo_transaction(transaction_id):
    if _require_admin():
        return redirect(url_for('auth.login'))
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "SELECT account_id, transaction_type, amount FROM transactions WHERE transaction_id = %s AND status = 'completed'",
            (transaction_id,)
        )
        txn = cur.fetchone()
        if txn:
            acc_id, txn_type, amount = txn
            if txn_type in ('withdrawal', 'fee', 'transfer', 'payment'):
                cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (amount, acc_id))
            elif txn_type == 'deposit':
                cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, acc_id))
            cur.execute("DELETE FROM transactions WHERE transaction_id = %s", (transaction_id,))
            conn.commit()
            # Reflect in Firebase
            push_record('accounts', acc_id, {'account_id': acc_id})
            flash("Transaction undone and balance adjusted.", "success")
        else:
            flash("Transaction not found or already pending/failed.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/handle_deposit/<int:request_id>/<action>', methods=['POST'])
def handle_deposit(request_id, action):
    if _require_admin():
        return redirect(url_for('auth.login'))
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        if action == 'accept':
            cur.execute(
                "SELECT account_id, amount FROM deposit_requests WHERE request_id = %s AND status = 'pending'",
                (request_id,)
            )
            req = cur.fetchone()
            if req:
                acc_id, amount = req
                # Insert completed transaction — trigger updates balance automatically.
                # Do NOT add a separate UPDATE accounts here — that would double the balance.
                cur.execute(
                    "INSERT INTO transactions (account_id, transaction_type, amount, description, status) "
                    "VALUES (%s, 'deposit', %s, 'Admin-Approved Cash Deposit', 'completed')",
                    (acc_id, amount)
                )
                cur.execute("UPDATE deposit_requests SET status = 'accepted' WHERE request_id = %s", (request_id,))
                conn.commit()
                push_record('deposit_requests', request_id, {'request_id': request_id, 'status': 'accepted'})
                flash("Deposit approved and processed.", "success")
        elif action == 'reject':
            cur.execute("UPDATE deposit_requests SET status = 'rejected' WHERE request_id = %s", (request_id,))
            conn.commit()
            push_record('deposit_requests', request_id, {'request_id': request_id, 'status': 'rejected'})
            flash("Deposit request rejected.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/handle_account_request/<int:request_id>/<action>', methods=['POST'])
def handle_account_request(request_id, action):
    if _require_admin():
        return redirect(url_for('auth.login'))
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        if action == 'accept':
            cur.execute(
                "SELECT username, email, password_hash, first_name, last_name FROM account_requests "
                "WHERE request_id = %s AND status = 'pending'",
                (request_id,)
            )
            req = cur.fetchone()
            if req:
                username, email, password_hash, first_name, last_name = req
                cur.execute(
                    "INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, 1) RETURNING user_id",
                    (username, email, password_hash)
                )
                user_id = cur.fetchone()[0]
                cur.execute(
                    "INSERT INTO customers (user_id, first_name, last_name) VALUES (%s, %s, %s) RETURNING customer_id",
                    (user_id, first_name, last_name)
                )
                customer_id = cur.fetchone()[0]
                import random
                acc_num = f"PK-BANK-{random.randint(10000, 99999)}"
                cur.execute(
                    "INSERT INTO accounts (account_number, customer_id, account_type) VALUES (%s, %s, 'checking')",
                    (acc_num, customer_id)
                )
                cur.execute("UPDATE account_requests SET status = 'accepted' WHERE request_id = %s", (request_id,))
                conn.commit()
                push_record('users', user_id, {'user_id': user_id, 'username': username, 'email': email, 'role_id': 1})
                push_record('account_requests', request_id, {'request_id': request_id, 'status': 'accepted'})
                flash("Account approved. User can now log in.", "success")
        elif action == 'reject':
            cur.execute("UPDATE account_requests SET status = 'rejected' WHERE request_id = %s", (request_id,))
            conn.commit()
            push_record('account_requests', request_id, {'request_id': request_id, 'status': 'rejected'})
            flash("Account request rejected.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))


@admin_bp.route('/backup/push', methods=['POST'])
def backup_push():
    if _require_admin():
        return redirect(url_for('auth.login'))
    result = postgres_to_firebase()
    return jsonify(result)


@admin_bp.route('/backup/pull', methods=['POST'])
def backup_pull():
    if _require_admin():
        return redirect(url_for('auth.login'))
    result = firebase_to_postgres()
    return jsonify(result)


@admin_bp.route('/post-interest', methods=['POST'])
def post_interest():
    if _require_admin():
        return redirect(url_for('auth.login'))
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("CALL post_monthly_interest()")
        conn.commit()
        flash("Monthly interest posted to all savings accounts.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))
