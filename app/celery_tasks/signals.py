from celery.signals import (
    task_prerun, task_postrun, task_failure, task_retry, task_revoked,
)
import logging

logger = logging.getLogger(__name__)


@task_prerun.connect
def on_task_prerun(task_id=None, task=None, **kwargs):
    logger.info(f"[prerun] task={task.name} id={task_id}")


@task_postrun.connect
def on_task_postrun(task_id=None, task=None, state=None, **kwargs):
    logger.info(f"[postrun] task={task.name} id={task_id} state={state}")


@task_failure.connect
def on_task_failure(task_id=None, exception=None, **kwargs):
    logger.error(f"[failure] task_id={task_id} exc={exception}")


@task_retry.connect
def on_task_retry(request=None, reason=None, **kwargs):
    logger.warning(f"[retry] task_id={request.id} reason={reason}")


@task_revoked.connect
def on_task_revoked(request=None, **kwargs):
    logger.warning(f"[revoked] task_id={request.id}")