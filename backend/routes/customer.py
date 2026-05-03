from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.models.bank import Account, Transaction, Customer
from backend.mongo.audit import audit_logger
from sqlalchemy import text

customer_bp = Blueprint('customer', __name__)

def get_customer_id(user_id):
    customer = Customer.query.filter_by(user_id=user_id).first()
    return customer.customer_id if customer else None

@customer_bp.route('/accounts', methods=['GET'])
@jwt_required()
def get_accounts():
    identity = get_jwt_identity()
    if identity['role'] != 'customer':
        return jsonify({"error": "Unauthorized"}), 403
    
    cust_id = get_customer_id(identity['user_id'])
    accounts = Account.query.filter_by(customer_id=cust_id).all()
    
    return jsonify([
        {
            "account_id": a.account_id,
            "account_type": a.account_type,
            "balance": float(a.balance),
            "status": a.status,
            "currency": a.currency
        } for a in accounts
    ]), 200

@customer_bp.route('/transfer', methods=['POST'])
@jwt_required()
def transfer():
    identity = get_jwt_identity()
    if identity['role'] != 'customer':
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    from_account_id = data.get('from_account')
    to_account_id = data.get('to_account')
    amount = data.get('amount')
    description = data.get('description', 'Transfer')

    cust_id = get_customer_id(identity['user_id'])
    
    # Verify the from_account belongs to this customer
    account = Account.query.filter_by(account_id=from_account_id, customer_id=cust_id).first()
    if not account:
        return jsonify({"error": "Invalid source account"}), 400

    try:
        # Call stored procedure
        db.session.execute(
            text("CALL sp_transfer(:from_acc, :to_acc, :amount, :desc)"),
            {"from_acc": from_account_id, "to_acc": to_account_id, "amount": amount, "desc": description}
        )
        db.session.commit()
        
        audit_logger.log_event(identity['user_id'], "transfer", "success", {
            "from": from_account_id, "to": to_account_id, "amount": amount
        }, request.remote_addr)
        
        return jsonify({"message": "Transfer successful"}), 200
    except Exception as e:
        db.session.rollback()
        audit_logger.log_event(identity['user_id'], "transfer", "failure", {
            "from": from_account_id, "to": to_account_id, "amount": amount, "error": str(e)
        }, request.remote_addr)
        return jsonify({"error": str(e)}), 400

@customer_bp.route('/transactions/<int:account_id>', methods=['GET'])
@jwt_required()
def get_transactions(account_id):
    identity = get_jwt_identity()
    cust_id = get_customer_id(identity['user_id'])
    
    # Verify ownership
    account = Account.query.filter_by(account_id=account_id, customer_id=cust_id).first()
    if not account:
        return jsonify({"error": "Unauthorized"}), 403
    
    txns = Transaction.query.filter(
        (Transaction.from_account == account_id) | (Transaction.to_account == account_id)
    ).order_by(Transaction.created_at.desc()).all()
    
    return jsonify([
        {
            "txn_id": t.txn_id,
            "from_account": t.from_account,
            "to_account": t.to_account,
            "amount": float(t.amount),
            "type": t.txn_type,
            "status": t.status,
            "description": t.description,
            "created_at": t.created_at.isoformat()
        } for t in txns
    ]), 200
