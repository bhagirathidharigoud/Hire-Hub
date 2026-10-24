from flask import Blueprint, jsonify, request, session

from app.repositories.application_repository import ApplicationRepository
from app.repositories.audit_log_repository import AuditLogRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from app.services.reporting_service import ReportingService
from app.utils.decorators import api_login_required, api_role_required

admin_api = Blueprint("admin_api", __name__, url_prefix="/api/admin")


@admin_api.route("/users", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def list_users():
    users = UserRepository().find_all()
    for user in users:
        user.pop("password_hash", None)
    return jsonify({"success": True, "data": users})


@admin_api.route("/users/<user_id>", methods=["PATCH"])
@api_login_required
@api_role_required("ADMIN")
def update_user(user_id):
    payload = request.get_json(silent=True) or {}
    updates = {}
    if "role" in payload:
        if payload["role"] not in {"CANDIDATE", "RECRUITER", "ADMIN"}:
            return jsonify({"success": False, "message": "Invalid role"}), 400
        updates["role"] = payload["role"]
    if "is_active" in payload:
        if not isinstance(payload["is_active"], bool):
            return jsonify({"success": False, "message": "is_active must be a boolean"}), 400
        updates["is_active"] = payload["is_active"]
    if not updates:
        return jsonify({"success": False, "message": "Provide a role or is_active update"}), 400
    user = UserRepository().find_one({"_id": user_id})
    if not user:
        return jsonify({"success": False, "message": "User not found"}), 404
    if user_id == session.get("user_id") and (updates.get("role", user.get("role")) != "ADMIN" or updates.get("is_active", True) is False):
        return jsonify({"success": False, "message": "You cannot remove your own admin access"}), 400
    updated = UserRepository().update_one({"_id": user_id}, updates)
    AuditLogService().log_event("user.updated", f"User {user.get('email')} updated by admin", actor_id=session["user_id"], actor_role="ADMIN", metadata={"user_id": user_id, **updates})
    updated.pop("password_hash", None)
    return jsonify({"success": True, "data": updated})


@admin_api.route("/jobs", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def list_jobs():
    return jsonify({"success": True, "data": JobRepository().find_all()})


@admin_api.route("/jobs/<job_id>", methods=["PATCH", "DELETE"])
@api_login_required
@api_role_required("ADMIN")
def manage_job(job_id):
    jobs = JobRepository()
    job = jobs.find_one({"_id": job_id})
    if not job:
        return jsonify({"success": False, "message": "Job not found"}), 404
    if request.method == "DELETE":
        jobs.delete_one({"_id": job_id})
        AuditLogService().log_event("job.deleted", f"Job {job.get('title')} deleted by admin", actor_id=session["user_id"], actor_role="ADMIN", metadata={"job_id": job_id})
        return jsonify({"success": True, "message": "Job deleted"})
    payload = request.get_json(silent=True) or {}
    status = payload.get("status")
    if status not in {"OPEN", "CLOSED"}:
        return jsonify({"success": False, "message": "Status must be OPEN or CLOSED"}), 400
    updated = jobs.update_one({"_id": job_id}, {"status": status})
    AuditLogService().log_event("job.status_changed", f"Job {job.get('title')} status changed to {status}", actor_id=session["user_id"], actor_role="ADMIN", metadata={"job_id": job_id, "status": status})
    return jsonify({"success": True, "data": updated})


@admin_api.route("/applications", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def list_applications():
    return jsonify({"success": True, "data": ApplicationRepository().find_all()})


@admin_api.route("/analytics", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def analytics():
    report = ReportingService().build_report()
    payload = {
        "stats": report["stats"],
        "application_statuses": report["application_statuses"],
        "job_modes": report["job_modes"],
        "job_types": report["job_types"],
    }
    return jsonify({"success": True, "data": payload})


@admin_api.route("/reports", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def reports():
    report = ReportingService().build_report()
    return jsonify({
        "success": True,
        "data": {
            "stats": report["stats"],
            "application_statuses": report["application_statuses"],
            "job_modes": report["job_modes"],
            "job_types": report["job_types"],
        },
    })


@admin_api.route("/audit-logs", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def audit_logs():
    return jsonify({"success": True, "data": AuditLogRepository().find_all()})


@admin_api.route("/stats", methods=["GET"])
@api_login_required
@api_role_required("ADMIN")
def stats():
    return analytics()
