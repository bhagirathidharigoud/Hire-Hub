import os
from datetime import date
from urllib.parse import urljoin, urlparse
from uuid import uuid4

from flask import Blueprint, abort, current_app, flash, redirect, render_template, request, send_from_directory, session, url_for
from werkzeug.utils import secure_filename

from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository
from app.services.application_service import ApplicationService
from app.services.interview_service import InterviewService
from app.services.job_service import JobService
from app.services.matching_service import MatchingService
from app.services.notification_service import NotificationService
from app.services.audit_log_service import AuditLogService
from app.utils.validators import is_allowed_resume
from app.utils.decorators import login_required, role_required

candidate_bp = Blueprint("candidate", __name__, url_prefix="/candidate")


@candidate_bp.route("/dashboard")
@login_required
@role_required("CANDIDATE")
def dashboard():
    user_id = session.get("user_id")
    apps = ApplicationService().my_applications(user_id)
    interviews = InterviewService().list_for_candidate(user_id)
    notifications = NotificationService().list_for_user(user_id)
    jobs = MatchingService().recommend_for_candidate(user_id, limit=3)
    user = UserRepository().find_one({"_id": user_id}) or {}
    saved_job_ids = user.get("saved_job_ids", [])
    job_map = {job["_id"]: job for job in JobRepository().find_all()}
    for application in apps:
        application["job"] = job_map.get(application.get("job_id"))
    upcoming_interviews = sorted(
        (
            interview
            for interview in interviews
            if interview.get("status") == "SCHEDULED" and interview.get("date", "") >= date.today().isoformat()
        ),
        key=lambda interview: (interview.get("date", ""), interview.get("time", "")),
    )
    application_counts = {
        "shortlisted": sum(app.get("status") == "SHORTLISTED" for app in apps),
        "interviews": sum(app.get("status") == "INTERVIEW_SCHEDULED" for app in apps),
        "selections": sum(app.get("status") == "SELECTED" for app in apps),
    }
    return render_template(
        "candidate/dashboard.html",
        applications=apps,
        interviews=interviews,
        notifications=notifications,
        jobs=jobs,
        user=user,
        application_counts=application_counts,
        upcoming_interviews=upcoming_interviews[:2],
        recent_applications=sorted(apps, key=lambda app: app.get("applied_at", ""), reverse=True)[:4],
        saved_job_ids=saved_job_ids,
    )


@candidate_bp.route("/recommendations")
@login_required
@role_required("CANDIDATE")
def recommendations():
    jobs = MatchingService().recommend_for_candidate(session["user_id"], limit=50)
    return render_template("jobs/jobs.html", jobs=jobs, recommendations=True)


@candidate_bp.route("/profile", methods=["GET", "POST"])
@login_required
@role_required("CANDIDATE")
def profile():
    users = UserRepository()
    user = users.find_one({"_id": session["user_id"]})
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        if not name:
            flash("Name is required.", "danger")
            return render_template("candidate/profile.html", user=user), 400
        profile_data = {
            "name": name,
            "phone": request.form.get("phone", "").strip(),
            "location": request.form.get("location", "").strip(),
            "skills": [skill.strip() for skill in request.form.get("skills", "").split(",") if skill.strip()],
        }
        users.update_one({"_id": session["user_id"]}, profile_data)
        AuditLogService().log_event("candidate.profile_updated", "Candidate updated their profile", actor_id=session["user_id"], actor_role="CANDIDATE")
        flash("Your profile was saved.", "success")
        return redirect(url_for("candidate.profile"))
    return render_template("candidate/profile.html", user=user)


@candidate_bp.route("/applications")
@login_required
@role_required("CANDIDATE")
def applications():
    user_id = session.get("user_id")
    data = ApplicationService().my_applications(user_id)
    jobs = {job["_id"]: job for job in JobRepository().find_all()}
    for application in data:
        application["job"] = jobs.get(application.get("job_id"))
    return render_template("candidate/applications.html", applications=data)


@candidate_bp.route("/saved-jobs")
@login_required
@role_required("CANDIDATE")
def saved_jobs():
    user = UserRepository().find_one({"_id": session["user_id"]}) or {}
    saved_ids = user.get("saved_job_ids", [])
    jobs = [job for job in JobRepository().find_all({"_id": {"$in": saved_ids}}) if job.get("status") == "OPEN"]
    return render_template("jobs/jobs.html", jobs=jobs, saved_job_ids=saved_ids, saved_jobs_page=True)


@candidate_bp.route("/jobs/<job_id>/save", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def toggle_saved_job(job_id):
    job = JobRepository().find_one({"_id": job_id})
    if not job or job.get("status") != "OPEN":
        abort(404)
    users = UserRepository()
    user = users.find_one({"_id": session["user_id"]}) or {}
    saved_ids = set(user.get("saved_job_ids", []))
    if job_id in saved_ids:
        saved_ids.remove(job_id)
        flash("Job removed from your saved list.", "info")
    else:
        saved_ids.add(job_id)
        flash("Job saved.", "success")
    users.update_one({"_id": session["user_id"]}, {"saved_job_ids": sorted(saved_ids)})
    next_url = request.form.get("next", "")
    if next_url and urlparse(urljoin(request.host_url, next_url)).netloc == request.host:
        return redirect(next_url)
    return redirect(url_for("candidate.saved_jobs"))


@candidate_bp.route("/interviews")
@login_required
@role_required("CANDIDATE")
def interviews():
    interviews_list = InterviewService().list_for_candidate(session["user_id"])
    applications = ApplicationService().my_applications(session["user_id"])
    jobs = {job["_id"]: job for job in JobRepository().find_all()}
    application_map = {application["_id"]: application for application in applications}
    for interview in interviews_list:
        application = application_map.get(interview.get("application_id"))
        interview["job"] = jobs.get(application.get("job_id")) if application else None
    return render_template("candidate/interviews.html", interviews=interviews_list)


@candidate_bp.route("/applications/<application_id>/withdraw", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def withdraw_application(application_id):
    application = ApplicationRepository().find_one(
        {"_id": application_id, "candidate_id": session["user_id"]}
    )
    if not application:
        abort(404)
    if application.get("status") not in {"APPLIED", "UNDER_REVIEW", "SHORTLISTED"}:
        flash("This application can no longer be withdrawn.", "warning")
    else:
        ApplicationService().update_status(application_id, "WITHDRAWN")
        flash("Your application was withdrawn.", "success")
    return redirect(url_for("candidate.applications"))


@candidate_bp.route("/resume", methods=["GET", "POST"])
@login_required
@role_required("CANDIDATE")
def resume():
    users = UserRepository()
    user = users.find_one({"_id": session["user_id"]})
    if request.method == "POST":
        upload = request.files.get("resume")
        if upload is None or not upload.filename:
            flash("Choose a resume file to upload.", "danger")
            return render_template("candidate/resume.html", resume=user.get("resume")), 400
        original_name = secure_filename(upload.filename)
        extension = os.path.splitext(original_name)[1].lower()
        if extension not in {".pdf", ".doc", ".docx"} or not is_allowed_resume(original_name, upload.mimetype):
            flash("Resume must be a PDF, DOC, or DOCX file.", "danger")
            return render_template("candidate/resume.html", resume=user.get("resume")), 400

        stored_name = f"{uuid4().hex}{extension}"
        upload_folder = os.path.abspath(current_app.config["UPLOAD_FOLDER"])
        os.makedirs(upload_folder, exist_ok=True)
        upload.save(os.path.join(upload_folder, stored_name))
        resume_data = {"filename": stored_name, "original_name": original_name}
        users.update_one({"_id": session["user_id"]}, {"resume": resume_data})
        AuditLogService().log_event("candidate.resume_uploaded", "Candidate uploaded a resume", actor_id=session["user_id"], actor_role="CANDIDATE")
        flash("Your resume was uploaded.", "success")
        return redirect(url_for("candidate.resume"))
    return render_template("candidate/resume.html", resume=user.get("resume"))


@candidate_bp.route("/resume/download")
@login_required
@role_required("CANDIDATE")
def download_resume():
    user = UserRepository().find_one({"_id": session["user_id"]})
    resume = user.get("resume") if user else None
    if not resume or not resume.get("filename"):
        abort(404)
    return send_from_directory(
        os.path.abspath(current_app.config["UPLOAD_FOLDER"]),
        resume["filename"],
        as_attachment=True,
        download_name=resume.get("original_name", "resume"),
    )


@candidate_bp.route("/notifications")
@login_required
@role_required("CANDIDATE")
def notifications():
    user_id = session.get("user_id")
    data = NotificationService().list_for_user(user_id)
    return render_template("candidate/notifications.html", notifications=data)


@candidate_bp.route("/notifications/<notification_id>/read", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def mark_notification_read(notification_id):
    if not NotificationService().mark_read(session["user_id"], notification_id):
        abort(404)
    return redirect(url_for("candidate.notifications"))


@candidate_bp.route("/notifications/read-all", methods=["POST"])
@login_required
@role_required("CANDIDATE")
def mark_all_notifications_read():
    NotificationService().mark_read(session["user_id"])
    return redirect(url_for("candidate.notifications"))


@candidate_bp.route("/jobs")
@login_required
@role_required("CANDIDATE")
def jobs():
    filters = {
        key: request.args.get(key, "")
        for key in ("keyword", "location", "work_mode", "employment_type", "skills", "min_salary", "max_salary")
    }
    try:
        jobs = JobService().search_jobs(**filters, status="OPEN")
    except ValueError as exc:
        return render_template("jobs/jobs.html", jobs=[], search_error=str(exc)), 400
    return render_template("jobs/jobs.html", jobs=jobs, total=len(jobs), saved_job_ids=UserRepository().find_one({"_id": session["user_id"]}).get("saved_job_ids", []))
