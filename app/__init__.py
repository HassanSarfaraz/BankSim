from flask import Flask
from .models.db import init_app as init_db
from .firebase.firestore import init_firebase
from config import Config

def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)
    
    # Force deterministic secret key and permanent sessions
    app.config['SECRET_KEY'] = 'banksim-super-secret-key-permanent-2025'
    from datetime import timedelta
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(days=7)
    
    # Initialize DB and Firebase
    init_db(app)
    init_firebase(app)
    
    # Register Blueprints
    from .routes.auth import auth_bp
    from .routes.customer import customer_bp
    from .routes.admin import admin_bp
    
    app.register_blueprint(auth_bp)
    app.register_blueprint(customer_bp, url_prefix='/customer')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    
    @app.route('/')
    def index():
        from flask import redirect, url_for
        return redirect(url_for('auth.login'))
        
    return app
