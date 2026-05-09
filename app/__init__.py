from flask import Flask
from .models.db import init_app as init_db
from .firebase.firestore import init_firebase
from config import Config
from datetime import timedelta


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ─── Session Configuration ─────────────────────────────────────────────────
    # Hard-coded key so it NEVER changes between restarts (changing it kills sessions)
    app.config['SECRET_KEY'] = 'banksim-fixed-secret-key-do-not-change-2025'
    app.config['SESSION_COOKIE_NAME'] = 'banksim_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False          # set True only on HTTPS
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True    # refresh cookie on every request

    # ─── Init DB and Firebase ──────────────────────────────────────────────────
    init_db(app)
    init_firebase(app)

    # ─── Pull cloud data into local DB on startup ──────────────────────────────
    with app.app_context():
        try:
            from .backup.sync import firebase_to_postgres
            result = firebase_to_postgres()
            print(f"Startup cloud sync: {result.get('status')} | tables: {list(result.get('restored', {}).keys())}")
        except Exception as e:
            print(f"Startup cloud sync skipped: {e}")

    # ─── Register Blueprints ───────────────────────────────────────────────────
    from .routes.auth import auth_bp
    from .routes.customer import customer_bp
    from .routes.admin import admin_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')

    @app.route('/')
    def index():
        from flask import session, redirect, url_for
        # If already logged in, go to appropriate dashboard
        if 'user_id' in session:
            role = session.get('role_id')
            if role == 3:
                return redirect(url_for('admin.dashboard'))
            return redirect(url_for('customer.dashboard'))
        return redirect(url_for('auth.login'))

    return app
