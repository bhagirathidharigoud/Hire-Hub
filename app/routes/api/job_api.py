from flask import Blueprint, jsonify, request, session

from app.exceptions import DuplicateApplicationError, JobClosedError, JobNotFoundError
from app.services.audit_log_service import AuditLogService
from app.services.job_service import JobService
from app.services.notification_service import NotificationService
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.utils.decorators import api_login_required, api_role_required

job_api = Blueprint("job_api", __name__, url_prefix="/api")


@job_api.route("/jobs", methods=["GET"])
def list_jobs():
    filters = request.args.to_dict()
    filters.pop("status", None)
    filters.pop("recruiter_id", None)
    filters["status"] = "OPEN"
    try:
        jobs = JobService().search_jobs(**filters)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    return jsonify({"success": True, "data": jobs})


@job_api.route("/jobs", methods=["POST"])
@api_login_required
@api_role_required("RECRUITER")
def create_job():
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"success": False, "message": "Job details must be a JSON object"}), 400
    payload["recruiter_id"] = session["user_id"]
    recruiter = UserRepository().find_one({"_id": session["user_id"]}) or {}
    company = recruiter.get("company_profile") or {}
    payload["company_id"] = recruiter["_id"]
    payload["company_name"] = company.get("name", "")
    try:
        job = JobService().create_job(payload)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    AuditLogService().log_event("job.created", f"Job {job.get('title')} created", actor_id=session["user_id"], actor_role="RECRUITER", metadata={"job_id": job["_id"]})
    return jsonify({"success": True, "message": "Job created successfully", "data": job}), 201


@job_api.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    try:
        job = JobService().get_job_by_id(job_id)
    except JobNotFoundError:
        return jsonify({"success": False, "message": "Job not found"}), 404
    if job.get("status") != "OPEN" and not (
        session.get("role") == "ADMIN"
        or (
            session.get("role") == "RECRUITER"
            and job.get("recruiter_id") == session.get("user_id")
        )
    ):
        return jsonify({"success": False, "message": "Job not found"}), 404
    return jsonify({"success": True, "data": job})


@job_api.route("/jobs/<job_id>/status", methods=["PATCH"])
@api_login_required
@api_role_required("RECRUITER", "ADMIN")
def update_job_status(job_id):
    try:
        job = JobService().get_job_by_id(job_id)
    except JobNotFoundError:
        return jsonify({"success": False, "message": "Job not found"}), 404
    if session.get("role") == "RECRUITER" and job.get("recruiter_id") != session["user_id"]:
        return jsonify({"success": False, "message": "You are not authorized to update this job"}), 403
    payload = request.get_json(silent=True) or {}
    if not isinstance(payload, dict):
        return jsonify({"success": False, "message": "Job status must be a JSON object"}), 400
    try:
        updated = JobService().update_job_status(job_id, payload.get("status"))
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    AuditLogService().log_event(
        "job.status_changed",
        f"Job {job.get('title')} status changed to {updated['status']}",
        actor_id=session["user_id"],
        actor_role=session.get("role"),
        metadata={"job_id": job_id, "status": updated["status"]},
    )
    return jsonify({"success": True, "message": "Job status updated", "data": updated})


@job_api.route("/jobs/<job_id>/apply", methods=["POST"])
@api_login_required
@api_role_required("CANDIDATE")
def apply(job_id):
    try:
        application = JobService().apply_to_job(session["user_id"], job_id)
    except JobNotFoundError as exc:
        return jsonify({"success": False, "message": exc.message}), 404
    except (DuplicateApplicationError, JobClosedError) as exc:
        return jsonify({"success": False, "message": exc.message}), 409
    NotificationService().create(session["user_id"], "Your application was submitted successfully.", "SUCCESS")
    job = JobRepository().find_one({"_id": job_id})
    if job and job.get("recruiter_id"):
        candidate = UserRepository().find_one({"_id": session["user_id"]}) or {}
        NotificationService().create(
            job["recruiter_id"],
            f"{candidate.get('name', 'A candidate')} applied for {job.get('title', 'your job')}.",
        )
    AuditLogService().log_event("application.created", "Candidate applied for a job", actor_id=session["user_id"], actor_role="CANDIDATE", metadata={"job_id": job_id, "application_id": application["_id"]})
    return jsonify({"success": True, "message": "Application submitted successfully", "data": application}), 201
