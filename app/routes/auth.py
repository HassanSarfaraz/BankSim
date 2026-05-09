from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
from ..models.db import get_db_conn

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        conn = get_db_conn()
        cur = conn.cursor()
        
        cur.execute("SELECT user_id, password_hash, role_id, is_active FROM users WHERE username = %s", (username,))
        user = cur.fetchone()
        
        if user:
            user_id, pw_hash, role_id, is_active = user
            
            if not is_active:
                flash("Account Locked", "danger")
                return render_template('login.html')
            
            # Use bcrypt.checkpw if hash starts with $2b$, else simple check for dev
            try:
                is_valid = bcrypt.checkpw(password.encode('utf-8'), pw_hash.encode('utf-8'))
            except:
                is_valid = (password == pw_hash) # Fallback for seed data if not hashed
                
            if is_valid:
                session.permanent = True # Ensure session persists
                session['user_id'] = user_id
                session['role_id'] = role_id
                session['username'] = username
                
                # Log success and update last_login
                cur.execute("INSERT INTO login_attempts (user_id, success) VALUES (%s, TRUE)", (user_id,))
                cur.execute("UPDATE users SET last_login = NOW() WHERE user_id = %s", (user_id,))
                conn.commit()
                
                if role_id == 1: return redirect(url_for('customer.dashboard'))
                if role_id == 2: return redirect(url_for('teller.dashboard')) # To be implemented
                if role_id == 3: return redirect(url_for('admin.dashboard'))
                return redirect(url_for('customer.dashboard'))
            else:
                # Log failure
                cur.execute("INSERT INTO login_attempts (user_id, success) VALUES (%s, FALSE)", (user_id,))
                conn.commit()
                flash("Invalid credentials.", "danger")
        else:
            flash("User not found.", "danger")
            
    return render_template('login.html')

@auth_bp.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('auth.login'))

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        first_name = request.form.get('first_name')
        last_name = request.form.get('last_name')
        
        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')
        
        conn = get_db_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO account_requests (username, email, password_hash, first_name, last_name)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, email, pw_hash, first_name, last_name))
            conn.commit()
            flash("Account request submitted successfully. Please wait for admin approval.", "success")
            return redirect(url_for('auth.login'))
        except Exception as e:
            conn.rollback()
            flash("Error: Username or email might already be taken.", "danger")
            
    return render_template('signup.html')
