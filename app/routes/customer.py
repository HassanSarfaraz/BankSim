from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from ..models.db import get_db_conn
from ..backup.sync import push_record
from ..firebase.firestore import sync_doc_to_firestore
import psycopg2
import os

customer_bp = Blueprint('customer', __name__)


def _check_login():
    """Returns True if user is NOT a valid logged-in customer."""
    return 'user_id' not in session or int(session.get('role_id', 0)) not in (1, 2)


@customer_bp.route('/dashboard')
def dashboard():
    if _check_login():
        return redirect(url_for('auth.login'))

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.first_name, c.last_name, a.account_id, a.account_number,
               a.account_type, a.balance, a.status
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE c.user_id = %s
        ORDER BY a.account_id
    """, (session['user_id'],))
    accounts = cur.fetchall()

    cur.execute("""
        SELECT t.transaction_id, t.transaction_type, t.amount,
               t.transaction_date, t.description, t.status
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE c.user_id = %s
        ORDER BY t.transaction_date DESC
        LIMIT 10
    """, (session['user_id'],))
    transactions = cur.fetchall()

    cur.execute("SELECT previous_login FROM users WHERE user_id = %s", (session['user_id'],))
    last_login_res = cur.fetchone()
    last_login = last_login_res[0] if last_login_res else None

    return render_template('dashboard/customer.html', accounts=accounts, transactions=transactions, last_login=last_login)


@customer_bp.route('/transfer', methods=['POST'])
def transfer():
    if _check_login():
        return redirect(url_for('auth.login'))

    from_acc = request.form.get('from_account', '').strip()
    to_acc_num = request.form.get('to_account_number', '').strip()
    amount_str = request.form.get('amount', '0').strip()
    desc = 'Fund Transfer'

    # Validate inputs
    if not from_acc or not to_acc_num:
        flash("Please fill in all transfer fields.", "danger")
        return redirect(url_for('customer.dashboard'))

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Amount must be greater than zero.", "danger")
            return redirect(url_for('customer.dashboard'))
    except (ValueError, TypeError):
        flash("Invalid amount entered.", "danger")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        # Look up recipient account
        cur.execute("SELECT account_id FROM accounts WHERE account_number = %s", (to_acc_num,))
        res = cur.fetchone()
        if not res:
            flash(f"Recipient account '{to_acc_num}' not found.", "danger")
            return redirect(url_for('customer.dashboard'))

        to_acc_id = int(res[0])
        from_acc_id = int(from_acc)

        if from_acc_id == to_acc_id:
            flash("Cannot transfer to the same account.", "danger")
            return redirect(url_for('customer.dashboard'))

        # Execute stored procedure
        cur.execute("CALL transfer_funds(%s, %s, %s, %s)", (from_acc_id, to_acc_id, amount, desc))
        conn.commit()

        # Push updated balances to Firebase
        for acc_id in [from_acc_id, to_acc_id]:
            cur.execute("SELECT account_id, balance, status FROM accounts WHERE account_id = %s", (acc_id,))
            acc = cur.fetchone()
            if acc:
                push_record('accounts', acc[0], {
                    'account_id': str(acc[0]),
                    'balance': str(acc[1]),
                    'status': str(acc[2])
                })

        if amount >= 10000:
            flash("Transfer submitted. Amounts ≥ $10,000 require admin approval before funds move.", "warning")
        else:
            flash("Transfer successful!", "success")

    except psycopg2.Error as e:
        conn.rollback()
        # Extract clean error message from Postgres exception
        msg = str(e).split('\n')[0]
        flash(f"Transfer failed: {msg}", "danger")
    except Exception as e:
        conn.rollback()
        flash(f"Unexpected error: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/request_deposit', methods=['POST'])
def request_deposit():
    if _check_login():
        return redirect(url_for('auth.login'))

    account_id = request.form.get('account_id', '').strip()
    amount_str = request.form.get('amount', '0').strip()

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Amount must be positive.", "danger")
            return redirect(url_for('customer.dashboard'))
    except (ValueError, TypeError):
        flash("Invalid amount.", "danger")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO deposit_requests (account_id, amount) VALUES (%s, %s) RETURNING request_id",
            (int(account_id), amount)
        )
        req_id = cur.fetchone()[0]
        conn.commit()

        push_record('deposit_requests', req_id, {
            'request_id': str(req_id),
            'account_id': str(account_id),
            'amount': str(amount),
            'status': 'pending'
        })
        flash("Deposit request submitted. Awaiting admin approval.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/upload-kyc', methods=['POST'])
def upload_kyc():
    if _check_login():
        return redirect(url_for('auth.login'))

    file = request.files.get('document')
    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute("""
            INSERT INTO media_storage (user_id, media_type, file_name, file_data)
            VALUES (%s, 'document', %s, %s)
        """, (session['user_id'], file.filename, psycopg2.Binary(file.read())))
        conn.commit()
        flash("Document uploaded securely.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Upload error: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/upload-profile-pic', methods=['POST'])
def upload_profile_pic():
    if _check_login():
        return redirect(url_for('auth.login'))

    file = request.files.get('profile_pic')
    if not file or not file.filename:
        flash("No file selected.", "warning")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        # Get account number or fallback to username
        cur.execute("SELECT c.customer_id FROM customers c WHERE c.user_id = %s", (session['user_id'],))
        c_res = cur.fetchone()
        identifier = session.get('username')
        if c_res:
            cur.execute("SELECT account_number FROM accounts WHERE customer_id = %s ORDER BY account_id LIMIT 1", (c_res[0],))
            a_res = cur.fetchone()
            if a_res:
                identifier = a_res[0]
                
        # Save file locally
        ext = file.filename.split('.')[-1]
        filename = f"{identifier}.{ext}"
        upload_dir = os.path.join('app', 'static', 'profile_pics')
        os.makedirs(upload_dir, exist_ok=True)
        file.save(os.path.join(upload_dir, filename))
        
        # Save relative path to PostgreSQL
        db_path = f"profile_pics/{filename}"
        cur.execute("UPDATE users SET profile_image = %s WHERE user_id = %s", (db_path, session['user_id']))
        conn.commit()
        
        # Sync text path to Firebase
        try:
            sync_doc_to_firestore('users', session['user_id'], {'profile_image': db_path})
        except Exception as fb_e:
            print(f"Warning: Firebase sync failed: {fb_e}")

        flash("Profile picture updated successfully.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/open_account', methods=['POST'])
def open_account():
    if _check_login():
        return redirect(url_for('auth.login'))

    account_type = request.form.get('account_type', 'checking').strip().lower()
    if account_type not in ('checking', 'savings', 'business'):
        flash("Invalid account type selected.", "warning")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()
    try:
        # Get customer_id
        cur.execute("SELECT customer_id FROM customers WHERE user_id = %s", (session['user_id'],))
        c_res = cur.fetchone()
        if not c_res:
            flash("Customer profile not found.", "danger")
            return redirect(url_for('customer.dashboard'))
            
        customer_id = c_res[0]
        
        # Generate random account number
        import random
        acc_num = f"PK-BANK-{random.randint(10000, 99999)}"
        
        # Insert new account
        cur.execute(
            "INSERT INTO accounts (account_number, customer_id, account_type, balance, status) VALUES (%s, %s, %s, 0.00, 'active') RETURNING account_id",
            (acc_num, customer_id, account_type)
        )
        account_id = cur.fetchone()[0]
        conn.commit()
        
        # Sync to Firebase
        push_record('accounts', account_id, {
            'account_id': account_id,
            'account_number': acc_num,
            'customer_id': customer_id,
            'account_type': account_type,
            'balance': 0.00,
            'status': 'active'
        })
        
        flash(f"New {account_type.capitalize()} account opened successfully! Account #{acc_num}", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error opening account: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))
