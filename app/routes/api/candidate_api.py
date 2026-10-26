from flask import Blueprint, abort, jsonify, request, session

from app.repositories.user_repository import UserRepository
from app.repositories.job_repository import JobRepository
from app.services.application_service import ApplicationService
from app.services.interview_service import InterviewService
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService
from app.services.audit_log_service import AuditLogService
from app.utils.decorators import api_login_required, api_role_required
from app.utils.validators import is_valid_phone, normalize_skills

candidate_api = Blueprint("candidate_api", __name__, url_prefix="/api/candidates")


@candidate_api.route("/me/saved-jobs", methods=["GET"])
@api_login_required
@api_role_required("CANDIDATE")
def saved_jobs():
    user = UserRepository().find_one({"_id": session["user_id"]}) or {}
    saved_ids = user.get("saved_job_ids", [])
    jobs = JobRepository().find_all({"_id": {"$in": saved_ids}})
    return jsonify({"success": True, "data": [job for job in jobs if job.get("status") == "OPEN"]})


@candidate_api.route("/me/saved-jobs/<job_id>", methods=["PUT"])
@api_login_required
@api_role_required("CANDIDATE")
def toggle_saved_job(job_id):
    job = JobRepository().find_one({"_id": job_id})
    if not job or job.get("status") != "OPEN":
        return jsonify({"success": False, "message": "Open job not found"}), 404
    users = UserRepository()
    user = users.find_one({"_id": session["user_id"]}) or {}
    saved_ids = set(user.get("saved_job_ids", []))
    saved = job_id not in saved_ids
    if saved:
        saved_ids.add(job_id)
    else:
        saved_ids.remove(job_id)
    users.update_one({"_id": session["user_id"]}, {"saved_job_ids": sorted(saved_ids)})
    return jsonify({"success": True, "data": {"saved": saved, "job_id": job_id}})


@candidate_api.route("/me/recommendations", methods=["GET"])
@api_login_required
@api_role_required("CANDIDATE")
def recommended_jobs():
    try:
        limit = min(max(int(request.args.get("limit", 6)), 1), 50)
    except ValueError:
        return jsonify({"success": False, "message": "Limit must be an integer"}), 400
    return jsonify({
        "success": True,
        "data": MatchingService().recommend_for_candidate(session["user_id"], limit=limit),
    })


@candidate_api.route("/me/dashboard", methods=["GET"])
@api_login_required
@api_role_required("CANDIDATE")
def candidate_dashboard():
    candidate_id = session["user_id"]
    applications = ApplicationService().my_applications(candidate_id)
    interviews = InterviewService().list_for_candidate(candidate_id)
    notifications = NotificationService().list_for_user(candidate_id)
    user = UserRepository().find_one({"_id": candidate_id}) or {}
    job_ids = [application.get("job_id") for application in applications]
    jobs = JobRepository().find_all({"_id": {"$in": job_ids}})
    job_map = {job["_id"]: job for job in jobs}
    for application in applications:
        application["job"] = job_map.get(application.get("job_id"))
    return jsonify({
        "success": True,
        "data": {
            "user": {key: value for key, value in user.items() if key != "password_hash"},
            "applications": applications,
            "interviews": interviews,
            "notifications": notifications,
            "recommendations": MatchingService().recommend_for_candidate(candidate_id, limit=3),
            "saved_job_ids": user.get("saved_job_ids", []),
        },
    })


@candidate_api.route("/<candidate_id>", methods=["GET"])
@api_login_required
@api_role_required("CANDIDATE", "ADMIN")
def get_candidate(candidate_id):
    if session.get("role") != "ADMIN" and session.get("user_id") != candidate_id:
        abort(403)
    user = UserRepository().find_one({"_id": candidate_id})
    if not user or user.get("role") != "CANDIDATE":
        abort(404)
    user.pop("password_hash", None)
    return jsonify({"success": True, "data": user})


@candidate_api.route("/<candidate_id>", methods=["PUT"])
@api_login_required
@api_role_required("CANDIDATE")
def update_candidate(candidate_id):
    if session.get("user_id") != candidate_id:
        abort(403)
    payload = request.get_json(silent=True) or {}
    allowed_fields = {"name", "phone", "location", "skills"}
    updates = {key: payload[key] for key in allowed_fields if key in payload}
    if not updates:
        return jsonify({"success": False, "message": "No supported profile fields provided"}), 400
    if "name" in updates and not str(updates["name"]).strip():
        return jsonify({"success": False, "message": "Name is required"}), 400
    if "phone" in updates and updates["phone"] and not is_valid_phone(updates["phone"]):
        return jsonify({"success": False, "message": "Invalid phone number"}), 400
    if "skills" in updates and not isinstance(updates["skills"], (str, list, tuple)):
        return jsonify({"success": False, "message": "Skills must be a string or a list"}), 400
    if "name" in updates:
        updates["name"] = str(updates["name"]).strip()
    if "phone" in updates:
        updates["phone"] = str(updates["phone"] or "").strip()
    if "location" in updates:
        updates["location"] = str(updates["location"] or "").strip()
    if "skills" in updates:
        updates["skills"] = normalize_skills(updates["skills"])
    user = UserRepository().update_one({"_id": candidate_id}, updates)
    AuditLogService().log_event("candidate.profile_updated", "Candidate updated their profile", actor_id=candidate_id, actor_role="CANDIDATE")
    user.pop("password_hash", None)
    return jsonify({"success": True, "message": "Candidate updated", "data": user})
