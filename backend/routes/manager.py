# ===========================================================================
# Manager Routes — full system control endpoints
# ===========================================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt
from sqlalchemy import func
from backend.extensions import db
from backend.models.user import User
from backend.models.account import Branch, Customer, Employee, AuditPolicy
from backend.models.transaction import Account, Transaction
from backend.models.loan import Loan, Card
from backend.mongo.audit import log_audit_event, get_audit_logs
from functools import wraps

manager_bp = Blueprint('manager', __name__)


def manager_required(f):
    """Decorator: reject non-manager callers."""
    @wraps(f)
    @jwt_required()
    def wrapper(*args, **kwargs):
        if get_jwt()['role'] != 'manager':
            return jsonify({"success": False, "error": "Manager access required"}), 403
        return f(*args, **kwargs)
    return wrapper


# ---- Dashboard KPIs -------------------------------------------------------
@manager_bp.route('/dashboard', methods=['GET'])
@manager_required
def dashboard():
    total_assets  = db.session.query(func.coalesce(func.sum(Account.balance), 0)).scalar()
    active_accts  = Account.query.filter_by(status='active').count()
    loan_portfolio = db.session.query(func.coalesce(func.sum(Loan.amount), 0)).filter(Loan.status.in_(['active', 'approved'])).scalar()
    today_volume  = db.session.query(func.coalesce(func.sum(Transaction.amount), 0)).filter(
        db.cast(Transaction.timestamp, db.Date) == func.current_date()
    ).scalar()

    return jsonify({
        "success": True,
        "data": {
            "total_assets": float(total_assets),
            "active_accounts": active_accts,
            "loan_portfolio": float(loan_portfolio),
            "daily_volume": float(today_volume),
            "total_customers": Customer.query.count(),
            "total_branches": Branch.query.count(),
        }
    }), 200


# ---- Employee Management ---------------------------------------------------
@manager_bp.route('/employees', methods=['GET'])
@manager_required
def list_employees():
    employees = Employee.query.all()
    return jsonify({"success": True, "data": [e.to_dict() for e in employees]}), 200


@manager_bp.route('/employees', methods=['POST'])
@manager_required
def create_employee():
    data = request.get_json() or {}
    required = ['username', 'password', 'full_name', 'designation', 'branch_id']
    for field in required:
        if field not in data:
            return jsonify({"success": False, "error": f"Missing: {field}"}), 400

    if User.query.filter_by(username=data['username']).first():
        return jsonify({"success": False, "error": "Username already exists"}), 409

    user = User(username=data['username'], role='accountant')
    user.set_password(data['password'])
    db.session.add(user)
    db.session.flush()

    emp = Employee(
        user_id=user.user_id,
        branch_id=data['branch_id'],
        full_name=data['full_name'],
        designation=data['designation']
    )
    db.session.add(emp)
    db.session.commit()

    log_audit_event(get_jwt()['user_id'], 'CREATE_EMPLOYEE',
                    f"Created employee {data['full_name']}")

    return jsonify({"success": True, "data": emp.to_dict()}), 201


@manager_bp.route('/employees/<int:eid>/toggle', methods=['PUT'])
@manager_required
def toggle_employee(eid):
    emp = db.session.get(Employee, eid)
    if not emp:
        return jsonify({"success": False, "error": "Employee not found"}), 404
    emp.is_active = not emp.is_active
    user = db.session.get(User, emp.user_id)
    if user:
        user.is_active = emp.is_active
    db.session.commit()
    action = 'ACTIVATE_EMPLOYEE' if emp.is_active else 'DEACTIVATE_EMPLOYEE'
    log_audit_event(get_jwt()['user_id'], action, f"Employee #{eid}")
    return jsonify({"success": True, "data": emp.to_dict()}), 200


# ---- Branch Management -----------------------------------------------------
@manager_bp.route('/branches', methods=['GET'])
@manager_required
def list_branches():
    branches = Branch.query.all()
    result = []
    for b in branches:
        d = b.to_dict()
        d['total_accounts'] = Account.query.filter_by(branch_id=b.branch_id).count()
        d['total_deposits'] = float(
            db.session.query(func.coalesce(func.sum(Account.balance), 0))
            .filter(Account.branch_id == b.branch_id).scalar()
        )
        result.append(d)
    return jsonify({"success": True, "data": result}), 200


@manager_bp.route('/branches', methods=['POST'])
@manager_required
def create_branch():
    data = request.get_json() or {}
    for f in ['name', 'city', 'address']:
        if f not in data:
            return jsonify({"success": False, "error": f"Missing: {f}"}), 400
    b = Branch(name=data['name'], city=data['city'],
               address=data['address'], phone=data.get('phone', ''))
    db.session.add(b)
    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'CREATE_BRANCH', f"Branch: {data['name']}")
    return jsonify({"success": True, "data": b.to_dict()}), 201


# ---- Customer Oversight ----------------------------------------------------
@manager_bp.route('/customers', methods=['GET'])
@manager_required
def list_customers():
    customers = Customer.query.all()
    return jsonify({"success": True, "data": [c.to_dict() for c in customers]}), 200


@manager_bp.route('/accounts/<int:aid>/freeze', methods=['PUT'])
@manager_required
def toggle_freeze(aid):
    acc = db.session.get(Account, aid)
    if not acc:
        return jsonify({"success": False, "error": "Account not found"}), 404
    acc.status = 'frozen' if acc.status == 'active' else 'active'
    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'ACCOUNT_STATUS',
                    f"Account #{aid} → {acc.status}")
    return jsonify({"success": True, "data": acc.to_dict(include_customer=True)}), 200


# ---- Loan Approvals --------------------------------------------------------
@manager_bp.route('/loans/pending', methods=['GET'])
@manager_required
def pending_loans():
    loans = Loan.query.filter_by(status='pending').all()
    result = []
    for l in loans:
        d = l.to_dict()
        acc = db.session.get(Account, l.account_id)
        if acc and acc.customer:
            d['customer_name'] = acc.customer.full_name
        result.append(d)
    return jsonify({"success": True, "data": result}), 200


@manager_bp.route('/loans/<int:lid>/decide', methods=['PUT'])
@manager_required
def decide_loan(lid):
    data = request.get_json() or {}
    decision = data.get('decision')  # 'approve' or 'reject'
    reason   = data.get('reason', '')

    if decision not in ('approve', 'reject'):
        return jsonify({"success": False, "error": "decision must be approve or reject"}), 400
    if not reason:
        return jsonify({"success": False, "error": "Reason is required"}), 400

    loan = db.session.get(Loan, lid)
    if not loan or loan.status != 'pending':
        return jsonify({"success": False, "error": "Loan not found or already decided"}), 404

    identity = get_jwt()
    emp = Employee.query.filter_by(user_id=identity['user_id']).first()

    if decision == 'approve':
        loan.status = 'active'
        loan.approved_by = emp.employee_id if emp else None
        from datetime import datetime
        loan.approval_date = datetime.utcnow()
    else:
        loan.status = 'rejected'

    loan.reason = reason
    db.session.commit()

    log_audit_event(identity['user_id'], 'LOAN_DECISION',
                    f"Loan #{lid} {decision}d — {reason}")
    return jsonify({"success": True, "data": loan.to_dict()}), 200


# ---- System Configuration --------------------------------------------------
@manager_bp.route('/policies', methods=['GET'])
@manager_required
def get_policies():
    policies = AuditPolicy.query.all()
    return jsonify({"success": True, "data": [p.to_dict() for p in policies]}), 200


@manager_bp.route('/policies/<acc_type>', methods=['PUT'])
@manager_required
def update_policy(acc_type):
    data = request.get_json() or {}
    policy = AuditPolicy.query.filter_by(acc_type=acc_type).first()
    if not policy:
        return jsonify({"success": False, "error": "Policy not found"}), 404
    if 'daily_withdrawal_limit' in data:
        policy.daily_withdrawal_limit = data['daily_withdrawal_limit']
    if 'interest_rate' in data:
        policy.interest_rate = data['interest_rate']
    if 'min_balance' in data:
        policy.min_balance = data['min_balance']
    db.session.commit()
    log_audit_event(get_jwt()['user_id'], 'UPDATE_POLICY', f"Policy {acc_type} updated")
    return jsonify({"success": True, "data": policy.to_dict()}), 200


# ---- Audit Logs (from MongoDB) --------------------------------------------
@manager_bp.route('/audit', methods=['GET'])
@manager_required
def audit_logs():
    user_id = request.args.get('user_id', type=int)
    action  = request.args.get('action')
    limit   = request.args.get('limit', 200, type=int)
    logs = get_audit_logs(user_id=user_id, action=action, limit=limit)
    return jsonify({"success": True, "data": logs}), 200
