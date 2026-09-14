from functools import wraps
from flask import jsonify
from flask_jwt_extended import get_jwt_identity, verify_jwt_in_request
from app.extensions import db          # ← 新增
from app.models import User


def get_current_user():
    uid = get_jwt_identity()
    return db.session.get(User, int(uid)) if uid else None    # ← 改这行


def require_role(*role_names):
    """要求当前用户具备指定角色之一，需先登录"""
    def wrapper(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            verify_jwt_in_request()
            user = get_current_user()
            if not user:
                return jsonify({"error": "user not found"}), 401
            if not any(user.has_role(r) for r in role_names):
                return jsonify({"error": "permission denied"}), 403
            return fn(*args, **kwargs)
        return inner
    return wrapper