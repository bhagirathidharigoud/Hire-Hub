from flask import Blueprint, jsonify, request, session

from app.services.notification_service import NotificationService
from app.utils.decorators import api_login_required, api_role_required

notification_api = Blueprint("notification_api", __name__, url_prefix="/api/notifications")


@notification_api.route("", methods=["GET"])
@api_login_required
@api_role_required("CANDIDATE")
def list_notifications():
    data = NotificationService().list_for_user(session["user_id"])
    return jsonify({"success": True, "data": data})


@notification_api.route("/<notification_id>/read", methods=["POST"])
@api_login_required
@api_role_required("CANDIDATE")
def mark_notification_read(notification_id):
    if not NotificationService().mark_read(session["user_id"], notification_id):
        return jsonify({"success": False, "message": "Notification not found"}), 404
    return jsonify({"success": True, "message": "Notification marked as read"})


@notification_api.route("/read-all", methods=["POST"])
@api_login_required
@api_role_required("CANDIDATE")
def mark_all_notifications_read():
    NotificationService().mark_read(session["user_id"])
    return jsonify({"success": True, "message": "Notifications marked as read"})
