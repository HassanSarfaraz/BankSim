from pymongo import MongoClient
from datetime import datetime
import os

class AuditLogger:
    def __init__(self, mongo_url=None):
        url = mongo_url or os.environ.get('MONGO_URL', 'mongodb://mongoadmin:MongoPassword123@localhost:27017')
        self.client = MongoClient(url)
        self.db = self.client['securebank']
        self.logs = self.db['audit_logs']

    def log_event(self, user_id, action, status='success', details=None, ip_address=None):
        log_entry = {
            "user_id": user_id,
            "action": action,
            "status": status,
            "details": details or {},
            "ip_address": ip_address,
            "timestamp": datetime.utcnow()
        }
        try:
            self.logs.insert_one(log_entry)
            return True
        except Exception as e:
            print(f"Failed to log to MongoDB: {e}")
            return False

    def get_logs(self, filters=None, limit=100):
        query = filters or {}
        return list(self.logs.find(query).sort("timestamp", -1).limit(limit))

# Global instance
audit_logger = AuditLogger()
