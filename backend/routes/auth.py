from flask import Blueprint, request, jsonify
from flask_jwt_extended import create_access_token, jwt_required, get_jwt_identity
import bcrypt
from backend.models.user import User
from backend.app import db
from backend.mongo.audit import audit_logger
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    username = data.get('username')
    password = data.get('password')

    if not username or not password:
        return jsonify({"error": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()

    if user and bcrypt.checkpw(password.encode('utf-8'), user.password_hash.encode('utf-8')):
        if not user.is_active:
            return jsonify({"error": "Account is deactivated"}), 403
        
        user.last_login = datetime.utcnow()
        db.session.commit()

        audit_logger.log_event(user.user_id, "login", "success", {"username": username}, request.remote_addr)

        access_token = create_access_token(identity={"user_id": user.user_id, "role": user.role})
        return jsonify({
            "token": access_token,
            "role": user.role,
            "user": user.to_dict()
        }), 200

    audit_logger.log_event(None, "login", "failure", {"username": username, "reason": "Invalid credentials"}, request.remote_addr)
    return jsonify({"error": "Invalid credentials"}), 401

@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_current_user():
    identity = get_jwt_identity()
    user = User.query.get(identity['user_id'])
    if user:
        return jsonify(user.to_dict()), 200
    return jsonify({"error": "User not found"}), 404
