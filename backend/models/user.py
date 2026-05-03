from backend.extensions import db
from datetime import datetime
import bcrypt


class User(db.Model):
    __tablename__ = 'users'

    user_id       = db.Column(db.Integer, primary_key=True)
    username      = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    role          = db.Column(db.String(20), nullable=False)  # manager, accountant, customer
    is_active     = db.Column(db.Boolean, default=True)
    last_login    = db.Column(db.DateTime(timezone=True))
    created_at    = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    # Relationships
    customer = db.relationship('Customer', backref='user', uselist=False, lazy=True)
    employee = db.relationship('Employee', backref='user', uselist=False, lazy=True)

    def set_password(self, password):
        salt = bcrypt.gensalt(rounds=12)
        self.password_hash = bcrypt.hashpw(
            password.encode('utf-8'), salt
        ).decode('utf-8')

    def check_password(self, password):
        return bcrypt.checkpw(
            password.encode('utf-8'),
            self.password_hash.encode('utf-8')
        )

    def to_dict(self):
        return {
            "user_id":    self.user_id,
            "username":   self.username,
            "role":       self.role,
            "is_active":  self.is_active,
            "last_login": self.last_login.isoformat() if self.last_login else None,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }
