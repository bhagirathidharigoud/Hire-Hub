from datetime import date

from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for

from app.services.application_service import ApplicationService
from app.services.interview_service import InterviewService
from app.services.job_service import JobService
from app.services.notification_service import NotificationService
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.audit_log_service import AuditLogService
from app.utils.decorators import login_required, role_required

recruiter_bp = Blueprint("recruiter", __name__, url_prefix="/recruiter")


@recruiter_bp.route("/dashboard")
@login_required
@role_required("RECRUITER")
def dashboard():
    user_id = session.get("user_id")
    jobs = JobService().search_jobs(recruiter_id=user_id)
    apps = ApplicationService().for_recruiter(user_id)
    interviews = InterviewService().list_for_recruiter(user_id)
    notifications = NotificationService().list_for_user(user_id)
    users = {user["_id"]: user for user in UserRepository().find_all()}
    for application in apps:
        application["candidate"] = users.get(application.get("candidate_id"))
    upcoming = sorted(
        (interview for interview in interviews if interview.get("status") == "SCHEDULED" and interview.get("date", "") >= date.today().isoformat()),
        key=lambda interview: (interview.get("date", ""), interview.get("time", "")),
    )
    metrics = {
        "active_jobs": sum(job.get("status") == "OPEN" for job in jobs),
        "applications": len(apps),
        "shortlisted": sum(app.get("status") == "SHORTLISTED" for app in apps),
        "upcoming_interviews": len(upcoming),
    }
    return render_template(
        "recruiter/dashboard.html",
        jobs=jobs,
        applications=apps,
        interviews=upcoming[:4],
        notifications=notifications,
        metrics=metrics,
        recent_applications=sorted(apps, key=lambda app: app.get("applied_at", ""), reverse=True)[:6],
    )


@recruiter_bp.route("/jobs")
@login_required
@role_required("RECRUITER")
def jobs():
    user_id = session.get("user_id")
    jobs_list = JobService().search_jobs(recruiter_id=user_id)
    return render_template("recruiter/jobs.html", jobs=jobs_list)


@recruiter_bp.route("/applicants")
@login_required
@role_required("RECRUITER")
def applicants():
    applications = ApplicationService().for_recruiter(session["user_id"])
    users = {user["_id"]: user for user in UserRepository().find_all()}
    for application in applications:
        application["candidate"] = users.get(application.get("candidate_id"))
    return render_template("recruiter/applicants.html", applications=applications)


@recruiter_bp.route("/interviews")
@login_required
@role_required("RECRUITER")
def interviews():
    recruiter_id = session.get("user_id")
    interviews_list = InterviewService().list_for_recruiter(recruiter_id)
    applications = ApplicationService().for_recruiter(recruiter_id)
    users = {user["_id"]: user for user in UserRepository().find_all()}
    for interview in interviews_list:
        interview["application"] = next(
            (application for application in applications if application.get("_id") == interview.get("application_id")),
            None,
        )
        interview["candidate"] = users.get(interview.get("candidate_id"))
    return render_template("recruiter/interviews.html", interviews=interviews_list)


@recruiter_bp.route("/job/new", methods=["GET", "POST"])
@login_required
@role_required("RECRUITER")
def new_job():
    recruiter = UserRepository().find_one({"_id": session["user_id"]}) or {}
    if request.method == "POST":
        payload = request.form.to_dict()
        payload["skills"] = [skill.strip() for skill in payload.get("skills", "").split(",") if skill.strip()]
        payload["recruiter_id"] = session.get("user_id")
        recruiter = UserRepository().find_one({"_id": session["user_id"]}) or {}
        company = recruiter.get("company_profile", {})
        payload["company_id"] = recruiter.get("_id")
        payload["company_name"] = company.get("name", "")
        try:
            JobService().create_job(payload)
        except ValueError as exc:
            return render_template("recruiter/job_form.html", error=str(exc), form=payload, recruiter_has_company=bool(recruiter.get("company_profile", {}).get("name"))), 400
        AuditLogService().log_event("job.created", f"Job {payload.get('title')} created", actor_id=session["user_id"], actor_role="RECRUITER")
        flash("Job posted successfully.", "success")
        return redirect(url_for("recruiter.jobs"))
    return render_template("recruiter/job_form.html", recruiter_has_company=bool(recruiter.get("company_profile", {}).get("name")))


@recruiter_bp.route("/company", methods=["GET", "POST"])
@login_required
@role_required("RECRUITER")
def company_profile():
    users = UserRepository()
    recruiter = users.find_one({"_id": session["user_id"]}) or {}
    company = recruiter.get("company_profile", {})
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            return render_template("recruiter/company.html", company=company, error="Company name is required."), 400
        company = {
            "name": name,
            "website": request.form.get("website", "").strip(),
            "description": request.form.get("description", "").strip(),
            "location": request.form.get("location", "").strip(),
        }
        users.update_one({"_id": session["user_id"]}, {"company_profile": company})
        AuditLogService().log_event("company.profile_updated", "Recruiter updated company profile", actor_id=session["user_id"], actor_role="RECRUITER")
        flash("Company profile saved.", "success")
        return redirect(url_for("recruiter.company_profile"))
    return render_template("recruiter/company.html", company=company)


@recruiter_bp.route("/jobs/<job_id>/status", methods=["POST"])
@login_required
@role_required("RECRUITER")
def update_job_status(job_id):
    job = JobRepository().find_one({"_id": job_id})
    if not job or job.get("recruiter_id") != session["user_id"]:
        abort(404)
    status = request.form.get("status")
    if status not in {"OPEN", "CLOSED"}:
        flash("Invalid job status.", "danger")
        return redirect(url_for("recruiter.jobs"))
    JobRepository().update_one({"_id": job_id}, {"status": status})
    AuditLogService().log_event("job.status_changed", f"Job {job.get('title')} status changed to {status}", actor_id=session["user_id"], actor_role="RECRUITER", metadata={"job_id": job_id, "status": status})
    flash("Job status updated.", "success")
    return redirect(url_for("recruiter.jobs"))


@recruiter_bp.route("/applications/<application_id>/status", methods=["POST"])
@login_required
@role_required("RECRUITER")
def update_application_status(application_id):
    application = ApplicationRepository().find_one({"_id": application_id})
    if not application:
        abort(404)
    job = JobRepository().find_one({"_id": application.get("job_id")})
    if not job or job.get("recruiter_id") != session["user_id"]:
        abort(404)
    status = request.form.get("status")
    if status not in {"UNDER_REVIEW", "SHORTLISTED", "SELECTED", "REJECTED"}:
        flash("Invalid application status.", "danger")
        return redirect(url_for("recruiter.applicants"))
    ApplicationService().update_status(application_id, status)
    AuditLogService().log_event("application.status_changed", f"Application status changed to {status}", actor_id=session["user_id"], actor_role="RECRUITER", metadata={"application_id": application_id, "job_id": job["_id"]})
    NotificationService().create(
        application["candidate_id"],
        f"Your application for {job.get('title', 'a job')} is now {status.replace('_', ' ').lower()}.",
    )
    flash("Application status updated.", "success")
    return redirect(url_for("recruiter.applicants"))


@recruiter_bp.route("/applications/<application_id>/interview", methods=["POST"])
@login_required
@role_required("RECRUITER")
def schedule_interview(application_id):
    application = ApplicationRepository().find_one({"_id": application_id})
    if not application:
        abort(404)
    job = JobRepository().find_one({"_id": application.get("job_id")})
    if not job or job.get("recruiter_id") != session["user_id"]:
        abort(404)
    payload = {
        "application_id": application_id,
        "recruiter_id": session["user_id"],
        "date": request.form.get("date", "").strip(),
        "time": request.form.get("time", "").strip(),
        "type": request.form.get("type", "ONLINE"),
        "meeting_link": request.form.get("meeting_link", "").strip(),
    }
    if not payload["date"] or not payload["time"]:
        flash("Interview date and time are required.", "danger")
        return redirect(url_for("recruiter.applicants"))
    try:
        InterviewService().schedule(payload)
    except ValueError as exc:
        flash(str(exc), "danger")
        return redirect(url_for("recruiter.applicants"))
    AuditLogService().log_event("interview.scheduled", "Recruiter scheduled an interview", actor_id=session["user_id"], actor_role="RECRUITER", metadata={"application_id": application_id, "job_id": job["_id"]})
    NotificationService().create(
        application["candidate_id"],
        f"An interview for {job.get('title', 'your application')} has been scheduled on {payload['date']} at {payload['time']}.",
        "INFO",
    )
    flash("Interview scheduled.", "success")
    return redirect(url_for("recruiter.interviews"))
