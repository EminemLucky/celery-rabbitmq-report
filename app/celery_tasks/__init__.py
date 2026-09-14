from app import create_app
from app import celery

# worker 启动时也创建一次 app，给 ContextTask 用
_flask_app = create_app()

# 把它挂到 app 模块的全局
import app as app_module
app_module._flask_app = _flask_app

from app.celery_tasks import normal_tasks  # noqa
from app.celery_tasks import beat_tasks    # noqa
from app.celery_tasks import signals       # noqa
from app.celery_tasks import normal_tasks   # noqa
from app.celery_tasks import beat_tasks     # noqa
from app.celery_tasks import report_tasks   # noqa
from app.celery_tasks import signals        # noqa