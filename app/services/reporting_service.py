from collections import Counter

from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.repositories.user_repository import UserRepository


class ReportingService:
    def build_report(self):
        users = UserRepository().find_all()
        jobs = JobRepository().find_all()
        applications = ApplicationRepository().find_all()
        roles = Counter(user.get("role", "UNKNOWN") for user in users)
        application_statuses = Counter(app.get("status", "UNKNOWN") for app in applications)
        job_modes = Counter(job.get("work_mode", "UNSPECIFIED") for job in jobs)
        job_types = Counter(job.get("employment_type", "UNSPECIFIED") for job in jobs)
        active_jobs = [job for job in jobs if job.get("status") == "OPEN"]
        return {
            "stats": {
                "total_users": len(users),
                "active_users": sum(1 for user in users if user.get("is_active", True)),
                "total_jobs": len(jobs),
                "open_jobs": len(active_jobs),
                "total_applications": len(applications),
                "candidate_count": roles["CANDIDATE"],
                "recruiter_count": roles["RECRUITER"],
                "admin_count": roles["ADMIN"],
                "interviews": application_statuses["INTERVIEW_SCHEDULED"],
                "selected": application_statuses["SELECTED"],
            },
            "application_statuses": dict(sorted(application_statuses.items())),
            "job_modes": dict(sorted(job_modes.items())),
            "job_types": dict(sorted(job_types.items())),
            "users": users,
            "jobs": jobs,
            "applications": applications,
        }
