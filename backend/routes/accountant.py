# ===========================================================================
# Accountant Routes — daily banking operations
# ===========================================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from backend.extensions import db
from backend.models.user import User
from backend.models.account import Customer, Employee
from backend.models.transaction import Account, Transaction
from backend.models.loan import Loan, Card
from backend.services.transfer import transfer_funds, cash_deposit, cash_withdrawal
from backend.mongo.audit import log_audit_event
from functools import wraps
import random, string, bcrypt
from datetime import date, timedelta, datetime

accountant_bp = Blueprint('accountant', __name__)


def staff_required(f):
    """Allow accountant or manager."""
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        role = get_jwt()['role']
        if role not in ('accountant', 'manager'):
            return jsonify({"success": False, "error": "Staff access required"}), 403
        return f(*args, **kwargs)
    return wrapper


# ---- Dashboard KPIs -------------------------------------------------------
@accountant_bp.route('/dashboard', methods=['GET'])
@staff_required
def dashboard():
    today_txns = Transaction.query.filter(
        db.cast(Transaction.timestamp, db.Date) == func.current_date()
    ).count()
    pending_loans = Loan.query.filter_by(status='pending').count()
    low_bal = Account.query.filter(Account.balance < 1000, Account.status == 'active').count()
    return jsonify({"success": True, "data": {
        "today_transactions": today_txns,
        "pending_loans": pending_loans,
        "low_balance_alerts": low_bal,
    }}), 200


# ---- Account Management ---------------------------------------------------
@accountant_bp.route('/accounts', methods=['GET'])
@staff_required
def list_accounts():
    accounts = Account.query.all()
    return jsonify({
        "success": True,
        "data": [a.to_dict(include_customer=True) for a in accounts]
    }), 200


@accountant_bp.route('/accounts', methods=['POST'])
@staff_required
def open_account():
    data = request.get_json() or {}
    for f in ['customer_id', 'branch_id', 'type']:
        if f not in data:
            return jsonify({"success": False, "error": f"Missing: {f}"}), 400

    if data['type'] not in ('savings', 'current', 'fixed_deposit'):
        return jsonify({"success": False, "error": "Invalid account type"}), 400

    initial = float(data.get('initial_deposit', 0))
    acc = Account(
        customer_id=data['customer_id'],
        branch_id=data['branch_id'],
        type=data['type'],
        balance=initial,
        daily_limit=data.get('daily_limit', 50000),
    )
    db.session.add(acc)
    db.session.flush()

    if initial > 0:
        txn = Transaction(
            to_account=acc.account_id,
            amount=initial,
            txn_type='deposit',
            status='completed',
            description='Initial deposit on account opening',
            performed_by=get_jwt()['user_id'],
        )
        db.session.add(txn)

    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'OPEN_ACCOUNT',
                    f"Opened {data['type']} account for customer #{data['customer_id']}")
    return jsonify({"success": True, "data": acc.to_dict(include_customer=True)}), 201


# ---- Transaction Processing -----------------------------------------------
@accountant_bp.route('/transactions/deposit', methods=['POST'])
@staff_required
def deposit():
    data = request.get_json() or {}
    account_id = data.get('account_id')
    amount = float(data.get('amount', 0))
    if not account_id or amount <= 0:
        return jsonify({"success": False, "error": "account_id and positive amount required"}), 400

    success, msg = cash_deposit(account_id, amount,
                                get_jwt()['user_id'],
                                data.get('description', 'Cash deposit'))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@accountant_bp.route('/transactions/withdrawal', methods=['POST'])
@staff_required
def withdrawal():
    data = request.get_json() or {}
    account_id = data.get('account_id')
    amount = float(data.get('amount', 0))
    if not account_id or amount <= 0:
        return jsonify({"success": False, "error": "account_id and positive amount required"}), 400

    success, msg = cash_withdrawal(account_id, amount,
                                   get_jwt()['user_id'],
                                   data.get('description', 'Cash withdrawal'))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@accountant_bp.route('/transactions/transfer', methods=['POST'])
@staff_required
def transfer():
    data = request.get_json() or {}
    from_acc = data.get('from_account')
    to_acc   = data.get('to_account')
    amount   = float(data.get('amount', 0))

    if not from_acc or not to_acc or amount <= 0:
        return jsonify({"success": False, "error": "from_account, to_account and amount required"}), 400

    success, msg, _ = transfer_funds(
        from_acc, to_acc, amount,
        get_jwt()['user_id'],
        data.get('description', 'Counter transfer')
    )
    return jsonify({"success": success, "message": msg}), 200 if success else 400


@accountant_bp.route('/transactions', methods=['GET'])
@staff_required
def list_transactions():
    account_id = request.args.get('account_id', type=int)
    limit = request.args.get('limit', 50, type=int)
    q = Transaction.query
    if account_id:
        q = q.filter((Transaction.from_account == account_id) | (Transaction.to_account == account_id))
    txns = q.order_by(Transaction.timestamp.desc()).limit(limit).all()
    return jsonify({"success": True, "data": [t.to_dict() for t in txns]}), 200


# ---- Loan Management -------------------------------------------------------
@accountant_bp.route('/loans', methods=['GET'])
@staff_required
def list_loans():
    status_filter = request.args.get('status')
    q = Loan.query
    if status_filter:
        q = q.filter_by(status=status_filter)
    loans = q.order_by(Loan.created_at.desc()).all()
    result = []
    for l in loans:
        d = l.to_dict()
        acc = db.session.get(Account, l.account_id)
        if acc and acc.customer:
            d['customer_name'] = acc.customer.full_name
        result.append(d)
    return jsonify({"success": True, "data": result}), 200


@accountant_bp.route('/loans', methods=['POST'])
@staff_required
def create_loan():
    data = request.get_json() or {}
    for f in ['account_id', 'loan_type', 'amount', 'interest_rate', 'term_months']:
        if f not in data:
            return jsonify({"success": False, "error": f"Missing: {f}"}), 400

    amount = float(data['amount'])
    rate   = float(data['interest_rate'])
    term   = int(data['term_months'])
    monthly = round(amount * (1 + rate/100) / term, 2)

    loan = Loan(
        account_id=data['account_id'],
        loan_type=data['loan_type'],
        amount=amount,
        interest_rate=rate,
        term_months=term,
        monthly_payment=monthly,
    )
    db.session.add(loan)
    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'CREATE_LOAN',
                    f"Loan of PKR {amount} for acc #{data['account_id']}")
    return jsonify({"success": True, "data": loan.to_dict()}), 201


# ---- Customer KYC ----------------------------------------------------------
@accountant_bp.route('/customers', methods=['GET'])
@staff_required
def list_customers():
    customers = Customer.query.all()
    return jsonify({"success": True, "data": [c.to_dict() for c in customers]}), 200


@accountant_bp.route('/customers/<int:cid>/kyc', methods=['PUT'])
@staff_required
def update_kyc(cid):
    data = request.get_json() or {}
    cust = db.session.get(Customer, cid)
    if not cust:
        return jsonify({"success": False, "error": "Customer not found"}), 404
    cust.kyc_status = data.get('status', 'verified')
    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'KYC_UPDATE',
                    f"Customer #{cid} KYC → {cust.kyc_status}")
    return jsonify({"success": True, "data": cust.to_dict()}), 200


# ---- Card Management -------------------------------------------------------
@accountant_bp.route('/cards', methods=['GET'])
@staff_required
def list_cards():
    cards = Card.query.all()
    return jsonify({"success": True, "data": [c.to_dict() for c in cards]}), 200


@accountant_bp.route('/cards', methods=['POST'])
@staff_required
def issue_card():
    data = request.get_json() or {}
    if 'account_id' not in data:
        return jsonify({"success": False, "error": "account_id required"}), 400

    card_num = ''.join(random.choices(string.digits, k=16))
    cvv = ''.join(random.choices(string.digits, k=3))
    card = Card(
        account_id=data['account_id'],
        card_number=card_num,
        card_type=data.get('card_type', 'debit'),
        expiry_date=date.today() + timedelta(days=1460),
        cvv_hash=bcrypt.hashpw(cvv.encode(), bcrypt.gensalt()).decode(),
        credit_limit=data.get('credit_limit', 0),
    )
    db.session.add(card)
    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'ISSUE_CARD',
                    f"Card ****{card_num[-4:]} for acc #{data['account_id']}")
    return jsonify({"success": True, "data": card.to_dict(), "cvv": cvv}), 201


@accountant_bp.route('/cards/<int:cid>/toggle', methods=['PUT'])
@staff_required
def toggle_card(cid):
    card = db.session.get(Card, cid)
    if not card:
        return jsonify({"success": False, "error": "Card not found"}), 404
    card.status = 'blocked' if card.status == 'active' else 'active'
    db.session.commit()
    return jsonify({"success": True, "data": card.to_dict()}), 200
