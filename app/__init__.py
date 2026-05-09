from flask import Flask
from .models.db import init_app as init_db
from .firebase.firestore import init_firebase
from config import Config
from datetime import timedelta


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    # ── Session: hard-coded key so cookie is NEVER invalidated on restart ──────
    app.config['SECRET_KEY'] = 'banksim-fixed-secret-key-do-not-change-2025'
    app.config['SESSION_COOKIE_NAME'] = 'banksim_session'
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    app.config['SESSION_COOKIE_SECURE'] = False       # True only on HTTPS/prod
    app.config['SESSION_COOKIE_PATH'] = '/'
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    app.config['SESSION_REFRESH_EACH_REQUEST'] = True

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
