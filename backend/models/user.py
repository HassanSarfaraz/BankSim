from backend.app import db
from datetime import datetime

class User(db.Model):
    __tablename__ = 'users'
    
    user_id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.Text, nullable=False)
    role = db.Column(db.String(20), nullable=False)
    last_login = db.Column(db.DateTime(timezone=True))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        return {
            "user_id": self.user_id,
            "username": self.username,
            "role": self.role,
            "is_active": self.is_active
        }
