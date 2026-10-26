from flask import Blueprint, jsonify, request, session

from app.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserDeactivatedError,
    UserNotFoundError,
)
from app.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import AuthService


auth_api = Blueprint("auth_api", __name__, url_prefix="/api/auth")


@auth_api.route("/register", methods=["POST"])
def register():
    payload = request.get_json(silent=True) or {}
    try:
        user = AuthService().register_user(payload)
    except UserAlreadyExistsError as exc:
        return jsonify({"success": False, "message": exc.message, "error_code": exc.code}), 409
    except ValueError as exc:
        return jsonify({"success": False, "message": str(exc)}), 400
    session["user_id"] = str(user.get("_id"))
    session["role"] = user.get("role")
    session.permanent = True
    AuditLogService().log_event("auth.register", "User account created", actor_id=str(user.get("_id")), actor_role=user.get("role"))
    response_user = {key: value for key, value in user.items() if key != "password_hash"}
    return jsonify({"success": True, "message": "User registered successfully", "data": response_user}), 201


@auth_api.route("/login", methods=["POST"])
def login():
    payload = request.get_json(silent=True) or {}
    try:
        user = AuthService().login_user(payload.get("email"), payload.get("password"))
    except (InvalidCredentialsError, UserNotFoundError, UserDeactivatedError) as exc:
        return jsonify({"success": False, "message": exc.message, "error_code": exc.code}), 401
    session.clear()
    session["user_id"] = str(user.get("_id"))
    session["role"] = user.get("role")
    session.permanent = True
    AuditLogService().log_event("auth.login", "User signed in", actor_id=str(user.get("_id")), actor_role=user.get("role"))
    response_user = {key: value for key, value in user.items() if key != "password_hash"}
    return jsonify({"success": True, "message": "Login successful", "data": response_user})


@auth_api.route("/logout", methods=["POST"])
def logout():
    user_id = session.get("user_id")
    role = session.get("role")
    if user_id:
        AuditLogService().log_event("auth.logout", "User signed out", actor_id=user_id, actor_role=role)
    session.clear()
    return jsonify({"success": True, "message": "Logged out"})


@auth_api.route("/me", methods=["GET"])
def me():
    user = UserRepository().find_one({"_id": session.get("user_id")}) if session.get("user_id") else None
    if user:
        user.pop("password_hash", None)
    return jsonify({"success": True, "data": user})
