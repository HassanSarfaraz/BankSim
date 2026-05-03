# ===========================================================================
# Customer Routes — self-service banking
# ===========================================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import or_
from backend.extensions import db
from backend.models.user import User
from backend.models.account import Customer
from backend.models.transaction import Account, Transaction
from backend.models.loan import Loan, Card
from backend.services.transfer import transfer_funds
from backend.mongo.audit import log_audit_event
from functools import wraps

customer_bp = Blueprint('customer', __name__)


def customer_required(f):
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt()['role'] != 'customer':
            return jsonify({"success": False, "error": "Customer access required"}), 403
        return f(*args, **kwargs)
    return wrapper


def _get_customer():
    """Return Customer object for the logged-in user."""
    uid = get_jwt()['user_id']
    return Customer.query.filter_by(user_id=uid).first()


# ---- My Accounts -----------------------------------------------------------
@customer_bp.route('/accounts', methods=['GET'])
@customer_required
def my_accounts():
    cust = _get_customer()
    if not cust:
        return jsonify({"success": False, "error": "Customer profile not found"}), 404
    accounts = Account.query.filter_by(customer_id=cust.customer_id).all()
    return jsonify({
        "success": True,
        "data": [a.to_dict() for a in accounts]
    }), 200


# ---- My Transactions -------------------------------------------------------
@customer_bp.route('/transactions', methods=['GET'])
@customer_required
def my_transactions():
    cust = _get_customer()
    if not cust:
        return jsonify({"success": False, "error": "Not found"}), 404

    account_id = request.args.get('account_id', type=int)
    limit = request.args.get('limit', 50, type=int)

    # Get all account IDs belonging to this customer
    my_accs = [a.account_id for a in Account.query.filter_by(customer_id=cust.customer_id).all()]
    if not my_accs:
        return jsonify({"success": True, "data": []}), 200

    q = Transaction.query.filter(
        or_(Transaction.from_account.in_(my_accs),
            Transaction.to_account.in_(my_accs))
    )
    if account_id and account_id in my_accs:
        q = Transaction.query.filter(
            or_(Transaction.from_account == account_id,
                Transaction.to_account == account_id)
        )

    txns = q.order_by(Transaction.timestamp.desc()).limit(limit).all()
    return jsonify({"success": True, "data": [t.to_dict() for t in txns]}), 200


# ---- Fund Transfer ---------------------------------------------------------
@customer_bp.route('/transfer', methods=['POST'])
@customer_required
def self_transfer():
    data = request.get_json() or {}
    from_acc = data.get('from_account')
    to_acc   = data.get('to_account')
    amount   = float(data.get('amount', 0))

    if not from_acc or not to_acc or amount <= 0:
        return jsonify({"success": False, "error": "Provide from_account, to_account, and amount"}), 400

    # Verify ownership of source account
    cust = _get_customer()
    src = Account.query.filter_by(account_id=from_acc, customer_id=cust.customer_id).first()
    if not src:
        return jsonify({"success": False, "error": "Source account does not belong to you"}), 403

    uid = get_jwt()['user_id']
    success, msg, _ = transfer_funds(from_acc, to_acc, amount, uid,
                                     data.get('description', 'Online transfer'))
    return jsonify({"success": success, "message": msg}), 200 if success else 400


# ---- Apply for Loan --------------------------------------------------------
@customer_bp.route('/loans/apply', methods=['POST'])
@customer_required
def apply_loan():
    data = request.get_json() or {}
    for f in ['account_id', 'loan_type', 'amount', 'term_months']:
        if f not in data:
            return jsonify({"success": False, "error": f"Missing: {f}"}), 400

    cust = _get_customer()
    acc = Account.query.filter_by(account_id=data['account_id'],
                                  customer_id=cust.customer_id).first()
    if not acc:
        return jsonify({"success": False, "error": "Account not found or not yours"}), 403

    amount = float(data['amount'])
    term   = int(data['term_months'])
    rate   = float(data.get('interest_rate', 12.0))
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

    log_audit_event(get_jwt()['user_id'], 'LOAN_APPLICATION',
                    f"Applied for {data['loan_type']} loan of PKR {amount}")
    return jsonify({"success": True, "data": loan.to_dict()}), 201


# ---- My Loans --------------------------------------------------------------
@customer_bp.route('/loans', methods=['GET'])
@customer_required
def my_loans():
    cust = _get_customer()
    if not cust:
        return jsonify({"success": True, "data": []}), 200
    my_accs = [a.account_id for a in Account.query.filter_by(customer_id=cust.customer_id).all()]
    loans = Loan.query.filter(Loan.account_id.in_(my_accs)).all()
    return jsonify({"success": True, "data": [l.to_dict() for l in loans]}), 200


# ---- My Cards --------------------------------------------------------------
@customer_bp.route('/cards', methods=['GET'])
@customer_required
def my_cards():
    cust = _get_customer()
    if not cust:
        return jsonify({"success": True, "data": []}), 200
    my_accs = [a.account_id for a in Account.query.filter_by(customer_id=cust.customer_id).all()]
    cards = Card.query.filter(Card.account_id.in_(my_accs)).all()
    return jsonify({"success": True, "data": [c.to_dict() for c in cards]}), 200


# ---- Profile ---------------------------------------------------------------
@customer_bp.route('/profile', methods=['GET'])
@customer_required
def my_profile():
    cust = _get_customer()
    if not cust:
        return jsonify({"success": False, "error": "Not found"}), 404
    return jsonify({"success": True, "data": cust.to_dict()}), 200


@customer_bp.route('/profile', methods=['PUT'])
@customer_required
def update_profile():
    data = request.get_json() or {}
    cust = _get_customer()
    if not cust:
        return jsonify({"success": False, "error": "Not found"}), 404
    if 'phone' in data:
        cust.phone = data['phone']
    if 'email' in data:
        cust.email = data['email']
    if 'address' in data:
        cust.address = data['address']
    db.session.commit()
    return jsonify({"success": True, "data": cust.to_dict()}), 200


@customer_bp.route('/password', methods=['PUT'])
@customer_required
def change_password():
    data = request.get_json() or {}
    old_pw = data.get('old_password', '')
    new_pw = data.get('new_password', '')
    if not old_pw or not new_pw:
        return jsonify({"success": False, "error": "Both old and new passwords required"}), 400

    user = db.session.get(User, get_jwt()['user_id'])
    if not user.check_password(old_pw):
        return jsonify({"success": False, "error": "Current password is incorrect"}), 401

    user.set_password(new_pw)
    db.session.commit()
    log_audit_event(user.user_id, 'PASSWORD_CHANGE', 'Password changed')
    return jsonify({"success": True, "message": "Password changed successfully"}), 200
