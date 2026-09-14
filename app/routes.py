import uuid
from flask import Blueprint, request, jsonify
from flask_jwt_extended import (
    create_access_token, create_refresh_token,
    jwt_required, get_jwt_identity,
)

from app.extensions import db
from app.models import User, Role, EncryptTask
from app.utils.idempotent import try_acquire
from app.utils.auth import require_role
from app.celery_tasks.normal_tasks import encrypt_and_save, high_priority_demo

from app.schemas import (
    RegisterSchema, LoginSchema, UserSchema,
    EncryptSubmitSchema, EncryptTaskSchema, TaskListQuerySchema,
)

api_bp = Blueprint("api", __name__)

# 实例化 schema
register_schema = RegisterSchema()
login_schema = LoginSchema()
user_schema = UserSchema()
encrypt_submit_schema = EncryptSubmitSchema()
encrypt_task_schema = EncryptTaskSchema()
encrypt_tasks_schema = EncryptTaskSchema(many=True)
task_list_query_schema = TaskListQuerySchema()


# ==================== 认证 ====================
@api_bp.route("/auth/register", methods=["POST"])
def register():
    data = register_schema.load(request.get_json() or {})     # ← 校验 + 默认值

    if User.query.filter_by(username=data["username"]).first():
        return jsonify({"error": "username exists"}), 409

    user = User(username=data["username"])
    user.set_password(data["password"])

    default_role_name = "admin" if User.query.count() == 0 else "user"
    role = Role.query.filter_by(name=default_role_name).first()
    if not role:
        role = Role(name=default_role_name)
        db.session.add(role)
    user.roles.append(role)

    db.session.add(user)
    db.session.commit()
    return jsonify(user_schema.dump(user)), 201                # ← 序列化


@api_bp.route("/auth/login", methods=["POST"])
def login():
    data = login_schema.load(request.get_json() or {})
    user = User.query.filter_by(username=data["username"]).first()
    if not user or not user.check_password(data["password"]):
        return jsonify({"error": "bad credentials"}), 401

    return jsonify({
        "access_token": create_access_token(identity=str(user.id)),
        "refresh_token": create_refresh_token(identity=str(user.id)),
        "user": user_schema.dump(user),
    })


@api_bp.route("/auth/refresh", methods=["POST"])
@jwt_required(refresh=True)
def refresh():
    uid = get_jwt_identity()
    return jsonify({"access_token": create_access_token(identity=uid)})


@api_bp.route("/auth/me", methods=["GET"])
@jwt_required()
def me():
    uid = get_jwt_identity()
    user = db.session.get(User, int(uid))
    if not user:
        return jsonify({"error": "not found"}), 404
    return jsonify(user_schema.dump(user))


# ==================== 加密任务 ====================
@api_bp.route("/encrypt", methods=["POST"])
@jwt_required()
def submit_encrypt():
    data = encrypt_submit_schema.load(request.get_json() or {})
    uid = int(get_jwt_identity())

    if data.get("idem_key") and not try_acquire(data["idem_key"]):
        return jsonify({"error": "duplicate request"}), 409

    task_id = str(uuid.uuid4())
    record = EncryptTask(
        task_id=task_id,
        user_id=uid,
        raw_data=data["data"],
        status="PENDING",
        queue=data["queue"],
    )
    db.session.add(record)
    db.session.commit()

    if data["queue"] == "high":
        high_priority_demo.apply_async(args=[data["data"]], task_id=task_id, queue="high")
    else:
        encrypt_and_save.apply_async(
            args=[task_id, data["data"]], task_id=task_id, queue="normal"
        )

    return jsonify({"task_id": task_id, "status": "PENDING"}), 202


@api_bp.route("/encrypt/<task_id>", methods=["GET"])
@jwt_required()
def get_encrypted(task_id):
    uid = int(get_jwt_identity())
    record = EncryptTask.query.filter_by(task_id=task_id, user_id=uid).first()
    if not record:
        return jsonify({"error": "task not found"}), 404
    return jsonify(encrypt_task_schema.dump(record))


@api_bp.route("/encrypt/<task_id>/cancel", methods=["POST"])
@jwt_required()
def cancel_task(task_id):
    uid = int(get_jwt_identity())
    record = EncryptTask.query.filter_by(task_id=task_id, user_id=uid).first()
    if not record:
        return jsonify({"error": "task not found"}), 404

    from app import celery
    celery.control.revoke(task_id, terminate=True, signal="SIGTERM")
    record.status = "REVOKED"
    db.session.commit()
    return jsonify({"task_id": task_id, "status": "REVOKED"})


@api_bp.route("/tasks", methods=["GET"])
@jwt_required()
def list_tasks():
    query = task_list_query_schema.load(request.args.to_dict())   # ← 校验 query 参数
    uid = int(get_jwt_identity())

    q = EncryptTask.query.filter_by(user_id=uid).order_by(EncryptTask.id.desc())
    total = q.count()
    items = q.offset((query["page"] - 1) * query["size"]).limit(query["size"]).all()

    return jsonify({
        "total": total,
        "page": query["page"],
        "size": query["size"],
        "items": encrypt_tasks_schema.dump(items),
    })


@api_bp.route("/health", methods=["GET"])
def health():
    return jsonify({"status": "ok"})


# ==================== admin ====================
@api_bp.route("/admin/tasks", methods=["GET"])
@require_role("admin")
def admin_list_tasks():
    items = EncryptTask.query.order_by(EncryptTask.id.desc()).limit(100).all()
    return jsonify({"items": encrypt_tasks_schema.dump(items)})