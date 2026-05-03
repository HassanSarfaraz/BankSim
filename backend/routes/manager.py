from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from backend.app import db
from backend.models.bank import Branch, Employee, Account, Transaction
from backend.mongo.audit import audit_logger
from sqlalchemy import text, func

manager_bp = Blueprint('manager', __name__)

@manager_bp.route('/dashboard', methods=['GET'])
@jwt_required()
def get_dashboard_stats():
    identity = get_jwt_identity()
    if identity['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403
    
    total_assets = db.session.query(func.sum(Account.balance)).scalar() or 0
    total_customers = db.session.query(func.count(Account.customer_id.distinct())).scalar()
    total_txns = db.session.query(func.count(Transaction.txn_id)).scalar()
    
    return jsonify({
        "total_assets": float(total_assets),
        "total_customers": total_customers,
        "total_transactions": total_txns
    }), 200

@manager_bp.route('/audit-logs', methods=['GET'])
@jwt_required()
def get_audit_logs():
    identity = get_jwt_identity()
    if identity['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403
    
    limit = request.args.get('limit', 50, type=int)
    logs = audit_logger.get_logs(limit=limit)
    
    # Convert ObjectId to string for JSON serialization
    for log in logs:
        log['_id'] = str(log['_id'])
        log['timestamp'] = log['timestamp'].isoformat()
        
    return jsonify(logs), 200

@manager_bp.route('/reports/branch-performance', methods=['GET'])
@jwt_required()
def get_branch_performance():
    identity = get_jwt_identity()
    if identity['role'] != 'manager':
        return jsonify({"error": "Unauthorized"}), 403
    
    result = db.session.execute(text("SELECT * FROM v_branch_performance"))
    performance = [dict(row._mapping) for row in result]
    
    # Convert Decimal to float for JSON
    for p in performance:
        if p['total_deposits']:
            p['total_deposits'] = float(p['total_deposits'])
            
    return jsonify(performance), 200
