import firebase_admin
from firebase_admin import credentials, firestore, storage
import os

db_firestore = None
bucket = None

def init_firebase(app):
    global db_firestore, bucket
    cred_path = app.config['FIREBASE_CREDENTIALS_PATH']
    
    if os.path.exists(cred_path):
        cred = credentials.Certificate(cred_path)
        # Initialize without explicit project_id (it's inside the cred)
        firebase_admin.initialize_app(cred, {
            'storageBucket': app.config['FIREBASE_STORAGE_BUCKET']
        })
        # Force the database_id to 'default' as confirmed by the debug script
        db_firestore = firestore.client(database_id='default')
        bucket = storage.bucket()
        print("Firebase initialized successfully.")
    else:
        print(f"WARNING: Firebase credentials not found at {cred_path}. Cloud features will be disabled.")

def upload_to_firebase(file_bytes, filename, user_id):
    if bucket is None:
        return None
    path = f"users/{user_id}/{filename}"
    blob = bucket.blob(path)
    blob.upload_from_string(file_bytes)
    return path

def sync_doc_to_firestore(collection_name, doc_id, data):
    if db_firestore is None:
        return
    db_firestore.collection(collection_name).document(str(doc_id)).set(data)
