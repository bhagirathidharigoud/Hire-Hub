from flask import Blueprint, abort, jsonify, session

from app.repositories.user_repository import UserRepository
from app.utils.decorators import api_login_required, api_role_required

recruiter_api = Blueprint("recruiter_api", __name__, url_prefix="/api/recruiters")


@recruiter_api.route("/<recruiter_id>", methods=["GET"])
@api_login_required
@api_role_required("RECRUITER", "ADMIN")
def get_recruiter(recruiter_id):
    if session.get("role") != "ADMIN" and session.get("user_id") != recruiter_id:
        abort(403)
    user = UserRepository().find_one({"_id": recruiter_id})
    if not user or user.get("role") != "RECRUITER":
        abort(404)
    user.pop("password_hash", None)
    return jsonify({"success": True, "data": user})
