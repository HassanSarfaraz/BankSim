import os
from flask import Flask
from .models.db import init_app as init_db
from .firebase.firestore import init_firebase
from config import Config
from datetime import timedelta
from flask_session import Session


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
