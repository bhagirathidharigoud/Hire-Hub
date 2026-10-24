from flask import Blueprint, abort, jsonify, request, session

from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.services.application_service import ApplicationService
from app.services.audit_log_service import AuditLogService
from app.services.notification_service import NotificationService
from app.utils.decorators import api_login_required

application_api = Blueprint("application_api", __name__, url_prefix="/api")


@application_api.route("/applications", methods=["GET"])
@api_login_required
def list_applications():
    if session.get("role") == "CANDIDATE":
        data = ApplicationService().my_applications(session["user_id"])
    elif session.get("role") == "RECRUITER":
        data = ApplicationService().for_recruiter(session["user_id"])
    elif session.get("role") == "ADMIN":
        data = ApplicationRepository().find_all()
    else:
        abort(403)
    return jsonify({"success": True, "data": data})


@application_api.route("/applications/<application_id>", methods=["GET"])
@api_login_required
def get_application(application_id):
    app = ApplicationService().get_by_id(application_id)
    if not _can_access_application(app):
        abort(403)
    return jsonify({"success": True, "data": app})


@application_api.route("/applications/<application_id>/status", methods=["PUT"])
@api_login_required
def update_status(application_id):
    payload = request.get_json(silent=True) or {}
    application = ApplicationService().get_by_id(application_id)
    if session.get("role") == "CANDIDATE":
        if (
            application.get("candidate_id") != session["user_id"]
            or payload.get("status") != "WITHDRAWN"
            or application.get("status") not in {"APPLIED", "UNDER_REVIEW", "SHORTLISTED"}
        ):
            abort(403)
    elif session.get("role") == "RECRUITER":
        if payload.get("status") not in {"UNDER_REVIEW", "SHORTLISTED", "SELECTED", "REJECTED"}:
            abort(403)
        if not _is_recruiter_for(application):
            abort(403)
    elif session.get("role") != "ADMIN":
        abort(403)
    app = ApplicationService().update_status(application_id, payload.get("status"))
    if app.get("candidate_id") != session.get("user_id"):
        NotificationService().create(
            app["candidate_id"],
            f"Your application status is now {app['status'].replace('_', ' ').lower()}.",
        )
    AuditLogService().log_event(
        "application.status_changed",
        f"Application status changed to {app['status']}",
        actor_id=session["user_id"],
        actor_role=session.get("role"),
        metadata={"application_id": application_id, "status": app["status"]},
    )
    return jsonify({"success": True, "message": "Status updated", "data": app})


def _is_recruiter_for(application):
    job = JobRepository().find_one({"_id": application.get("job_id")})
    return session.get("role") == "RECRUITER" and job and job.get("recruiter_id") == session.get("user_id")


def _can_access_application(application):
    if session.get("role") == "ADMIN":
        return True
    if session.get("role") == "CANDIDATE":
        return application.get("candidate_id") == session.get("user_id")
    return _is_recruiter_for(application)
