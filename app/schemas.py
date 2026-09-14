from marshmallow import Schema, fields, validate


# ==================== 认证 ====================
class RegisterSchema(Schema):
    username = fields.Str(required=True, validate=validate.Length(min=3, max=64))
    password = fields.Str(required=True, validate=validate.Length(min=6, max=128))


class LoginSchema(Schema):
    username = fields.Str(required=True)
    password = fields.Str(required=True)


class UserSchema(Schema):
    id = fields.Int()
    username = fields.Str()
    roles = fields.Method("get_roles")

    def get_roles(self, obj):
        return [r.name for r in obj.roles]


# ==================== 加密任务 ====================
class EncryptSubmitSchema(Schema):
    data = fields.Str(required=True, validate=validate.Length(min=1, max=10000))
    queue = fields.Str(load_default="normal", validate=validate.OneOf(["normal", "high"]))
    idem_key = fields.Str(load_default=None, allow_none=True)


class EncryptTaskSchema(Schema):
    task_id = fields.Str()
    user_id = fields.Int()
    status = fields.Str()
    encrypted_data = fields.Str(allow_none=True)
    queue = fields.Str()
    retries = fields.Int()
    error = fields.Str(allow_none=True)
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


# ==================== 通用 ====================
class TaskListQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    size = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))

# ==================== 报告 ====================
class ReportSubmitSchema(Schema):
    title = fields.Str(required=True, validate=validate.Length(min=1, max=255))
    content = fields.Str(load_default="")
    format = fields.Str(load_default="xlsx", validate=validate.OneOf(["xlsx", "pdf"]))


class ReportSchema(Schema):
    id = fields.Int()
    report_no = fields.Str()
    title = fields.Str()
    content = fields.Str()
    status = fields.Str()
    version = fields.Str()
    user_id = fields.Int()
    created_at = fields.DateTime()
    updated_at = fields.DateTime()


class ReportVersionSchema(Schema):
    id = fields.Int()
    report_id = fields.Int()
    version = fields.Str()
    file_type = fields.Str()
    created_at = fields.DateTime()


class ReportListQuerySchema(Schema):
    page = fields.Int(load_default=1, validate=validate.Range(min=1))
    size = fields.Int(load_default=20, validate=validate.Range(min=1, max=100))
    status = fields.Str(load_default=None, allow_none=True)