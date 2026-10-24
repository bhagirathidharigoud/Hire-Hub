from flask import Blueprint, flash, redirect, render_template, request, session, url_for

from app.exceptions import DuplicateApplicationError, JobClosedError, JobNotFoundError
from app.services.audit_log_service import AuditLogService
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.job_service import JobService
from app.services.notification_service import NotificationService
from app.utils.decorators import login_required, role_required

jobs_bp = Blueprint("jobs", __name__, url_prefix="/jobs")


@jobs_bp.route("", methods=["GET"])
def jobs_list():
    filters = {
        key: request.args.get(key, "")
        for key in (
            "keyword", "location", "work_mode", "employment_type", "min_experience", "max_experience",
            "min_salary", "max_salary", "company", "skills",
        )
    }
    try:
        jobs = JobService().search_jobs(**filters, status="OPEN")
    except ValueError as exc:
        return render_template("jobs/jobs.html", jobs=[], search_error=str(exc)), 400
    sort = request.args.get("sort", "recent")
    if sort == "salary_high":
        jobs.sort(key=lambda job: job.get("salary_max") or 0, reverse=True)
    elif sort == "salary_low":
        jobs.sort(key=lambda job: job.get("salary_min") or 0)
    else:
        jobs.sort(key=lambda job: job.get("posted_date", job.get("created_at", "")), reverse=True)
    page = max(request.args.get("page", 1, type=int), 1)
    per_page = 9
    total = len(jobs)
    page_count = max((total + per_page - 1) // per_page, 1)
    page = min(page, page_count)
    previous_url = None
    next_url = None
    if page > 1:
        previous_args = request.args.to_dict()
        previous_args["page"] = page - 1
        previous_url = url_for("jobs.jobs_list", **previous_args)
    if page < page_count:
        next_args = request.args.to_dict()
        next_args["page"] = page + 1
        next_url = url_for("jobs.jobs_list", **next_args)
    return render_template(
        "jobs/jobs.html",
        jobs=jobs[(page - 1) * per_page:page * per_page],
        total=total,
        page=page,
        page_count=page_count,
        sort=sort,
        filters=filters,
        previous_url=previous_url,
        next_url=next_url,
    )


@jobs_bp.route("/<job_id>", methods=["GET"])
def job_detail(job_id):
    job = JobService().get_job_by_id(job_id)
    return render_template("jobs/job_detail.html", job=job)


@jobs_bp.route("/<job_id>/apply", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def apply(job_id):
    try:
        application = JobService().apply_to_job(session["user_id"], job_id)
    except (DuplicateApplicationError, JobClosedError, JobNotFoundError) as exc:
        flash(exc.message, "warning")
        return redirect(url_for("jobs.job_detail", job_id=job_id))
    NotificationService().create(
        application["candidate_id"],
        "Your application was submitted successfully.",
        "SUCCESS",
    )
    job = JobRepository().find_one({"_id": job_id})
    if job and job.get("recruiter_id"):
        candidate = UserRepository().find_one({"_id": application["candidate_id"]}) or {}
        NotificationService().create(
            job["recruiter_id"],
            f"{candidate.get('name', 'A candidate')} applied for {job.get('title', 'your job')}.",
        )
    AuditLogService().log_event("application.created", "Candidate applied for a job", actor_id=session["user_id"], actor_role="CANDIDATE", metadata={"job_id": job_id, "application_id": application["_id"]})
    flash("Your application was submitted.", "success")
    return redirect(url_for("candidate.applications"))
