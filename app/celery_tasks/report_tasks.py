from app import celery
from app.extensions import db
from app.models import Report, ReportVersion
from app.utils.report_builder import build_excel, build_pdf
from app.config import Config


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
        report = db.session.get(Report, report_id)
        if not report:
            return {"error": "report not found"}

        try:
            if fmt == "pdf":
                path = build_pdf(report.report_no, report.title, content)
            else:
                path = build_excel(report.report_no, report.title, content)

            # 版本号：V1.0 -> V1.1 -> V1.2
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
            report.status = "pending_review"    # 草稿 -> 待审核
            report.content = content
            db.session.commit()

            return {"report_id": report.id, "version": new_version, "file": path}

        except Exception as exc:
            db.session.rollback()
            report.status = "draft"
            db.session.commit()
            raise self.retry(exc=exc, countdown=5)