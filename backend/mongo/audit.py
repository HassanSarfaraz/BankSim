"""
MongoDB Audit Module - SecureBank
All audit events are written asynchronously so they never block Flask requests.
"""
import os, threading
from datetime import datetime
from pymongo import MongoClient, ASCENDING
from pymongo.errors import ConnectionFailure

_client = None
_db     = None

def _get_db():
    global _client, _db
    if _db is None:
        uri = os.environ.get('MONGO_URI', 'mongodb://localhost:27017/securebank_audit')
        _client = MongoClient(uri, serverSelectionTimeoutMS=3000)
        _db = _client.get_default_database()
        # Ensure indexes
        _db.audit_logs.create_index([("user_id", ASCENDING), ("timestamp", ASCENDING)])
        _db.audit_logs.create_index([("action", ASCENDING)])
        _db.statements.create_index([("account_id", ASCENDING), ("month", ASCENDING)])
    return _db


def _write_async(doc: dict, collection: str = 'audit_logs'):
    """Fire-and-forget MongoDB write in a background thread."""
    def _do():
        try:
            db = _get_db()
            db[collection].insert_one(doc)
        except Exception as e:
            print(f"[MongoDB] Write failed ({collection}): {e}")
    threading.Thread(target=_do, daemon=True).start()


def log_audit_event(user_id: int, action: str, details: str, ip: str = None, extra: dict = None):
    """Log any user action to MongoDB audit_logs collection."""
    doc = {
        "user_id": user_id,
        "action": action,
        "details": details,
        "ip": ip,
        "timestamp": datetime.utcnow()
    }
    if extra:
        doc.update(extra)
    _write_async(doc, 'audit_logs')


def store_statement(account_id: int, month: str, transactions: list):
    """Persist a monthly statement JSON document to MongoDB."""
    doc = {
        "account_id": account_id,
        "month": month,
        "generated_at": datetime.utcnow(),
        "transactions": transactions
    }
    _write_async(doc, 'statements')


def get_audit_logs(user_id: int = None, action: str = None, limit: int = 100) -> list:
    """Synchronously fetch audit logs (used by Manager Audit Log Viewer)."""
    try:
        db = _get_db()
        query = {}
        if user_id:
            query["user_id"] = user_id
        if action:
            query["action"] = action
        docs = list(db.audit_logs.find(query, {"_id": 0}).sort("timestamp", -1).limit(limit))
        # Convert datetimes to strings for JSON serialisation
        for d in docs:
            if "timestamp" in d:
                d["timestamp"] = d["timestamp"].isoformat()
        return docs
    except Exception as e:
        print(f"[MongoDB] Read failed: {e}")
        return []
