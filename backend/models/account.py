from backend.extensions import db
from datetime import datetime, date
from decimal import Decimal


class Branch(db.Model):
    __tablename__ = 'branches'
    branch_id  = db.Column(db.Integer, primary_key=True)
    name       = db.Column(db.String(100), nullable=False)
    city       = db.Column(db.String(50), nullable=False)
    address    = db.Column(db.Text, nullable=False)
    phone      = db.Column(db.String(20))
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    employees = db.relationship('Employee', backref='branch', lazy=True)
    accounts  = db.relationship('Account',  backref='branch', lazy=True)

    def to_dict(self):
        return {
            "branch_id": self.branch_id,
            "name": self.name,
            "city": self.city,
            "address": self.address,
            "phone": self.phone,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True)
    cnic        = db.Column(db.String(15), unique=True, nullable=False)
    full_name   = db.Column(db.String(100), nullable=False)
    dob         = db.Column(db.Date, nullable=False)
    address     = db.Column(db.Text)
    phone       = db.Column(db.String(20))
    email       = db.Column(db.String(100), unique=True)
    kyc_status  = db.Column(db.String(20), default='pending')
    created_at  = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    accounts = db.relationship('Account', backref='customer', lazy=True)

    def to_dict(self):
        return {
            "customer_id": self.customer_id,
            "user_id": self.user_id,
            "cnic": self.cnic,
            "full_name": self.full_name,
            "dob": self.dob.isoformat() if self.dob else None,
            "address": self.address,
            "phone": self.phone,
            "email": self.email,
            "kyc_status": self.kyc_status,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }


class Employee(db.Model):
    __tablename__ = 'employees'
    employee_id = db.Column(db.Integer, primary_key=True)
    user_id     = db.Column(db.Integer, db.ForeignKey('users.user_id', ondelete='CASCADE'), unique=True)
    branch_id   = db.Column(db.Integer, db.ForeignKey('branches.branch_id'))
    full_name   = db.Column(db.String(100), nullable=False)
    designation = db.Column(db.String(50), nullable=False)
    is_active   = db.Column(db.Boolean, default=True)
    created_at  = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    def to_dict(self):
        return {
            "employee_id": self.employee_id,
            "user_id": self.user_id,
            "branch_id": self.branch_id,
            "full_name": self.full_name,
            "designation": self.designation,
            "is_active": self.is_active,
            "branch_name": self.branch.name if self.branch else None
        }


class AuditPolicy(db.Model):
    __tablename__ = 'audit_policies'
    policy_id              = db.Column(db.Integer, primary_key=True)
    acc_type               = db.Column(db.String(20), unique=True, nullable=False)
    daily_withdrawal_limit = db.Column(db.Numeric(15, 2), nullable=False)
    overdraft_allowed      = db.Column(db.Boolean, default=False)
    min_balance            = db.Column(db.Numeric(15, 2), default=0)
    interest_rate          = db.Column(db.Numeric(5, 2), default=0)

    def to_dict(self):
        return {
            "acc_type": self.acc_type,
            "daily_withdrawal_limit": float(self.daily_withdrawal_limit),
            "overdraft_allowed": self.overdraft_allowed,
            "min_balance": float(self.min_balance),
            "interest_rate": float(self.interest_rate)
        }
