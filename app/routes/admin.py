from flask import Blueprint, render_template, request, session, redirect, url_for, flash, jsonify
from ..models.db import get_db_conn
from ..backup.sync import postgres_to_firebase, firebase_to_postgres

admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/dashboard')
def dashboard():
    if 'user_id' not in session or session.get('role_id') != 3:
        return redirect(url_for('auth.login'))
        
    conn = get_db_conn()
    cur = conn.cursor()
    
    # Use View: Open Fraud Alerts
    cur.execute("SELECT * FROM open_fraud_alerts_view")
    alerts = cur.fetchall()
    
    # Use View: Active Accounts
    cur.execute("SELECT * FROM active_accounts_view LIMIT 20")
    active_accounts = cur.fetchall()
    
    return render_template('dashboard/admin.html', alerts=alerts, active_accounts=active_accounts)

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
