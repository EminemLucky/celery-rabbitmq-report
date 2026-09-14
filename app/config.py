import os
from datetime import timedelta


class Config:
    # ---------- Flask ----------
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret")

    # ---------- MySQL ----------
    MYSQL_HOST = os.getenv("MYSQL_HOST", "mysql")
    MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    MYSQL_USER = os.getenv("MYSQL_USER", "appuser")
    MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "apppass")
    MYSQL_DB = os.getenv("MYSQL_DB", "reportdb")

    SQLALCHEMY_DATABASE_URI = (
        f"mysql+pymysql://{MYSQL_USER}:{MYSQL_PASSWORD}"
        f"@{MYSQL_HOST}:{MYSQL_PORT}/{MYSQL_DB}?charset=utf8mb4"
    )
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_pre_ping": True,
        "pool_recycle": 3600,
        "pool_size": 10,
        "max_overflow": 20,
    }

    # ---------- Redis ----------
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_DB = int(os.getenv("REDIS_DB", 0))

    # ---------- Celery ----------
    CELERY_BROKER_URL = os.getenv(
        "CELERY_BROKER",
        "amqp://appuser:apppass@rabbitmq:5672//"
    )
    CELERY_RESULT_BACKEND = os.getenv(
        "CELERY_BACKEND",
        "redis://redis:6379/1"
    )
    CELERY_TASK_ACKS_LATE = True
    CELERY_WORKER_PREFETCH_MULTIPLIER = 1
    CELERY_TASK_DEFAULT_QUEUE = "normal"
    CELERY_TASK_QUEUES = ("normal", "beat", "high")

    CELERY_TASK_TIME_LIMIT = 60 * 5
    CELERY_TASK_SOFT_TIME_LIMIT = 60 * 4
    CELERY_TASK_MAX_RETRIES = 3
    CELERY_TASK_RETRY_DELAY = 5

    # ---------- JWT 双 token ----------
    JWT_SECRET_KEY = os.getenv(
        "JWT_SECRET_KEY",
        "jwt-dev-secret-key-at-least-32-bytes-0000"
    )
    JWT_ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
    JWT_REFRESH_TOKEN_EXPIRES = timedelta(days=7)

    # ---------- AES ----------
    AES_KEY = os.getenv("AES_KEY", "0123456789abcdef0123456789abcdef")
    AES_IV = os.getenv("AES_IV", "abcdef9876543210")

    # ---------- 文件存储 ----------
    REPORT_DIR = os.getenv("REPORT_DIR", "/app/reports")