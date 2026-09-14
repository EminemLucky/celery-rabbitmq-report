from datetime import datetime
from app.extensions import db


# ==================== RBAC ====================
user_role = db.Table(
    "user_role",
    db.Column("user_id", db.Integer, db.ForeignKey("user.id"), primary_key=True),
    db.Column("role_id", db.Integer, db.ForeignKey("role.id"), primary_key=True),
)


class User(db.Model):
    __tablename__ = "user"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    username = db.Column(db.String(64), unique=True, index=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    roles = db.relationship("Role", secondary=user_role, backref="users")

    def set_password(self, raw: str):
        from werkzeug.security import generate_password_hash
        self.password_hash = generate_password_hash(raw)

    def check_password(self, raw: str) -> bool:
        from werkzeug.security import check_password_hash
        return check_password_hash(self.password_hash, raw)

    def has_role(self, name: str) -> bool:
        return any(r.name == name for r in self.roles)

    def to_dict(self):
        return {
            "id": self.id,
            "username": self.username,
            "roles": [r.name for r in self.roles],
        }


class Role(db.Model):
    __tablename__ = "role"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    name = db.Column(db.String(32), unique=True, nullable=False)


# ==================== 加密任务 ====================
class EncryptTask(db.Model):
    __tablename__ = "encrypt_task"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    task_id = db.Column(db.String(64), unique=True, index=True, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    raw_data = db.Column(db.Text, nullable=True)
    encrypted_data = db.Column(db.Text, nullable=True)
    status = db.Column(db.String(20), default="PENDING", index=True)
    queue = db.Column(db.String(20), default="normal")
    retries = db.Column(db.Integer, default=0)
    timeout = db.Column(db.Integer, default=300)
    error = db.Column(db.Text, nullable=True)

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_user_status", "user_id", "status"),
    )

    def to_dict(self):
        return {
            "task_id": self.task_id,
            "user_id": self.user_id,
            "status": self.status,
            "encrypted_data": self.encrypted_data,
            "queue": self.queue,
            "retries": self.retries,
            "error": self.error,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


# ==================== 幂等 ====================
class IdempotentRecord(db.Model):
    __tablename__ = "idempotent_record"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    idem_key = db.Column(db.String(128), unique=True, index=True, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ==================== 报告 & 版本 ====================
class Report(db.Model):
    __tablename__ = "report"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_no = db.Column(db.String(64), unique=True, index=True, nullable=False)
    title = db.Column(db.String(255), nullable=False)
    content = db.Column(db.Text, default="")
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), index=True)

    # 状态：draft -> pending_review -> approved -> archived
    status = db.Column(db.String(32), default="draft", index=True)
    version = db.Column(db.String(16), default="V1.0")

    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_report_user_status", "user_id", "status"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "report_no": self.report_no,
            "title": self.title,
            "content": self.content,
            "status": self.status,
            "version": self.version,
            "user_id": self.user_id,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class ReportVersion(db.Model):
    __tablename__ = "report_version"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    report_id = db.Column(db.Integer, db.ForeignKey("report.id"), index=True, nullable=False)
    version = db.Column(db.String(16), nullable=False)
    file_path = db.Column(db.String(512))
    file_type = db.Column(db.String(16))          # xlsx / pdf
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    __table_args__ = (
        db.Index("idx_report_version", "report_id", "version"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "report_id": self.report_id,
            "version": self.version,
            "file_path": self.file_path,
            "file_type": self.file_type,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }