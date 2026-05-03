# ===========================================================================
# SecureBank Management System
# Flask Configuration — no Docker, local PostgreSQL + MongoDB
# ===========================================================================
import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    # ---- Flask core --------------------------------------------------------
    SECRET_KEY = os.getenv('SECRET_KEY', 'securebank-dev-secret-2026-very-secure-32bytes-long-key')

    # ---- JWT ---------------------------------------------------------------
    JWT_SECRET_KEY = os.getenv('JWT_SECRET_KEY', 'jwt-securebank-key-2026-very-secure-32bytes-long-key')
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(hours=8)

    # ---- PostgreSQL --------------------------------------------------------
    DB_USER     = os.getenv('DB_USER',     'postgres')
    DB_PASSWORD = os.getenv('DB_PASSWORD', 'postgres')
    DB_HOST     = os.getenv('DB_HOST',     'localhost')
    DB_PORT     = os.getenv('DB_PORT',     '5432')
    DB_NAME     = os.getenv('DB_NAME',     'securebank')

    SQLALCHEMY_DATABASE_URI = (
        f"postgresql://{DB_USER}:{DB_PASSWORD}@{DB_HOST}:{DB_PORT}/{DB_NAME}"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_size': 10,
        'pool_recycle': 300,
        'pool_pre_ping': True,
    }

    # ---- MongoDB -----------------------------------------------------------
    MONGO_URI = os.getenv('MONGO_URI', 'mongodb://localhost:27017/securebank_audit')
