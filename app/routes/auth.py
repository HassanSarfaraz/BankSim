from flask import Blueprint, render_template, request, redirect, url_for, session, flash
import bcrypt
from ..models.db import get_db_conn
from ..backup.sync import firebase_to_postgres_for_user, postgres_to_firebase_for_user

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

            # Verify password
            try:
                is_valid = bcrypt.checkpw(password.encode('utf-8'), pw_hash.encode('utf-8'))
            except Exception:
                is_valid = (password == pw_hash)  # Fallback for seed data

            if is_valid:
                session.permanent = True
                session['user_id'] = user_id
                session['role_id'] = role_id
                session['username'] = username

                # Log success and update last_login
                cur.execute("INSERT INTO login_attempts (user_id, success) VALUES (%s, TRUE)", (user_id,))
                cur.execute("UPDATE users SET previous_login = last_login, last_login = NOW() WHERE user_id = %s", (user_id,))
                conn.commit()

                # ── FIREBASE FIRST: pull any cloud data newer than local ──────
                try:
                    result = firebase_to_postgres_for_user(user_id)
                    if result.get('added'):
                        flash(f"Synced {result['added']} new record(s) from cloud.", "info")
                except Exception as fb_e:
                    # Non-fatal — log but don't block login
                    import logging
                    logging.getLogger(__name__).warning(f"Firebase pull on login failed: {fb_e}")

                if role_id == 1:
                    return redirect(url_for('customer.dashboard'))
                if role_id == 2:
                    return redirect(url_for('teller.dashboard'))
                if role_id == 3:
                    return redirect(url_for('admin.dashboard'))
                return redirect(url_for('customer.dashboard'))
            else:
                cur.execute("INSERT INTO login_attempts (user_id, success) VALUES (%s, FALSE)", (user_id,))
                conn.commit()
                flash("Invalid credentials.", "danger")
        else:
            flash("User not found.", "danger")

    return render_template('login.html')


@auth_bp.route('/logout')
def logout():
    user_id = session.get('user_id')

    # ── PUSH LOCAL → FIREBASE before clearing session ────────────────────────
    if user_id:
        try:
            postgres_to_firebase_for_user(user_id)
        except Exception as fb_e:
            import logging
            logging.getLogger(__name__).warning(f"Firebase push on logout failed: {fb_e}")

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
        date_of_birth = request.form.get('date_of_birth')
        phone = request.form.get('phone')
        city = request.form.get('city')
        country = request.form.get('country')

        pw_hash = bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

        conn = get_db_conn()
        cur = conn.cursor()
        try:
            cur.execute("""
                INSERT INTO account_requests (username, email, password_hash, first_name, last_name, date_of_birth, phone, city, country)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (username, email, pw_hash, first_name, last_name, date_of_birth, phone, city, country))
            conn.commit()
            flash("Account request submitted successfully. Please wait for admin approval.", "success")
            return redirect(url_for('auth.login'))
        except Exception:
            conn.rollback()
            flash("Error: Username or email might already be taken.", "danger")

    return render_template('signup.html')
