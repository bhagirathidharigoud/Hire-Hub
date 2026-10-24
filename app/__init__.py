import os
from datetime import datetime, timezone
from uuid import uuid4

from flask import Flask, session
from werkzeug.security import generate_password_hash

from app.config import config
from app.extensions import init_extensions
from app.repositories.user_repository import UserRepository
from app.routes.api import register_api_routes
from app.routes.web import register_web_routes
from app.utils.error_handlers import register_error_handlers


def seed_demo_data(app):
    mongo_db = app.extensions.get("mongo_db")
    users = [
        {
            "_id": str(uuid4()),
            "name": "Aisha Candidate",
            "email": "candidate@example.com",
            "phone": "9876543210",
            "password_hash": generate_password_hash("secret123"),
            "role": "CANDIDATE",
            "is_active": True,
        },
        {
            "_id": str(uuid4()),
            "name": "Rohan Recruiter",
            "email": "recruiter@example.com",
            "phone": "9123456780",
            "password_hash": generate_password_hash("secret123"),
            "role": "RECRUITER",
            "is_active": True,
        },
        {
            "_id": str(uuid4()),
            "name": "Meera Admin",
            "email": "admin@example.com",
            "phone": "9988776655",
            "password_hash": generate_password_hash("secret123"),
            "role": "ADMIN",
            "is_active": True,
        },
    ]
    jobs = [
        {
            "_id": str(uuid4()),
            "title": "Python Developer",
            "description": "Build and maintain Flask APIs and backend services.",
            "company_id": "company_1",
            "recruiter_id": "",
            "location": "Bengaluru",
            "work_mode": "HYBRID",
            "employment_type": "FULL_TIME",
            "skills": ["Python", "Flask", "REST APIs"],
            "status": "OPEN",
        },
        {
            "_id": str(uuid4()),
            "title": "Frontend Engineer",
            "description": "Create elegant user experiences and responsive dashboards.",
            "company_id": "company_1",
            "recruiter_id": "",
            "location": "Remote",
            "work_mode": "REMOTE",
            "employment_type": "FULL_TIME",
            "skills": ["JavaScript", "Bootstrap", "UI Design"],
            "status": "OPEN",
        },
    ]

    if mongo_db is not None:
        existing_user_emails = {
            user["email"] for user in mongo_db.users.find({}, {"email": 1})
        }
        for user in users:
            if user["email"] not in existing_user_emails:
                mongo_db.users.insert_one(user)
                existing_user_emails.add(user["email"])

        recruiter_user = mongo_db.users.find_one({"role": "RECRUITER"}, {"_id": 1})
        recruiter_id = recruiter_user["_id"] if recruiter_user else ""
        existing_job_titles = {job["title"] for job in mongo_db.jobs.find({}, {"title": 1})}
        for job in jobs:
            if job["title"] in existing_job_titles:
                continue
            job["recruiter_id"] = recruiter_id
            mongo_db.jobs.insert_one(job)
            existing_job_titles.add(job["title"])

        if mongo_db.audit_logs.count_documents({"event_type": "system.bootstrap"}) == 0:
            mongo_db.audit_logs.insert_one(
                {
                    "_id": str(uuid4()),
                    "event_type": "system.bootstrap",
                    "message": "HireHub demo data initialized",
                    "actor_role": "ADMIN",
                    "metadata": {"user_count": len(users), "job_count": len(jobs)},
                    "created_at": datetime.now(timezone.utc).isoformat(),
                }
            )
        return

    store = app.extensions.setdefault("memory_store", {})
    user_store = store.setdefault("users", [])
    existing_user_emails = {user.get("email") for user in user_store}
    for user in users:
        if user["email"] not in existing_user_emails:
            user_store.append(user)
            existing_user_emails.add(user["email"])

    job_store = store.setdefault("jobs", [])
    existing_job_titles = {job.get("title") for job in job_store}
    recruiter_id = next((user["_id"] for user in user_store if user.get("role") == "RECRUITER"), "")
    for job in jobs:
        if job["title"] in existing_job_titles:
            continue
        job["recruiter_id"] = recruiter_id
        job_store.append(job)
        existing_job_titles.add(job["title"])

    audit_logs = store.setdefault("audit_logs", [])
    if not any(log.get("event_type") == "system.bootstrap" for log in audit_logs):
        audit_logs.append(
            {
                "_id": str(uuid4()),
                "event_type": "system.bootstrap",
                "message": "HireHub demo data initialized",
                "actor_role": "ADMIN",
                "metadata": {"user_count": len(users), "job_count": len(jobs)},
                "created_at": datetime.now(timezone.utc).isoformat(),
            }
        )


def create_app(config_name: str = "default"):
    if config_name == "production" and not os.getenv("SECRET_KEY"):
        raise RuntimeError("SECRET_KEY must be configured in production")
    app = Flask(__name__)
    app.config.from_object(config[config_name])
    if config_name == "production":
        app.config["MONGO_REQUIRED"] = True
    if config_name == "production" and "SESSION_COOKIE_SECURE" not in os.environ:
        app.config["SESSION_COOKIE_SECURE"] = True
    init_extensions(app)
    if config_name != "production":
        seed_demo_data(app)
    register_web_routes(app)
    register_api_routes(app)
    register_error_handlers(app)

    @app.before_request
    def validate_session_user():
        user_id = session.get("user_id")
        if not user_id:
            return None
        user = UserRepository().find_one({"_id": user_id})
        if not user or not user.get("is_active", True) or user.get("role") != session.get("role"):
            session.clear()
    return app
    return app
