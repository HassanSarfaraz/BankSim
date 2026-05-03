# ===========================================================================
# Auth Routes — POST /api/auth/login · POST /api/auth/register (manager only)
# ===========================================================================
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, jwt_required, get_jwt
)
from backend.extensions import db
from backend.models.user import User
from backend.mongo.audit import log_audit_event
from datetime import datetime

auth_bp = Blueprint('auth', __name__)


@auth_bp.route('/login', methods=['POST'])
def login():
    """Authenticate user, return JWT + role."""
    data = request.get_json() or {}
    username = data.get('username', '').strip()
    password = data.get('password', '')

    if not username or not password:
        return jsonify({"success": False, "error": "Username and password required"}), 400

    user = User.query.filter_by(username=username).first()

    if not user or not user.is_active:
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    if not user.check_password(password):
        return jsonify({"success": False, "error": "Invalid credentials"}), 401

    # Update last_login
    user.last_login = datetime.utcnow()
    db.session.commit()

    token = create_access_token(
        identity=str(user.user_id),
        additional_claims={"user_id": user.user_id, "role": user.role}
    )

    log_audit_event(user.user_id, 'LOGIN',
                    f"User {username} logged in",
                    ip=request.remote_addr)

    return jsonify({
        "success": True,
        "token": token,
        "user": user.to_dict()
    }), 200


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    """Return current user info from JWT."""
    identity = get_jwt()
    user = db.session.get(User, identity['user_id'])
    if not user:
        return jsonify({"error": "User not found"}), 404
    return jsonify({"success": True, "user": user.to_dict()}), 200
