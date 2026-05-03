from backend.app import db
from datetime import datetime

class Branch(db.Model):
    __tablename__ = 'branches'
    branch_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(100), nullable=False)
    address = db.Column(db.Text, nullable=False)
    phone = db.Column(db.String(20), unique=True, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    employees = db.relationship('Employee', backref='branch', lazy=True)
    accounts = db.relationship('Account', backref='branch', lazy=True)

class Customer(db.Model):
    __tablename__ = 'customers'
    customer_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True)
    cnic = db.Column(db.String(15), unique=True, nullable=False)
    full_name = db.Column(db.String(100), nullable=False)
    dob = db.Column(db.Date, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    phone = db.Column(db.String(20), nullable=False)
    address = db.Column(db.Text, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    accounts = db.relationship('Account', backref='customer', lazy=True)

class Employee(db.Model):
    __tablename__ = 'employees'
    employee_id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.user_id'), unique=True)
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.branch_id'))
    role = db.Column(db.String(50), nullable=False)
    salary = db.Column(db.Numeric(12, 2), default=0.00)
    hire_date = db.Column(db.Date, default=datetime.utcnow().date)

class Account(db.Model):
    __tablename__ = 'accounts'
    account_id = db.Column(db.Integer, primary_key=True)
    customer_id = db.Column(db.Integer, db.ForeignKey('customers.customer_id'))
    branch_id = db.Column(db.Integer, db.ForeignKey('branches.branch_id'))
    account_type = db.Column(db.String(20), nullable=False)
    balance = db.Column(db.Numeric(15, 2), default=0.00)
    status = db.Column(db.String(20), default='active')
    currency = db.Column(db.String(3), default='PKR')
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

    transactions_from = db.relationship('Transaction', foreign_keys='Transaction.from_account', backref='source_account', lazy=True)
    transactions_to = db.relationship('Transaction', foreign_keys='Transaction.to_account', backref='dest_account', lazy=True)
    loans = db.relationship('Loan', backref='account', lazy=True)
    cards = db.relationship('Card', backref='account', lazy=True)

class Transaction(db.Model):
    __tablename__ = 'transactions'
    txn_id = db.Column(db.Integer, primary_key=True)
    from_account = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    to_account = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    amount = db.Column(db.Numeric(15, 2), nullable=False)
    txn_type = db.Column(db.String(20), nullable=False)
    status = db.Column(db.String(20), default='completed')
    description = db.Column(db.Text)
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)

class Loan(db.Model):
    __tablename__ = 'loans'
    loan_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    loan_type = db.Column(db.String(50), nullable=False)
    principal_amount = db.Column(db.Numeric(15, 2), nullable=False)
    interest_rate = db.Column(db.Numeric(5, 2), nullable=False)
    term_months = db.Column(db.Integer, nullable=False)
    remaining_balance = db.Column(db.Numeric(15, 2), nullable=False)
    status = db.Column(db.String(20), default='pending')
    applied_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
    approved_at = db.Column(db.DateTime(timezone=True))

class Card(db.Model):
    __tablename__ = 'cards'
    card_id = db.Column(db.Integer, primary_key=True)
    account_id = db.Column(db.Integer, db.ForeignKey('accounts.account_id'))
    card_number = db.Column(db.String(16), unique=True, nullable=False)
    card_type = db.Column(db.String(20), nullable=False)
    expiry_date = db.Column(db.Date, nullable=False)
    cvv = db.Column(db.String(4), nullable=False)
    status = db.Column(db.String(20), default='active')
    created_at = db.Column(db.DateTime(timezone=True), default=datetime.utcnow)
