from flask import Blueprint, redirect, session, url_for

from app.utils.decorators import login_required

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="")


@dashboard_bp.route("/dashboard")
@login_required
def index():
    endpoint_by_role = {
        "CANDIDATE": "candidate.dashboard",
        "RECRUITER": "recruiter.dashboard",
        "ADMIN": "admin.dashboard",
    }
    endpoint = endpoint_by_role.get(session.get("role"))
    if endpoint is None:
        return redirect(url_for("auth.login"))
    return redirect(url_for(endpoint))
