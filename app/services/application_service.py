from datetime import datetime, timezone

from app.exceptions import ApplicationNotFoundError, InvalidApplicationStatusError
from app.repositories.application_repository import ApplicationRepository


class ApplicationService:
    def __init__(self, application_repository=None):
        self.application_repository = application_repository or ApplicationRepository()

    def get_by_id(self, application_id):
        app = self.application_repository.find_one({"_id": application_id})
        if not app:
            raise ApplicationNotFoundError("Application not found")
        return app

    def my_applications(self, candidate_id):
        return self.application_repository.find_all({"candidate_id": candidate_id})

    def for_recruiter(self, recruiter_id):
        from app.repositories.job_repository import JobRepository

        jobs = JobRepository().find_all({"recruiter_id": recruiter_id})
        job_map = {job["_id"]: job for job in jobs}
        applications = []
        for job_id, job in job_map.items():
            for application in self.application_repository.find_by_job(job_id):
                application["job"] = job
                applications.append(application)
        return applications

    def update_status(self, application_id, status):
        application = self.get_by_id(application_id)
        valid_statuses = {
            "APPLIED",
            "UNDER_REVIEW",
            "SHORTLISTED",
            "INTERVIEW_SCHEDULED",
            "SELECTED",
            "REJECTED",
            "WITHDRAWN",
        }
        if status not in valid_statuses:
            raise InvalidApplicationStatusError("Invalid application status")
        allowed_transitions = {
            "APPLIED": {"UNDER_REVIEW", "SHORTLISTED", "INTERVIEW_SCHEDULED", "SELECTED", "REJECTED", "WITHDRAWN"},
            "UNDER_REVIEW": {"SHORTLISTED", "INTERVIEW_SCHEDULED", "SELECTED", "REJECTED", "WITHDRAWN"},
            "SHORTLISTED": {"INTERVIEW_SCHEDULED", "SELECTED", "REJECTED", "WITHDRAWN"},
            "INTERVIEW_SCHEDULED": {"SELECTED", "REJECTED"},
            "SELECTED": set(),
            "REJECTED": set(),
            "WITHDRAWN": set(),
        }
        if status != application.get("status") and status not in allowed_transitions.get(application.get("status"), set()):
            raise InvalidApplicationStatusError("Application status cannot transition from its current value")
        updates = {
            "status": status,
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.application_repository.update_one({"_id": application_id}, updates)
        application.update(updates)
        return application
