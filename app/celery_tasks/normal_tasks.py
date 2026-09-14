import time
from app import celery
from app import db
from app.crypto import aes_encrypt
from app.models import EncryptTask
from app.config import Config


@celery.task(
    bind=True,
    name="app.celery_tasks.normal_tasks.encrypt_and_save",
    queue="normal",
    max_retries=Config.CELERY_TASK_MAX_RETRIES,
    default_retry_delay=Config.CELERY_TASK_RETRY_DELAY,
    acks_late=True,
    time_limit=Config.CELERY_TASK_TIME_LIMIT,
    soft_time_limit=Config.CELERY_TASK_SOFT_TIME_LIMIT,
)
def encrypt_and_save(self, task_id: str, raw_data: str):
    """
    1. 查任务记录
    2. AES 加密
    3. 写回 MySQL
    失败自动重试（最多 3 次）
    """
    record = EncryptTask.query.filter_by(task_id=task_id).first()
    if not record:
        return {"task_id": task_id, "error": "record not found"}

    try:
        record.status = "STARTED"
        record.retries = self.request.retries
        db.session.commit()

        # 模拟耗时
        time.sleep(1)

        # AES 加密
        encrypted = aes_encrypt(raw_data)

        record.encrypted_data = encrypted
        record.status = "SUCCESS"
        record.error = None
        db.session.commit()

        return {"task_id": task_id, "status": "SUCCESS"}

    except Exception as exc:
        db.session.rollback()
        record.status = "RETRY" if self.request.retries < self.max_retries else "FAILURE"
        record.error = str(exc)
        record.retries = self.request.retries + 1
        db.session.commit()

        # 自动重试
        raise self.retry(exc=exc, countdown=Config.CELERY_TASK_RETRY_DELAY)


@celery.task(
    bind=True,
    name="app.celery_tasks.normal_tasks.high_priority_demo",
    queue="high",
    max_retries=2,
)
def high_priority_demo(self, payload: str):
    """演示高优先级队列任务"""
    time.sleep(2)
    return {"payload": payload, "queue": "high"}