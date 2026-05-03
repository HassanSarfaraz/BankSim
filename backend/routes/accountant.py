from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.models.bank import Account, Transaction, Customer, Loan
from backend.mongo.audit import audit_logger
from datetime import datetime

accountant_bp = Blueprint('accountant', __name__)

@accountant_bp.route('/accounts', methods=['GET'])
@jwt_required()
def list_accounts():
    identity = get_jwt_identity()
    if identity['role'] not in ['accountant', 'manager']:
        return jsonify({"error": "Unauthorized"}), 403
    
    accounts = Account.query.all()
    return jsonify([
        {
            "account_id": a.account_id,
            "customer_name": a.customer.full_name,
            "account_type": a.account_type,
            "balance": float(a.balance),
            "status": a.status
        } for a in accounts
    ]), 200

@accountant_bp.route('/accounts', methods=['POST'])
@jwt_required()
def create_account():
    identity = get_jwt_identity()
    if identity['role'] != 'accountant':
        return jsonify({"error": "Unauthorized"}), 403
    
    data = request.get_json()
    new_account = Account(
        customer_id=data['customer_id'],
        branch_id=data['branch_id'],
        account_type=data['account_type'],
        balance=data.get('initial_deposit', 0),
        status='active'
    )
    db.session.add(new_account)
    db.session.commit()
    
    audit_logger.log_event(identity['user_id'], "create_account", "success", {
        "account_id": new_account.account_id, "customer_id": data['customer_id']
    }, request.remote_addr)
    
    return jsonify({"message": "Account created", "account_id": new_account.account_id}), 201

@accountant_bp.route('/transactions/deposit', methods=['POST'])
@jwt_required()
def deposit():
    identity = get_jwt_identity()
    data = request.get_json()
    
    txn = Transaction(
        to_account=data['account_id'],
        amount=data['amount'],
        txn_type='deposit',
        description=data.get('description', 'Cash Deposit')
    )
    db.session.add(txn)
    db.session.commit()
    
    audit_logger.log_event(identity['user_id'], "deposit", "success", {
        "account_id": data['account_id'], "amount": data['amount']
    }, request.remote_addr)
    
    return jsonify({"message": "Deposit successful"}), 200

@accountant_bp.route('/loans', methods=['GET'])
@jwt_required()
def list_loans():
    loans = Loan.query.all()
    return jsonify([
        {
            "loan_id": l.loan_id,
            "customer_name": l.account.customer.full_name,
            "amount": float(l.principal_amount),
            "status": l.status
        } for l in loans
    ]), 200
