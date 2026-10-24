from flask import Blueprint, jsonify, request, session

from app.repositories.interview_repository import InterviewRepository
from app.services.audit_log_service import AuditLogService
from app.services.interview_service import InterviewService
from app.services.notification_service import NotificationService
from app.utils.decorators import api_login_required, api_role_required

interview_api = Blueprint("interview_api", __name__, url_prefix="/api")


@interview_api.route("/interviews", methods=["POST"])
@api_login_required
@api_role_required("RECRUITER")
def create_interview():
    payload = request.get_json(silent=True) or {}
    payload["recruiter_id"] = session["user_id"]
    try:
        interview = InterviewService().schedule(payload)
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    AuditLogService().log_event("interview.scheduled", "Recruiter scheduled an interview", actor_id=session["user_id"], actor_role="RECRUITER", metadata={"application_id": interview["application_id"]})
    NotificationService().create(
        interview["candidate_id"],
        f"An interview has been scheduled on {interview['date']} at {interview['time']}.",
    )
    return jsonify({"success": True, "message": "Interview scheduled", "data": interview}), 201


@interview_api.route("/interviews", methods=["GET"])
@api_login_required
def list_interviews():
    if session.get("role") == "CANDIDATE":
        interviews = InterviewService().list_for_candidate(session["user_id"])
    elif session.get("role") == "RECRUITER":
        interviews = InterviewService().list_for_recruiter(session["user_id"])
    elif session.get("role") == "ADMIN":
        interviews = InterviewRepository().find_all()
    else:
        return jsonify({"success": False, "message": "You are not authorized to perform this action"}), 403
    return jsonify({"success": True, "data": interviews})
