import os
import logging
from flask import Flask, jsonify
from celery import Celery
from kombu import Queue
from celery.schedules import crontab
from app.extensions import db, jwt, migrate

logging.basicConfig(level=logging.INFO)

# ---------------- Celery ----------------
celery = Celery(__name__)

celery.conf.broker_url = os.getenv("CELERY_BROKER", "amqp://appuser:apppass@rabbitmq:5672//")
celery.conf.result_backend = os.getenv("CELERY_BACKEND", "redis://redis:6379/1")
celery.conf.task_acks_late = True
celery.conf.worker_prefetch_multiplier = 1
celery.conf.task_default_queue = "normal"

celery.conf.task_queues = (
    Queue("normal"),
    Queue("beat"),
    Queue("high"),
)

celery.conf.task_routes = {
    "app.celery_tasks.normal_tasks.*": {"queue": "normal"},
    "app.celery_tasks.beat_tasks.*": {"queue": "beat"},
    "app.celery_tasks.report_tasks.*": {"queue": "normal"},
}

celery.conf.task_time_limit = 60 * 5
celery.conf.task_soft_time_limit = 60 * 4
celery.conf.imports = ("app.celery_tasks",)
celery.conf.timezone = "Asia/Shanghai"
celery.conf.enable_utc = False

celery.conf.beat_schedule = {
    "cleanup-stale-every-10min": {
        "task": "app.celery_tasks.beat_tasks.cleanup_stale_tasks",
        "schedule": crontab(minute="*/10"),
        "options": {"queue": "beat"},
    },
    "heartbeat-every-minute": {
        "task": "app.celery_tasks.beat_tasks.heartbeat",
        "schedule": crontab(minute="*"),
        "options": {"queue": "beat"},
    },
}


# ---------------- Flask app ----------------
_flask_app = None


def get_flask_app():
    global _flask_app
    if _flask_app is None:
        _flask_app = create_app()
    return _flask_app


class ContextTask(celery.Task):
    abstract = True

    def __call__(self, *args, **kwargs):
        app = get_flask_app()
        with app.app_context():
            return self.run(*args, **kwargs)


celery.Task = ContextTask


def create_app(config_override=None):
    global _flask_app

    app = Flask(__name__)
    app.config.from_object("app.config.Config")

    # ✅ 先覆盖配置
    if config_override:
        app.config.update(config_override)

    # ✅ 加这三行：SQLite 不支持 MySQL 连接池参数
    if app.config["SQLALCHEMY_DATABASE_URI"].startswith("sqlite"):
        app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {}

    # ✅ 再 init 扩展，这时用的是覆盖后的 URI
    db.init_app(app)
    jwt.init_app(app)
    migrate.init_app(app, db)

    _flask_app = app

    from app.routes import api_bp
    app.register_blueprint(api_bp, url_prefix="/api")

    from app.api.report import report_bp
    app.register_blueprint(report_bp, url_prefix="/api/report")

    from marshmallow import ValidationError
    @app.errorhandler(ValidationError)
    def handle_validation_error(err):
        return jsonify({"error": "validation failed", "detail": err.messages}), 400

    @app.cli.command("init-roles")
    def init_roles_command():
        from app.models import Role
        for name in ("admin", "user"):
            if not Role.query.filter_by(name=name).first():
                db.session.add(Role(name=name))
        db.session.commit()
        print("roles initialized")

    return app



from app.celery_tasks import normal_tasks   # noqa
from app.celery_tasks import beat_tasks     # noqa
from app.celery_tasks import report_tasks   # noqa
from app.celery_tasks import signals        # noqa