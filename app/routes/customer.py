from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from ..models.db import get_db_conn
from ..backup.sync import push_record

customer_bp = Blueprint('customer', __name__)


def _require_customer():
    return 'user_id' not in session or session.get('role_id') != 1


@customer_bp.route('/dashboard')
def dashboard():
    if _require_customer():
        return redirect(url_for('auth.login'))

    conn = get_db_conn()
    cur = conn.cursor()

    cur.execute("""
        SELECT c.first_name, c.last_name, a.account_id, a.account_number,
               a.account_type, a.balance, a.status
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE c.user_id = %s
    """, (session['user_id'],))
    accounts = cur.fetchall()

    cur.execute("""
        SELECT t.transaction_id, t.transaction_type, t.amount, t.transaction_date, t.description
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE c.user_id = %s AND t.status = 'completed'
        ORDER BY t.transaction_date DESC
        LIMIT 10
    """, (session['user_id'],))
    transactions = cur.fetchall()

    return render_template('dashboard/customer.html', accounts=accounts, transactions=transactions)


@customer_bp.route('/transfer', methods=['POST'])
def transfer():
    if _require_customer():
        return redirect(url_for('auth.login'))

    from_acc = request.form.get('from_account')
    to_acc_num = request.form.get('to_account_number')
    amount_str = request.form.get('amount', '0')
    desc = request.form.get('description', 'Fund Transfer')

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Amount must be positive.", "danger")
            return redirect(url_for('customer.dashboard'))
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute("SELECT account_id FROM accounts WHERE account_number = %s", (to_acc_num,))
        res = cur.fetchone()
        if not res:
            flash("Recipient account not found.", "danger")
            return redirect(url_for('customer.dashboard'))

        to_acc = res[0]
        cur.execute("CALL transfer_funds(%s, %s, %s, %s)", (from_acc, to_acc, amount, desc))
        conn.commit()

        # Push updated accounts to Firebase
        for acc_id in [from_acc, to_acc]:
            cur.execute("SELECT account_id, balance, status FROM accounts WHERE account_id = %s", (acc_id,))
            acc = cur.fetchone()
            if acc:
                push_record('accounts', acc[0], {'account_id': acc[0], 'balance': acc[1], 'status': acc[2]})

        if amount >= 10000:
            flash("Transfer submitted. Amounts ≥$10,000 require admin approval before processing.", "warning")
        else:
            flash("Transfer successful!", "success")

    except Exception as e:
        conn.rollback()
        flash(f"Transfer failed: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/upload-kyc', methods=['POST'])
def upload_kyc():
    if _require_customer():
        return redirect(url_for('auth.login'))

    file = request.files.get('document')
    if file and file.filename:
        file_data = file.read()
        filename = file.filename

        conn = get_db_conn()
        cur = conn.cursor()
        import psycopg2

        try:
            cur.execute("""
                INSERT INTO media_storage (user_id, media_type, file_name, file_data)
                VALUES (%s, 'document', %s, %s)
            """, (session['user_id'], filename, psycopg2.Binary(file_data)))
            conn.commit()
            flash("Document uploaded securely to local database.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Upload error: {str(e)}", "danger")
    else:
        flash("No file selected.", "warning")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/upload-profile-pic', methods=['POST'])
def upload_profile_pic():
    if _require_customer():
        return redirect(url_for('auth.login'))

    file = request.files.get('profile_pic')
    if file and file.filename:
        file_data = file.read()

        conn = get_db_conn()
        cur = conn.cursor()
        import psycopg2

        try:
            cur.execute("UPDATE users SET profile_image = %s WHERE user_id = %s",
                        (psycopg2.Binary(file_data), session['user_id']))
            conn.commit()
            flash("Profile picture updated.", "success")
        except Exception as e:
            conn.rollback()
            flash(f"Error: {str(e)}", "danger")
    else:
        flash("No file selected.", "warning")

    return redirect(url_for('customer.dashboard'))


@customer_bp.route('/request_deposit', methods=['POST'])
def request_deposit():
    if _require_customer():
        return redirect(url_for('auth.login'))

    account_id = request.form.get('account_id')
    amount_str = request.form.get('amount', '0')

    try:
        amount = float(amount_str)
        if amount <= 0:
            flash("Amount must be positive.", "danger")
            return redirect(url_for('customer.dashboard'))
    except ValueError:
        flash("Invalid amount.", "danger")
        return redirect(url_for('customer.dashboard'))

    conn = get_db_conn()
    cur = conn.cursor()

    try:
        cur.execute(
            "INSERT INTO deposit_requests (account_id, amount) VALUES (%s, %s) RETURNING request_id",
            (account_id, amount)
        )
        req_id = cur.fetchone()[0]
        conn.commit()

        # Push to Firebase immediately so admin on any machine sees it
        push_record('deposit_requests', req_id, {
            'request_id': req_id,
            'account_id': account_id,
            'amount': amount,
            'status': 'pending'
        })
        flash("Deposit request submitted. Awaiting admin approval.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))
