import uuid
from flask import Blueprint, request, jsonify, send_file
from flask_jwt_extended import jwt_required, get_jwt_identity

from app.extensions import db, limiter
from app.models import Report, ReportVersion
from app.schemas import (
    ReportSubmitSchema, ReportSchema, ReportVersionSchema, ReportListQuerySchema,
)
from app.utils.auth import require_role
from app.celery_tasks.report_tasks import generate_report
import os
import io
import zipfile
from flask import send_file

report_bp = Blueprint("report", __name__)

submit_schema = ReportSubmitSchema()
report_schema = ReportSchema()
reports_schema = ReportSchema(many=True)
version_schema = ReportVersionSchema()
versions_schema = ReportVersionSchema(many=True)
list_query_schema = ReportListQuerySchema()


@report_bp.route("", methods=["POST"])
@jwt_required()
@limiter.limit("30/minute")
def submit_report():
    data = submit_schema.load(request.get_json() or {})
    uid = int(get_jwt_identity())

    report = Report(
        report_no=f"RPT-{uuid.uuid4().hex[:8].upper()}",
        title=data["title"],
        content=data["content"],
        user_id=uid,
        status="draft",
    )
    db.session.add(report)
    db.session.commit()

    generate_report.apply_async(
        args=[report.id, data["format"], data["content"]],
        queue="normal",
    )
    return jsonify(report_schema.dump(report)), 202


@report_bp.route("", methods=["GET"])
@jwt_required()
def list_reports():
    query = list_query_schema.load(request.args.to_dict())
    uid = int(get_jwt_identity())

    q = Report.query.filter_by(user_id=uid)
    if query["status"]:
        q = q.filter_by(status=query["status"])
    q = q.order_by(Report.id.desc())

    total = q.count()
    items = q.offset((query["page"] - 1) * query["size"]).limit(query["size"]).all()

    return jsonify({
        "total": total,
        "page": query["page"],
        "size": query["size"],
        "items": reports_schema.dump(items),
    })


@report_bp.route("/<int:report_id>", methods=["GET"])
@jwt_required()
def get_report(report_id):
    uid = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=uid).first()
    if not report:
        return jsonify({"error": "not found"}), 404
    return jsonify(report_schema.dump(report))


@report_bp.route("/<int:report_id>/versions", methods=["GET"])
@jwt_required()
def list_versions(report_id):
    uid = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=uid).first()
    if not report:
        return jsonify({"error": "not found"}), 404

    versions = (
        ReportVersion.query
        .filter_by(report_id=report_id)
        .order_by(ReportVersion.id.desc())
        .all()
    )
    return jsonify({"items": versions_schema.dump(versions)})


@report_bp.route("/<int:report_id>/submit-review", methods=["POST"])
@jwt_required()
def submit_review(report_id):
    """草稿 -> 待审核"""
    uid = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=uid).first()
    if not report:
        return jsonify({"error": "not found"}), 404
    if report.status != "draft":
        return jsonify({"error": f"cannot submit from {report.status}"}), 400

    report.status = "pending_review"
    db.session.commit()
    return jsonify(report_schema.dump(report))


@report_bp.route("/<int:report_id>/approve", methods=["POST"])
@require_role("admin")
def approve(report_id):
    """待审核 -> 已审核（仅 admin）"""
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"error": "not found"}), 404
    if report.status != "pending_review":
        return jsonify({"error": f"cannot approve from {report.status}"}), 400

    report.status = "approved"
    db.session.commit()
    return jsonify(report_schema.dump(report))


@report_bp.route("/<int:report_id>/archive", methods=["POST"])
@require_role("admin")
def archive(report_id):
    """已审核 -> 已归档（仅 admin）"""
    report = db.session.get(Report, report_id)
    if not report:
        return jsonify({"error": "not found"}), 404
    if report.status != "approved":
        return jsonify({"error": f"cannot archive from {report.status}"}), 400

    report.status = "archived"
    db.session.commit()
    return jsonify(report_schema.dump(report))


@report_bp.route("/<int:report_id>/download/<version>", methods=["GET"])
@jwt_required()
def download(report_id, version):
    uid = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=uid).first()
    if not report:
        return jsonify({"error": "not found"}), 404

    rv = ReportVersion.query.filter_by(report_id=report_id, version=version).first()
    if not rv:
        return jsonify({"error": "version not found"}), 404

    return send_file(rv.file_path, as_attachment=True)


@report_bp.route("/<int:report_id>/regenerate", methods=["POST"])
@jwt_required()
def regenerate(report_id):
    """重新生成，版本 +0.1"""
    uid = int(get_jwt_identity())
    report = Report.query.filter_by(id=report_id, user_id=uid).first()
    if not report:
        return jsonify({"error": "not found"}), 404

    fmt = (request.get_json() or {}).get("format", "xlsx")
    generate_report.apply_async(
        args=[report.id, fmt, report.content or ""],
        queue="normal",
    )
    return jsonify({"report_id": report_id, "status": "regenerating"}), 202

@report_bp.route("/batch-export", methods=["POST"])
@jwt_required()
@limiter.limit("10/minute")
def batch_export():
    """批量导出报告，返回 ZIP"""
    data = request.get_json() or {}
    report_ids = data.get("report_ids") or []

    if not report_ids:
        return jsonify({"error": "report_ids is required"}), 400

    uid = int(get_jwt_identity())

    # 只导出当前用户的报告
    reports = Report.query.filter(
        Report.id.in_(report_ids),
        Report.user_id == uid,
    ).all()

    if not reports:
        return jsonify({"error": "no reports found"}), 404

    # 内存里打包 ZIP
    memory_file = io.BytesIO()
    with zipfile.ZipFile(memory_file, "w", zipfile.ZIP_DEFLATED) as zf:
        for report in reports:
            # 取最新版本的文件
            version = (
                ReportVersion.query
                .filter_by(report_id=report.id)
                .order_by(ReportVersion.id.desc())
                .first()
            )
            if version and os.path.exists(version.file_path):
                # ZIP 里文件名：报告编号_版本.扩展名
                ext = version.file_type
                arcname = f"{report.report_no}_{version.version}.{ext}"
                zf.write(version.file_path, arcname)

    memory_file.seek(0)

    return send_file(
        memory_file,
        mimetype="application/zip",
        as_attachment=True,
        download_name=f"reports_{uid}.zip",
    )