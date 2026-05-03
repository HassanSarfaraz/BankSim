from backend.extensions import db
from datetime import datetime


class Loan(db.Model):
    __tablename__ = 'loans'
    loan_id         = db.Column(db.Integer, primary_key=True)
    account_id      = db.Column(db.Integer, db.ForeignKey('accounts.account_id', ondelete='CASCADE'))
    loan_type       = db.Column(db.String(20), nullable=False)
    amount          = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate   = db.Column(db.Numeric(5, 2), nullable=False)
    term_months     = db.Column(db.Integer, nullable=False)
    monthly_payment = db.Column(db.Numeric(15, 2))
    amount_paid     = db.Column(db.Numeric(15, 2), default=0)
    status          = db.Column(db.String(20), default='pending')
    approved_by     = db.Column(db.Integer, db.ForeignKey('employees.employee_id'))
    approval_date   = db.Column(db.DateTime(timezone=True))
    reason          = db.Column(db.Text)
    created_at      = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        remaining = float(self.amount) - float(self.amount_paid or 0)
        return {
            "loan_id": self.loan_id,
            "account_id": self.account_id,
            "loan_type": self.loan_type,
            "amount": float(self.amount),
            "interest_rate": float(self.interest_rate),
            "term_months": self.term_months,
            "monthly_payment": float(self.monthly_payment or 0),
            "amount_paid": float(self.amount_paid or 0),
            "amount_remaining": round(remaining, 2),
            "status": self.status,
            "reason": self.reason,
            "approval_date": self.approval_date.isoformat() if self.approval_date else None,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Card(db.Model):
    __tablename__ = 'cards'
    card_id      = db.Column(db.Integer, primary_key=True)
    account_id   = db.Column(db.Integer, db.ForeignKey('accounts.account_id', ondelete='CASCADE'))
    card_number  = db.Column(db.String(16), unique=True, nullable=False)
    card_type    = db.Column(db.String(10), nullable=False)
    expiry_date  = db.Column(db.Date)
    cvv_hash     = db.Column(db.String(255), nullable=False)
    status       = db.Column(db.String(20), default='active')
    credit_limit = db.Column(db.Numeric(15, 2), default=0)
    created_at   = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        masked = f"**** **** **** {self.card_number[-4:]}" if self.card_number else "N/A"
        return {
            "card_id": self.card_id,
            "account_id": self.account_id,
            "card_number_masked": masked,
            "card_type": self.card_type,
            "expiry_date": self.expiry_date.isoformat() if self.expiry_date else None,
            "status": self.status,
            "credit_limit": float(self.credit_limit)
        }
