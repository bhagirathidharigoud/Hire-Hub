import csv
from io import StringIO

from flask import Blueprint, flash, make_response, render_template, request, session

from app.repositories.application_repository import ApplicationRepository

from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from app.services.reporting_service import ReportingService
from app.utils.decorators import login_required, role_required

admin_bp = Blueprint("admin", __name__, url_prefix="/admin")


@admin_bp.route("/dashboard")
@login_required
@role_required("ADMIN")
def dashboard():
    users = UserRepository().find_all()
    jobs = JobRepository().find_all()
    applications = ApplicationRepository().find_all()
    logs = AuditLogService().list_recent(limit=6)
    logs = [
        {
            **log,
            "actor": UserRepository().find_one({"_id": log.get("actor_id")}) if log.get("actor_id") else None,
        }
        for log in logs
    ]
    pending_applications = sum(application.get("status") in {"APPLIED", "UNDER_REVIEW"} for application in applications)
    companies = {job.get("company_id") or job.get("company_name") for job in jobs if job.get("company_id") or job.get("company_name")}
    return render_template(
        "admin/dashboard.html",
        users=users,
        jobs=jobs,
        applications=applications,
        logs=logs,
        pending_applications=pending_applications,
        company_count=len(companies),
    )


@admin_bp.route("/companies")
@login_required
@role_required("ADMIN")
def companies():
    jobs = JobRepository().find_all()
    recruiters = {user["_id"]: user for user in UserRepository().find_all() if user.get("role") == "RECRUITER"}
    company_map = {}
    for job in jobs:
        company_id = job.get("company_id") or job.get("company_name")
        if not company_id:
            continue
        company = company_map.setdefault(company_id, {
            "id": company_id,
            "name": job.get("company_name") or recruiters.get(job.get("recruiter_id"), {}).get("company_profile", {}).get("name") or "Company profile needed",
            "recruiter": recruiters.get(job.get("recruiter_id"), {}),
            "jobs": 0,
            "open_jobs": 0,
        })
        company["jobs"] += 1
        company["open_jobs"] += job.get("status") == "OPEN"
    return render_template("admin/companies.html", companies=list(company_map.values()))


@admin_bp.route("/users", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def users():
    if request.method == "POST":
        user_id = request.form.get("user_id")
        if user_id:
            user = UserRepository().find_one({"_id": user_id})
            if user:
                role = request.form.get("role", user.get("role"))
                is_active = request.form.get("is_active") == "on"
                if role not in {"CANDIDATE", "RECRUITER", "ADMIN"}:
                    flash("Select a valid user role.", "danger")
                    return render_template("admin/users.html", users=UserRepository().find_all()), 400
                if user_id == session.get("user_id") and (role != "ADMIN" or not is_active):
                    flash("You cannot remove admin access or deactivate your own account.", "warning")
                    return render_template("admin/users.html", users=UserRepository().find_all()), 400
                UserRepository().update_one(
                    {"_id": user_id},
                    {"role": role, "is_active": is_active},
                )
                user["role"] = role
                user["is_active"] = is_active
                AuditLogService().log_event(
                    "user.updated",
                    f"User {user.get('email')} updated by admin",
                    actor_id=session.get("user_id"),
                    actor_role="ADMIN",
                    metadata={"user_id": user_id, "role": user["role"], "is_active": user["is_active"]},
                )

    users_list = UserRepository().find_all()
    return render_template("admin/users.html", users=users_list)


@admin_bp.route("/jobs", methods=["GET", "POST"])
@login_required
@role_required("ADMIN")
def jobs():
    if request.method == "POST":
        job_id = request.form.get("job_id")
        action = request.form.get("action")
        if job_id:
            job = JobRepository().find_one({"_id": job_id})
            if not job:
                return render_template("admin/jobs.html", jobs=JobRepository().find_all(), error="Job not found")
            if action == "toggle_status":
                new_status = "CLOSED" if job.get("status") == "OPEN" else "OPEN"
                JobRepository().update_one({"_id": job_id}, {"status": new_status})
                AuditLogService().log_event(
                    "job.status_changed",
                    f"Job {job.get('title')} status changed to {new_status}",
                    actor_id=session.get("user_id"),
                    actor_role="ADMIN",
                    metadata={"job_id": job_id, "status": new_status},
                )
            elif action == "delete":
                JobRepository().delete_one({"_id": job_id})
                AuditLogService().log_event(
                    "job.deleted",
                    f"Job {job.get('title')} deleted by admin",
                    actor_id=session.get("user_id"),
                    actor_role="ADMIN",
                    metadata={"job_id": job_id},
                )

    jobs_list = JobRepository().find_all()
    return render_template("admin/jobs.html", jobs=jobs_list)


@admin_bp.route("/applications")
@login_required
@role_required("ADMIN")
def applications():
    applications_list = ApplicationRepository().find_all(sort=("applied_at", True))
    candidates = {user["_id"]: user for user in UserRepository().find_all()}
    jobs = {job["_id"]: job for job in JobRepository().find_all()}
    for application in applications_list:
        application["candidate"] = candidates.get(application.get("candidate_id"))
        application["job"] = jobs.get(application.get("job_id"))
    return render_template("admin/applications.html", applications=applications_list)


@admin_bp.route("/analytics")
@login_required
@role_required("ADMIN")
def analytics():
    report = ReportingService().build_report()
    stats = report["stats"]
    chart_data = {
        "roles": {"labels": ["Candidates", "Recruiters", "Admins"], "values": [stats["candidate_count"], stats["recruiter_count"], stats["admin_count"]]},
        "applications": {"labels": list(report["application_statuses"]), "values": list(report["application_statuses"].values())},
        "work_modes": {"labels": list(report["job_modes"]), "values": list(report["job_modes"].values())},
    }
    return render_template("admin/analytics.html", stats=stats, chart_data=chart_data, report=report)


@admin_bp.route("/audit-logs")
@login_required
@role_required("ADMIN")
def audit_logs():
    logs = AuditLogService().list_recent(limit=25)
    return render_template("admin/audit_logs.html", logs=logs)


@admin_bp.route("/reports")
@login_required
@role_required("ADMIN")
def reports():
    report = ReportingService().build_report()
    return render_template("admin/reports.html", **report)


@admin_bp.route("/reports/export.csv")
@login_required
@role_required("ADMIN")
def export_report():
    report = ReportingService().build_report()
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Report", "Metric", "Value"])
    for key, value in report["stats"].items():
        writer.writerow(["Summary", key, value])
    for key, value in report["application_statuses"].items():
        writer.writerow(["Applications by status", key, value])
    for key, value in report["job_modes"].items():
        writer.writerow(["Jobs by work mode", key, value])
    for key, value in report["job_types"].items():
        writer.writerow(["Jobs by employment type", key, value])
    response = make_response(output.getvalue())
    response.headers["Content-Type"] = "text/csv; charset=utf-8"
    response.headers["Content-Disposition"] = "attachment; filename=hirehub-report.csv"
    return response
