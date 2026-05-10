import os
from flask import Flask
from .models.db import init_app as init_db
from .firebase.firestore import init_firebase
from config import Config
from datetime import timedelta
from flask_session import Session


def ensure_db_objects(app):
    """
    Runs on every app startup to guarantee all DB tables and views exist.
    - Tables use CREATE TABLE IF NOT EXISTS (safe to re-run)
    - Views use CREATE OR REPLACE (safe to re-run)
    This prevents missing-table or missing-view crashes without needing pgAdmin4.
    """
    import psycopg2
    sql_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'sql', 'views.sql')

    # SQL to ensure any tables added after initial schema setup exist
    ENSURE_TABLES_SQL = """
    CREATE TABLE IF NOT EXISTS support_tickets (
        ticket_id BIGSERIAL PRIMARY KEY,
        user_id BIGINT REFERENCES users(user_id) ON DELETE CASCADE,
        subject VARCHAR(200) NOT NULL,
        message TEXT NOT NULL,
        admin_reply TEXT,
        status VARCHAR(20) DEFAULT 'pending',
        created_at TIMESTAMP DEFAULT NOW(),
        updated_at TIMESTAMP DEFAULT NOW()
    );
    CREATE INDEX IF NOT EXISTS idx_tickets_user ON support_tickets(user_id);
    CREATE INDEX IF NOT EXISTS idx_tickets_status ON support_tickets(status);
    """

    try:
        conn = psycopg2.connect(
            dbname=app.config.get('POSTGRES_DB'),
            user=app.config.get('POSTGRES_USER'),
            password=app.config.get('POSTGRES_PASSWORD'),
            host=app.config.get('POSTGRES_HOST', 'localhost'),
            port=app.config.get('POSTGRES_PORT', 5432),
        )
        cur = conn.cursor()

        # 1. Ensure any missing tables
        cur.execute(ENSURE_TABLES_SQL)
        conn.commit()

        # 2. Ensure all views (CREATE OR REPLACE)
        with open(sql_path, 'r') as f:
            views_sql = f.read()
        cur.execute(views_sql)
        conn.commit()

        # 3. Reset sequences to prevent duplicate key errors from manual inserts
        RESET_SEQUENCES_SQL = """
        SELECT setval('deposit_requests_request_id_seq', COALESCE((SELECT MAX(request_id) FROM deposit_requests), 1));
        SELECT setval('support_tickets_ticket_id_seq',   COALESCE((SELECT MAX(ticket_id)   FROM support_tickets),   1));
        SELECT setval('fraud_alerts_alert_id_seq',       COALESCE((SELECT MAX(alert_id)    FROM fraud_alerts),      1));
        SELECT setval('accounts_account_id_seq',         COALESCE((SELECT MAX(account_id)  FROM accounts),          1));
        SELECT setval('users_user_id_seq',               COALESCE((SELECT MAX(user_id)     FROM users),             1));
        SELECT setval('audit_log_log_id_seq',            COALESCE((SELECT MAX(log_id)      FROM audit_log),         1));
        SELECT setval('account_requests_request_id_seq', COALESCE((SELECT MAX(request_id)  FROM account_requests),  1));
        """
        cur.execute(RESET_SEQUENCES_SQL)
        conn.commit()

        conn.close()
        print("[BankSim] ✅ Database tables, views, and sequences ensured.")
    except Exception as e:
        print(f"[BankSim] ⚠️  Could not ensure DB objects: {e}")


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Hard-coded SECRET_KEY so cookie is NEVER invalidated on restart ──────────
    app.config['SECRET_KEY'] = 'banksim-fixed-secret-key-do-not-change-2025'

    # ── Server-side filesystem sessions (most reliable — no cookie size limits,
    #    survives reloader restarts, works across all routes) ─────────────────────
    sessions_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'flask_sessions')
    os.makedirs(sessions_dir, exist_ok=True)

    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_FILE_DIR'] = sessions_dir
    app.config['SESSION_FILE_THRESHOLD'] = 500          # max session files
    app.config['SESSION_PERMANENT'] = True
    app.config['SESSION_USE_SIGNER'] = True             # sign session IDs
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_COOKIE_NAME'] = 'banksim_sid'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False          # True only on HTTPS
    app.config['SESSION_COOKIE_PATH'] = '/'

    Session(app)  # initialize server-side sessions

    # ── Init DB and Firebase ───────────────────────────────────────────────────
    init_db(app)
    init_firebase(app)

    # ── Ensure all DB tables and views exist (safe to re-run) ────────────────
    ensure_db_objects(app)

    # ── Register Blueprints ────────────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.customer import customer_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    def index():
        from flask import session, redirect, url_for
        if 'user_id' in session:
            return redirect(url_for('admin.dashboard') if session.get('role_id') == 3 else url_for('customer.dashboard'))
        return redirect(url_for('auth.login'))

    return app
