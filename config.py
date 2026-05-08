import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', 'banksim-premium-secret-key-2025')
    
    # PostgreSQL Configuration
    POSTGRES_USER = os.environ.get('POSTGRES_USER', 'postgres')
    POSTGRES_PASSWORD = os.environ.get('POSTGRES_PASSWORD', 'password')
    POSTGRES_DB = os.environ.get('POSTGRES_DB', 'banksim')
    POSTGRES_HOST = os.environ.get('POSTGRES_HOST', 'localhost')
    POSTGRES_PORT = os.environ.get('POSTGRES_PORT', '5432')
    
    SQLALCHEMY_DATABASE_URI = f"postgresql://{POSTGRES_USER}:{POSTGRES_PASSWORD}@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Firebase Configuration
    FIREBASE_CREDENTIALS_PATH = os.environ.get('FIREBASE_CREDENTIALS', 'firebase-credentials.json')
    FIREBASE_PROJECT_ID = os.environ.get('FIREBASE_PROJECT_ID', 'dbms-banksim')
    FIREBASE_STORAGE_BUCKET = f"{FIREBASE_PROJECT_ID}.appspot.com"
