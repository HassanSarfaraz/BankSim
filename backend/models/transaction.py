from backend.extensions import db
from datetime import datetime


class Account(db.Model):
    __tablename__ = 'accounts'
    account_id  = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id', ondelete='CASCADE'))
    branch_id   = db.Column(db.Integer, db.ForeignKey('branches.branch_id'))
    type        = db.Column(db.String(20), nullable=False)
    balance     = db.Column(db.Numeric(15, 2), default=0)
    status      = db.Column(db.String(20), default='active')
    daily_limit = db.Column(db.Numeric(15, 2), default=50000)
    created_at  = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    transactions_from = db.relationship('Transaction', foreign_keys='Transaction.from_account', backref='source', lazy=True)
    transactions_to   = db.relationship('Transaction', foreign_keys='Transaction.to_account',   backref='destination', lazy=True)
    loans  = db.relationship('Loan', backref='account', lazy=True)
    cards  = db.relationship('Card', backref='account', lazy=True)

    def to_dict(self, include_customer=False):
        d = {
            "account_id": self.account_id,
            "customer_id": self.customer_id,
            "branch_id": self.branch_id,
            "type": self.type,
            "balance": float(self.balance),
            "status": self.status,
            "daily_limit": float(self.daily_limit),
            "created_at": self.created_at.isoformat() if self.created_at else None
        }
        if include_customer and self.customer:
            d["customer_name"] = self.customer.full_name
            d["cnic"] = self.customer.cnic
        if self.branch:
            d["branch_name"] = self.branch.name
        return d


class Transaction(db.Model):
    __tablename__ = 'transactions'
    txn_id       = db.Column(db.Integer, primary_key=True)
    from_account = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    to_account   = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    amount       = db.Column(db.Numeric(15, 2), nullable=False)
    txn_type     = db.Column(db.String(30), nullable=False)
    status       = db.Column(db.String(20), default='pending')
    description  = db.Column(db.Text)
    performed_by = db.Column(db.Integer, db.ForeignKey('users.user_id'))
    timestamp    = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        return {
            "txn_id": self.txn_id,
            "from_account": self.from_account,
            "to_account": self.to_account,
            "amount": float(self.amount),
            "txn_type": self.txn_type,
            "status": self.status,
            "description": self.description,
            "timestamp": self.timestamp.isoformat() if self.timestamp else None
        }
