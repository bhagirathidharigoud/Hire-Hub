from flask import Blueprint, abort, jsonify, request, session

from app.repositories.user_repository import UserRepository
from app.services.matching_service import MatchingService
from app.services.audit_log_service import AuditLogService
from app.utils.decorators import api_login_required, api_role_required

candidate_api = Blueprint("candidate_api", __name__, url_prefix="/api/candidates")


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
    user = UserRepository().update_one({"_id": candidate_id}, updates)
    AuditLogService().log_event("candidate.profile_updated", "Candidate updated their profile", actor_id=candidate_id, actor_role="CANDIDATE")
    user.pop("password_hash", None)
    return jsonify({"success": True, "message": "Candidate updated", "data": user})
