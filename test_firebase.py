import firebase_admin
from firebase_admin import credentials, firestore
import os

# Path to your JSON
cred_path = "firebase-credentials.json"

print("--- Starting Firebase Debug V2 ---")
cred = credentials.Certificate(cred_path)
firebase_admin.initialize_app(cred)

# 1. Try with (default) - using correct keyword 'database_id'
try:
    print("Test 1: Trying database_id='(default)'...")
    db1 = firestore.client(database_id='(default)')
    db1.collection('debug_test').add({'msg': 'Test (default)'})
    print("✅ SUCCESS with (default)!")
except Exception as e:
    print(f"❌ FAILED with (default): {str(e)}")

# 2. Try with default (no parentheses) - using correct keyword 'database_id'
try:
    print("\nTest 2: Trying database_id='default'...")
    db2 = firestore.client(database_id='default')
    db2.collection('debug_test').add({'msg': 'Test default'})
    print("✅ SUCCESS with 'default'!")
except Exception as e:
    print(f"❌ FAILED with 'default': {str(e)}")

print("\n--- Debug Finished ---")
