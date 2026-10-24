from urllib.parse import urljoin, urlparse

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.exceptions import HireHubError
from app.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from app.services.auth_service import AuthService
from app.services.notification_service import NotificationService
from app.utils.decorators import login_required


auth_bp = Blueprint("auth", __name__, url_prefix="")


@auth_bp.route("/", methods=["GET"])
def home():
    return render_template("home.html")


@auth_bp.route("/login", methods=["GET", "POST"])
def login():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        email = request.form.get("email")
        password = request.form.get("password")
        try:
            user = AuthService().login_user(email, password)
            session.clear()
            session["user_id"] = str(user.get("_id"))
            session["role"] = user.get("role")
            session.permanent = True
            AuditLogService().log_event("auth.login", "User signed in", actor_id=str(user.get("_id")), actor_role=user.get("role"))
            next_url = request.args.get("next") or request.form.get("next")
            if next_url and urlparse(urljoin(request.host_url, next_url)).netloc == request.host:
                return redirect(next_url)
            return redirect(url_for("dashboard.index"))
        except (HireHubError, ValueError) as exc:
            return render_template("auth/login.html", error=str(exc), next=request.args.get("next", "")), 400
    return render_template("auth/login.html")


@auth_bp.route("/register", methods=["GET", "POST"])
def register():
    if "user_id" in session:
        return redirect(url_for("dashboard.index"))

    if request.method == "POST":
        payload = request.form.to_dict()
        confirm_password = request.form.get("confirm_password")
        if payload.get("password") != confirm_password:
            return render_template("auth/register.html", error="Passwords do not match", form=payload), 400
        try:
            user = AuthService().register_user(payload)
            session.clear()
            session["user_id"] = str(user.get("_id"))
            session["role"] = user.get("role")
            session.permanent = True
            AuditLogService().log_event("auth.register", "User account created", actor_id=str(user.get("_id")), actor_role=user.get("role"))
            return redirect(url_for("dashboard.index"))
        except (HireHubError, ValueError) as exc:
            return render_template("auth/register.html", error=str(exc), form=payload), 400
    return render_template("auth/register.html")


@auth_bp.route("/profile", methods=["GET", "POST"])
@login_required
def profile():
    users = UserRepository()
    user = users.find_one({"_id": session["user_id"]})
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return render_template("account/profile.html", user=user, error="Name is required."), 400
        updates = {
            "name": name,
            "phone": request.form.get("phone", "").strip(),
        }
        if user.get("role") == "CANDIDATE":
            updates["location"] = request.form.get("location", "").strip()
            updates["skills"] = [
                skill.strip()
                for skill in request.form.get("skills", "").split(",")
                if skill.strip()
            ]
        users.update_one({"_id": session["user_id"]}, updates)
        AuditLogService().log_event(
            "user.profile_updated",
            "User updated their profile",
            actor_id=session["user_id"],
            actor_role=session.get("role"),
        )
        flash("Your profile was saved.", "success")
        return redirect(url_for("auth.profile"))
    return render_template("account/profile.html", user=user)


@auth_bp.route("/notifications")
@login_required
def notifications():
    data = NotificationService().list_for_user(session["user_id"])
    return render_template("account/notifications.html", notifications=data)


@auth_bp.route("/notifications/<notification_id>/read", methods=["POST"])
@login_required
def mark_notification_read(notification_id):
    if not NotificationService().mark_read(session["user_id"], notification_id):
        abort(404)
    return redirect(url_for("auth.notifications"))


@auth_bp.route("/logout", methods=["GET", "POST"])
def logout():
    user_id = session.get("user_id")
    role = session.get("role")
    if user_id:
        AuditLogService().log_event("auth.logout", "User signed out", actor_id=user_id, actor_role=role)
    session.clear()
    return redirect(url_for("auth.login"))
