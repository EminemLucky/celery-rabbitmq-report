import time
from celery import shared_task
from app import db
from app.models import EncryptTask


@shared_task(
    name="app.celery_tasks.beat_tasks.cleanup_stale_tasks",
    queue="beat",
)
def cleanup_stale_tasks():
    """定时清理：把超过 1 天还 PENDING 的任务标记为 FAILURE"""
    from datetime import datetime, timedelta
    threshold = datetime.utcnow() - timedelta(days=1)

    stale = EncryptTask.query.filter(
        EncryptTask.status == "PENDING",
        EncryptTask.created_at < threshold,
    ).all()

    for t in stale:
        t.status = "FAILURE"
        t.error = "stale task cleaned by beat"
    db.session.commit()

    return {"cleaned": len(stale)}


@shared_task(
    name="app.celery_tasks.beat_tasks.heartbeat",
    queue="beat",
)
def heartbeat():
    """每分钟心跳，演示 Beat 调度"""
    return {"ts": time.time()}