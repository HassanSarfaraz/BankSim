from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from werkzeug.security import generate_password_hash
from ..models.db import get_db_conn
from ..backup.sync import postgres_to_firebase, firebase_to_postgres

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role_id') != 3:
        return redirect(url_for('auth.login'))
        
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Use View: Open Fraud Alerts (updated schema with recipient info and user_id)
    cur.execute("SELECT * FROM open_fraud_alerts_view")
    alerts = cur.fetchall()
    
    # Use View: Active Accounts
    cur.execute("""
        SELECT c.customer_id, c.first_name || ' ' || c.last_name AS customer_name,
               a.account_number, a.account_type, a.balance, a.status, u.is_active, u.user_id
        FROM users u
        JOIN customers c ON u.user_id = c.user_id
        JOIN accounts a ON c.customer_id = a.customer_id
        ORDER BY c.customer_id
        LIMIT 50
    """)
    active_accounts = cur.fetchall()

    # Get Global Transactions with dynamic limit
    txn_limit = request.args.get('txn_limit', 50, type=int)
    limit_clause = f"LIMIT {txn_limit}" if txn_limit > 0 else ""
    cur.execute(f"""
        SELECT t.transaction_id, t.transaction_type, t.amount, t.transaction_date, t.description, a.account_number
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        ORDER BY t.transaction_date DESC
        {limit_clause}
    """)
    global_transactions = cur.fetchall()

    # Get Pending Deposit Requests
    cur.execute("""
        SELECT dr.request_id, a.account_number, dr.amount, dr.created_at, c.first_name || ' ' || c.last_name
        FROM deposit_requests dr
        JOIN accounts a ON dr.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE dr.status = 'pending'
        ORDER BY dr.created_at DESC
    """)
    deposit_requests = cur.fetchall()

    # Get Pending Account Requests
    cur.execute("""
        SELECT request_id, username, email, first_name, last_name, created_at
        FROM account_requests
        WHERE status = 'pending'
        ORDER BY created_at DESC
    """)
    account_requests = cur.fetchall()
    
    return render_template('dashboard/admin.html', alerts=alerts, active_accounts=active_accounts, 
                           global_transactions=global_transactions, deposit_requests=deposit_requests,
                           account_requests=account_requests, txn_limit=txn_limit)

@admin_bp.route('/toggle_lock/<int:user_id>', methods=['POST'])
def toggle_lock(user_id):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("UPDATE users SET is_active = NOT is_active WHERE user_id = %s RETURNING is_active", (user_id,))
        new_status = cur.fetchone()[0]
        conn.commit()
        status_text = "unlocked" if new_status else "locked"
        flash(f"User account has been {status_text}.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error toggling lock: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/undo_transaction/<int:transaction_id>', methods=['POST'])
def undo_transaction(transaction_id):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("SELECT account_id, transaction_type, amount FROM transactions WHERE transaction_id = %s", (transaction_id,))
        txn = cur.fetchone()
        if txn:
            acc_id, txn_type, amount = txn
            if txn_type in ['withdrawal', 'fee', 'transfer']:
                cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (amount, acc_id))
            elif txn_type == 'deposit':
                cur.execute("UPDATE accounts SET balance = balance - %s WHERE account_id = %s", (amount, acc_id))
            
            cur.execute("DELETE FROM transactions WHERE transaction_id = %s", (transaction_id,))
            conn.commit()
            flash("Transaction undone and balance adjusted.", "success")
        else:
            flash("Transaction not found.", "warning")
    except Exception as e:
        conn.rollback()
        flash(f"Error undoing transaction: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/handle_deposit/<int:request_id>/<action>', methods=['POST'])
def handle_deposit(request_id, action):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        if action == 'accept':
            cur.execute("SELECT account_id, amount FROM deposit_requests WHERE request_id = %s AND status = 'pending'", (request_id,))
            req = cur.fetchone()
            if req:
                acc_id, amount = req
                cur.execute("UPDATE accounts SET balance = balance + %s WHERE account_id = %s", (amount, acc_id))
                cur.execute("INSERT INTO transactions (account_id, transaction_type, amount, description) VALUES (%s, 'deposit', %s, 'Approved Cash Deposit')", (acc_id, amount))
                cur.execute("UPDATE deposit_requests SET status = 'accepted' WHERE request_id = %s", (request_id,))
                conn.commit()
                flash("Deposit approved and processed.", "success")
        elif action == 'reject':
            cur.execute("UPDATE deposit_requests SET status = 'rejected' WHERE request_id = %s", (request_id,))
            conn.commit()
            flash("Deposit request rejected.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error handling deposit: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/handle_account_request/<int:request_id>/<action>', methods=['POST'])
def handle_account_request(request_id, action):
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        if action == 'accept':
            cur.execute("SELECT username, email, password_hash, first_name, last_name FROM account_requests WHERE request_id = %s AND status = 'pending'", (request_id,))
            req = cur.fetchone()
            if req:
                username, email, password_hash, first_name, last_name = req
                # Insert into users (role_id 1 = Customer)
                cur.execute("INSERT INTO users (username, email, password_hash, role_id) VALUES (%s, %s, %s, 1) RETURNING user_id", (username, email, password_hash))
                user_id = cur.fetchone()[0]
                # Insert into customers
                cur.execute("INSERT INTO customers (user_id, first_name, last_name) VALUES (%s, %s, %s) RETURNING customer_id", (user_id, first_name, last_name))
                customer_id = cur.fetchone()[0]
                # Create a default checking account
                import random
                acc_num = f"PK-BANK-{random.randint(1000, 9999)}"
                cur.execute("INSERT INTO accounts (account_number, customer_id, account_type) VALUES (%s, %s, 'checking')", (acc_num, customer_id))
                
                # Update status
                cur.execute("UPDATE account_requests SET status = 'accepted' WHERE request_id = %s", (request_id,))
                conn.commit()
                flash("Account request approved and user created.", "success")
        elif action == 'reject':
            cur.execute("UPDATE account_requests SET status = 'rejected' WHERE request_id = %s", (request_id,))
            conn.commit()
            flash("Account request rejected.", "info")
    except Exception as e:
        conn.rollback()
        flash(f"Error handling account request: {str(e)}", "danger")
    return redirect(url_for('admin.dashboard'))

@admin_bp.route('/backup/push', methods=['POST'])
def backup_push():
    result = postgres_to_firebase()
    return jsonify(result)

@admin_bp.route('/backup/pull', methods=['POST'])
def backup_pull():
    result = firebase_to_postgres()
    return jsonify(result)

@admin_bp.route('/post-interest', methods=['POST'])
def post_interest():
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

