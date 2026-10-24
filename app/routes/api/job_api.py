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
    if "status" not in filters:
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
    payload["recruiter_id"] = session["user_id"]
    try:
        job = JobService().create_job(payload)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    AuditLogService().log_event("job.created", f"Job {job.get('title')} created", actor_id=session["user_id"], actor_role="RECRUITER", metadata={"job_id": job["_id"]})
    return jsonify({"success": True, "message": "Job created successfully", "data": job}), 201


@job_api.route("/jobs/<job_id>", methods=["GET"])
def get_job(job_id):
    job = JobService().get_job_by_id(job_id)
    return jsonify({"success": True, "data": job})


@job_api.route("/jobs/<job_id>/apply", methods=["POST"])
@api_login_required
@api_role_required("CANDIDATE")
def apply(job_id):
    try:
        application = JobService().apply_to_job(session["user_id"], job_id)
    except (DuplicateApplicationError, JobClosedError, JobNotFoundError) as exc:
        return jsonify({"success": False, "message": exc.message}), 400
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
