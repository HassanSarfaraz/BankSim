# ===========================================================================
# SecureBank — Flask Application Factory
# Registers all blueprints, initialises extensions, creates tables if needed.
# ===========================================================================
from flask import Flask, jsonify
from flask_cors import CORS
from backend.config import Config
from backend.extensions import db, jwt


def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    # ---- extensions --------------------------------------------------------
    CORS(app)
    db.init_app(app)
    jwt.init_app(app)

    # ---- blueprints (lazy imports avoid circular deps) ---------------------
    from backend.routes.auth import auth_bp
    from backend.routes.manager import manager_bp
    from backend.routes.accountant import accountant_bp
    from backend.routes.customer import customer_bp

    app.register_blueprint(auth_bp,       url_prefix='/api/auth')
    app.register_blueprint(manager_bp,    url_prefix='/api/manager')
    app.register_blueprint(accountant_bp, url_prefix='/api/accountant')
    app.register_blueprint(customer_bp,   url_prefix='/api/customer')

    # ---- health check ------------------------------------------------------
    @app.route('/api/health', methods=['GET'])
    def health_check():
        try:
            db.session.execute(db.text('SELECT 1'))
            pg_ok = True
        except Exception:
            pg_ok = False
        return jsonify({
            "status": "healthy" if pg_ok else "degraded",
            "postgres": pg_ok,
        }), 200 if pg_ok else 503

    # ---- create tables (dev convenience) -----------------------------------
    with app.app_context():
        # Import all models so SQLAlchemy sees them
        import backend.models.user        # noqa
        import backend.models.account     # noqa
        import backend.models.transaction # noqa
        import backend.models.loan        # noqa

    return app


# ---------------------------------------------------------------------------
# Run directly:  python -m backend.app
# ---------------------------------------------------------------------------
if __name__ == '__main__':
    app = create_app()
    app.run(host='127.0.0.1', port=5000, debug=True, use_reloader=False)
