from flask import Blueprint, render_template, request, session, redirect, url_for, flash
from ..models.db import get_db_conn
from ..firebase.firestore import upload_to_firebase, sync_doc_to_firestore

customer_bp = Blueprint('customer', __name__)

@customer_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role_id') != 1:
        return redirect(url_for('auth.login'))
        
    conn = get_db_conn()
    cur = conn.cursor(cursor_factory=None) # Default cursor
    
    # Get Customer Info + Accounts (JOIN)
    cur.execute("""
        SELECT c.first_name, c.last_name, a.account_id, a.account_number, 
               a.account_type, a.balance, a.status
        FROM customers c
        JOIN accounts a ON c.customer_id = a.customer_id
        WHERE c.user_id = %s
    """, (session['user_id'],))
    accounts = cur.fetchall()
    
    # Get recent transactions (Partitioned table)
    cur.execute("""
        SELECT t.transaction_id, t.transaction_type, t.amount, t.transaction_date, t.description
        FROM transactions t
        JOIN accounts a ON t.account_id = a.account_id
        JOIN customers c ON a.customer_id = c.customer_id
        WHERE c.user_id = %s
        ORDER BY t.transaction_date DESC
        LIMIT 10
    """, (session['user_id'],))
    transactions = cur.fetchall()
    
    return render_template('dashboard/customer.html', accounts=accounts, transactions=transactions)

@customer_bp.route('/transfer', methods=['POST'])
def transfer():
    from_acc = request.form.get('from_account')
    to_acc_num = request.form.get('to_account_number')
    amount = float(request.form.get('amount'))
    desc = request.form.get('description', 'Fund Transfer')
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        # Find to_account_id from account_number
        cur.execute("SELECT account_id FROM accounts WHERE account_number = %s", (to_acc_num,))
        res = cur.fetchone()
        if not res:
            flash("Recipient account not found.", "danger")
            return redirect(url_for('customer.dashboard'))
        
        to_acc = res[0]
        
        # Call Stored Procedure (ACID Transaction)
        cur.execute("CALL transfer_funds(%s, %s, %s, %s)", (from_acc, to_acc, amount, desc))
        conn.commit()
        
        # Mirror to Firebase
        sync_doc_to_firestore('transactions', f"transfer_{from_acc}_{to_acc}", {
            'from': from_acc,
            'to': to_acc,
            'amount': amount,
            'desc': desc
        })
        
        flash("Transfer successful!", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Transfer failed: {str(e)}", "danger")
        
    return redirect(url_for('customer.dashboard'))

@customer_bp.route('/upload-kyc', methods=['POST'])
def upload_kyc():
    file = request.files.get('document')
    if file:
        file_data = file.read()
        filename = file.filename
        
        conn = get_db_conn()
        cur = conn.cursor()
        
        import psycopg2
        # Store in Postgres (BYTEA)
        cur.execute("""
            INSERT INTO media_storage (user_id, media_type, file_name, file_data)
            VALUES (%s, %s, %s, %s) RETURNING media_id
        """, (session['user_id'], 'document', filename, psycopg2.Binary(file_data)))
        
        media_id = cur.fetchone()[0]
        conn.commit()
        
        # Upload to Firebase Storage
        fb_path = upload_to_firebase(file_data, filename, session['user_id'])
        if fb_path:
            cur.execute("UPDATE media_storage SET firebase_path = %s WHERE media_id = %s", (fb_path, media_id))
            conn.commit()
            
        flash("Document uploaded successfully.", "success")
        
    return redirect(url_for('customer.dashboard'))

@customer_bp.route('/request_deposit', methods=['POST'])
def request_deposit():
    account_id = request.form.get('account_id')
    amount = float(request.form.get('amount'))
    
    conn = get_db_conn()
    cur = conn.cursor()
    
    try:
        cur.execute("INSERT INTO deposit_requests (account_id, amount) VALUES (%s, %s)", (account_id, amount))
        conn.commit()
        
        # Mirror to Firebase explicitly if needed, but the admin's push/pull will handle it if deposit_requests is in SYNC_TABLES
        sync_doc_to_firestore('deposit_requests', f"req_{account_id}_{amount}", {
            'account_id': account_id,
            'amount': amount,
            'status': 'pending'
        })
        
        flash("Deposit request submitted successfully. Awaiting admin approval.", "success")
    except Exception as e:
        conn.rollback()
        flash(f"Error submitting request: {str(e)}", "danger")
        
    return redirect(url_for('customer.dashboard'))
