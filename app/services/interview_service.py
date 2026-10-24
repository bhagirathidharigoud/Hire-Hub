from datetime import datetime, timezone

from app.repositories.application_repository import ApplicationRepository
from app.repositories.interview_repository import InterviewRepository
from app.repositories.job_repository import JobRepository


class InterviewService:
    def __init__(self, interview_repository=None, application_repository=None, job_repository=None):
        self.interview_repository = interview_repository or InterviewRepository()
        self.application_repository = application_repository or ApplicationRepository()
        self.job_repository = job_repository or JobRepository()

    def schedule(self, payload):
        application_id = payload.get("application_id")
        recruiter_id = payload.get("recruiter_id")
        date = (payload.get("date") or "").strip()
        time = (payload.get("time") or "").strip()
        interview_type = payload.get("type", "ONLINE")
        if not application_id or not recruiter_id:
            raise ValueError("Application and recruiter are required")
        if not date or not time:
            raise ValueError("Interview date and time are required")
        try:
            scheduled_at = datetime.strptime(f"{date} {time}", "%Y-%m-%d %H:%M")
        except ValueError as exc:
            raise ValueError("Enter a valid interview date and time") from exc
        if scheduled_at <= datetime.now():
            raise ValueError("Interview must be scheduled in the future")
        if interview_type not in {"ONLINE", "IN_PERSON", "PHONE"}:
            raise ValueError("Invalid interview type")

        application = self.application_repository.find_one({"_id": application_id})
        if not application:
            raise ValueError("Application not found")
        job = self.job_repository.find_one({"_id": application.get("job_id")})
        if not job or job.get("recruiter_id") != recruiter_id:
            raise ValueError("You cannot schedule an interview for this application")
        if application.get("status") not in {"APPLIED", "UNDER_REVIEW", "SHORTLISTED"}:
            raise ValueError("This application cannot be scheduled for an interview")
        if self.interview_repository.find_one({"application_id": application_id, "status": "SCHEDULED"}):
            raise ValueError("An interview is already scheduled for this application")
        interview = {
            "application_id": application["_id"],
            "candidate_id": application["candidate_id"],
            "recruiter_id": recruiter_id,
            "date": date,
            "time": time,
            "type": interview_type,
            "meeting_link": payload.get("meeting_link", ""),
            "status": "SCHEDULED",
            "feedback": "",
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        interview_id = self.interview_repository.insert_one(interview)
        interview["_id"] = interview_id
        self.application_repository.update_one({"_id": payload["application_id"]}, {"status": "INTERVIEW_SCHEDULED"})
        return interview

    def list_for_candidate(self, candidate_id):
        return self.interview_repository.find_all({"candidate_id": candidate_id})

    def list_for_recruiter(self, recruiter_id):
        return self.interview_repository.find_all({"recruiter_id": recruiter_id})
