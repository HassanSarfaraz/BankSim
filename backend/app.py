from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_jwt_extended import JWTManager
from flask_cors import CORS
from backend.config import Config

db = SQLAlchemy()
jwt = JWTManager()

def create_app(config_class=Config):
    app = Flask(__name__)
    app.config.from_object(config_class)

    db.init_app(app)
    jwt.init_app(app)
    CORS(app)

    # Register blueprints
    from backend.routes.auth import auth_bp
    from backend.routes.manager import manager_bp
    from backend.routes.accountant import accountant_bp
    from backend.routes.customer import customer_bp

    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(manager_bp, url_prefix='/api/manager')
    app.register_blueprint(accountant_bp, url_prefix='/api/accountant')
    app.register_blueprint(customer_bp, url_prefix='/api/customer')

    @app.route('/health')
    def health():
        return {"status": "healthy"}, 200

    return app

if __name__ == '__main__':
    app = create_app()
    app.run(host='0.0.0.0', port=5000, debug=True)
