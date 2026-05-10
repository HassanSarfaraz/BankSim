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
               a.account_type, a.balance, a.status, a.interest_rate, a.overdraft_limit
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE c.user_id = %s
        ORDER BY a.account_id
    """, (session['user_id'],))
    accounts = cur.fetchall()

    cur.execute("""
        SELECT t.transaction_id, t.transaction_type, t.amount,
               t.transaction_date, t.description, t.status, t.balance_after
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE c.user_id = %s
        ORDER BY t.transaction_date DESC
        LIMIT 10
    """, (session['user_id'],))
    transactions = cur.fetchall()

    cur.execute("SELECT previous_login, profile_image FROM users WHERE user_id = %s", (session['user_id'],))
    user_res = cur.fetchone()
    last_login = user_res[0] if user_res else None
    raw_image = user_res[1] if user_res else None

    # Only use profile_image if the file actually exists on disk
    if raw_image:
        image_path = os.path.join('app', 'static', raw_image)
        profile_image = raw_image if os.path.exists(image_path) else None
    else:
        profile_image = None

    # Fetch support tickets
    cur.execute("SELECT ticket_id, subject, message, admin_reply, status, created_at, updated_at FROM support_tickets WHERE user_id = %s ORDER BY updated_at DESC", (session['user_id'],))
    tickets = cur.fetchall()

    # Fetch loans
    cur.execute("""
        SELECT loan_id, loan_type, principal_amount, interest_rate, tenure_months, emi, outstanding_balance, status, disbursement_date
        FROM loans l
        JOIN customers c ON l.customer_id = c.customer_id
        WHERE c.user_id = %s
        ORDER BY disbursement_date DESC NULLS FIRST
    """, (session['user_id'],))
    loans = cur.fetchall()

    return render_template('dashboard/customer.html', 
                         accounts=accounts, 
                         transactions=transactions, 
                         last_login=last_login,
                         profile_image=profile_image,
                         tickets=tickets,
                         loans=loans)


@customer_bp.route('/apply_loan', methods=['POST'])
def apply_loan():
    if _check_login():
        return redirect(url_for('auth.login'))

    loan_type = request.form.get('loan_type', 'personal').strip()
    amount_str = request.form.get('amount', '0').strip()
    tenure_str = request.form.get('tenure', '12').strip()

    try:
        amount = float(amount_str)
        tenure = int(tenure_str)
        if amount <= 0 or tenure <= 0:
            flash("Amount and tenure must be positive.", "warning")
            return redirect(url_for('customer.dashboard'))
    except (ValueError, TypeError):
        flash("Invalid amount or tenure.", "danger")
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

        # Define interest rate based on loan type
        rates = {'personal': 0.12, 'home': 0.08, 'car': 0.10, 'education': 0.07}
        rate = rates.get(loan_type, 0.12)

        # Use SQL function calculate_emi to get monthly payment
        cur.execute("SELECT calculate_emi(%s, %s, %s)", (amount, rate, tenure))
        emi = cur.fetchone()[0]

        # Insert loan request
        cur.execute("""
            INSERT INTO loans (customer_id, loan_type, principal_amount, interest_rate, tenure_months, emi, outstanding_balance, status)
            VALUES (%s, %s, %s, %s, %s, %s, %s, 'pending')
            RETURNING loan_id
        """, (customer_id, loan_type, amount, rate, tenure, emi, amount))
        loan_id = cur.fetchone()[0]

        # Audit Log
        cur.execute("""
            INSERT INTO audit_log (user_id, action, table_name, record_id, new_value)
            VALUES (%s, 'APPLY_LOAN', 'loans', %s,
                    jsonb_build_object('loan_type', %s, 'amount', %s, 'status', 'pending'))
        """, (session['user_id'], loan_id, loan_type, amount))
        
        conn.commit()

        # Push to Firebase
        push_record('loans', loan_id, {
            'loan_id': str(loan_id),
            'customer_id': str(customer_id),
            'loan_type': loan_type,
            'amount': str(amount),
            'emi': str(emi),
            'status': 'pending'
        })

        flash(f"{loan_type.capitalize()} loan application submitted! Awaiting admin approval.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error applying for loan: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))


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

        # Push updated balances and transactions to Firebase
        for acc_id in [from_acc_id, to_acc_id]:
            cur.execute("SELECT account_id, balance, status FROM accounts WHERE account_id = %s", (acc_id,))
            acc = cur.fetchone()
            if acc:
                push_record('accounts', acc[0], {
                    'account_id': str(acc[0]),
                    'balance': str(acc[1]),
                    'status': str(acc[2])
                })
            
            # Push the latest transaction for this account
            cur.execute("SELECT * FROM transactions WHERE account_id = %s ORDER BY transaction_date DESC LIMIT 1", (acc_id,))
            t_data = cur.fetchone()
            if t_data:
                # (transaction_id(0), account_id(1), type(2), amount(3), balance_after(4), desc(5), ref(6), status(7), date(8))
                push_record('transactions_2026', t_id := t_data[0], {
                    'transaction_id': t_id,
                    'account_id': t_data[1],
                    'transaction_type': t_data[2],
                    'amount': str(t_data[3]),
                    'balance_after': str(t_data[4]) if t_data[4] else None,
                    'description': t_data[5],
                    'status': t_data[7],
                    'transaction_date': t_data[8].isoformat() if t_data[8] else None
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
        identifier = str(session['user_id'])
                
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
        
        # Generate standardized account number
        import random
        acc_num = f"PK99-BANK-{random.randint(10000, 99999)}"
        
        # Insert new account with pending status
        cur.execute(
            "INSERT INTO accounts (account_number, customer_id, account_type, balance, status) VALUES (%s, %s, %s, 0.00, 'pending') RETURNING account_id",
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
            'status': 'pending'
        })
        
        flash(f"New {account_type.capitalize()} account requested successfully! Admin approval pending.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error opening account: {str(e)}", "danger")

    return redirect(url_for('customer.dashboard'))

@customer_bp.route('/submit_ticket', methods=['POST'])
def submit_ticket():
    if _check_login():
        return redirect(url_for('auth.login'))
        
    subject = request.form.get('subject')
    message = request.form.get('message')
    
    if not subject or not message:
        flash("Subject and message are required.", "warning")
        return redirect(url_for('customer.dashboard'))
        
    conn = get_db_conn()
    cur = conn.cursor()
    try:
        cur.execute(
            "INSERT INTO support_tickets (user_id, subject, message) VALUES (%s, %s, %s) RETURNING ticket_id",
            (session['user_id'], subject, message)
        )
        ticket_id = cur.fetchone()[0]

        # Write to audit log so admin audit view reflects this action
        cur.execute("""
            INSERT INTO audit_log (user_id, action, table_name, record_id, new_value)
            VALUES (%s, 'SUBMIT_TICKET', 'support_tickets', %s,
                    jsonb_build_object('ticket_id', %s, 'subject', %s))
        """, (session['user_id'], ticket_id, ticket_id, subject))
        conn.commit()

        push_record('support_tickets', ticket_id, {
            'ticket_id': str(ticket_id),
            'user_id': str(session['user_id']),
            'subject': subject,
            'message': message,
            'status': 'pending'
        })
        flash("Support ticket submitted successfully. Admin will reply soon.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error submitting ticket: {str(e)}", "danger")
        
    return redirect(url_for('customer.dashboard'))
