from app import celery
from app.extensions import db, socketio
from app.models import Report, ReportVersion
from app.utils.report_builder import build_excel, build_pdf
from app.config import Config


def emit_progress(report_id, progress, status, message=""):
    """推送到对应房间"""
    socketio.emit(
        "report_progress",
        {
            "report_id": report_id,
            "progress": progress,
            "status": status,
            "message": message,
        },
        room=f"report_{report_id}",
    )


@celery.task(
    bind=True,
    name="app.celery_tasks.report_tasks.generate_report",
    queue="normal",
    max_retries=Config.CELERY_TASK_MAX_RETRIES,
)
def generate_report(self, report_id: int, fmt: str = "xlsx", content: str = ""):
    from app import get_flask_app
    app = get_flask_app()
    with app.app_context():
        emit_progress(report_id, 5, "started", "任务开始")

        report = db.session.get(Report, report_id)
        if not report:
            emit_progress(report_id, 0, "failed", "报告不存在")
            return {"error": "report not found"}

        try:
            emit_progress(report_id, 20, "generating", "生成文件...")

            if fmt == "pdf":
                path = build_pdf(report.report_no, report.title, content)
            else:
                path = build_excel(report.report_no, report.title, content)

            emit_progress(report_id, 70, "saving", "写入版本...")

            # 版本号 V1.0 -> V1.1
            last = (
                ReportVersion.query
                .filter_by(report_id=report.id)
                .order_by(ReportVersion.id.desc())
                .first()
            )
            if last:
                major, minor = last.version.replace("V", "").split(".")
                new_version = f"V{major}.{int(minor) + 1}"
            else:
                new_version = "V1.0"

            rv = ReportVersion(
                report_id=report.id,
                version=new_version,
                file_path=path,
                file_type=fmt,
            )
            db.session.add(rv)

            report.version = new_version
            report.status = "pending_review"
            report.content = content
            db.session.commit()

            emit_progress(report_id, 100, "done", f"完成 {new_version}")
            return {"report_id": report.id, "version": new_version, "file": path}

        except Exception as exc:
            db.session.rollback()
            report.status = "draft"
            db.session.commit()
            emit_progress(report_id, 0, "failed", str(exc))
            raise self.retry(exc=exc, countdown=5)