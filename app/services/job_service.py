from datetime import date, datetime, timezone

from pymongo.errors import DuplicateKeyError

from app.exceptions import DuplicateApplicationError, JobClosedError, JobNotFoundError
from app.repositories.application_repository import ApplicationRepository
from app.repositories.job_repository import JobRepository
from app.utils.validators import normalize_skills


class JobService:
    def __init__(self, job_repository=None, application_repository=None):
        self.job_repository = job_repository or JobRepository()
        self.application_repository = application_repository or ApplicationRepository()

    def get_all_jobs(self):
        return self.job_repository.find_all()

    def get_job_by_id(self, job_id):
        job = self.job_repository.find_one({"_id": job_id})
        if not job:
            raise JobNotFoundError("Job not found")
        return job

    def create_job(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Job details must be provided as an object")
        title = (payload.get("title") or "").strip()
        description = (payload.get("description") or "").strip()
        if not title or not description:
            raise ValueError("Job title and description are required")
        work_mode = (payload.get("work_mode") or "REMOTE").upper()
        employment_type = (payload.get("employment_type") or "FULL_TIME").upper()
        if work_mode not in {"REMOTE", "HYBRID", "ONSITE"}:
            raise ValueError("Invalid work mode")
        if employment_type not in {"FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP"}:
            raise ValueError("Invalid employment type")
        numeric_fields = ("experience_min", "experience_max", "salary_min", "salary_max")
        values = {}
        try:
            values = {field: int(payload.get(field) or 0) for field in numeric_fields}
        except (TypeError, ValueError) as exc:
            raise ValueError("Experience and salary values must be whole numbers") from exc
        if any(value < 0 for value in values.values()):
            raise ValueError("Experience and salary values cannot be negative")
        if values["experience_max"] and values["experience_max"] < values["experience_min"]:
            raise ValueError("Maximum experience must be greater than or equal to minimum experience")
        if values["salary_max"] and values["salary_max"] < values["salary_min"]:
            raise ValueError("Maximum salary must be greater than or equal to minimum salary")
        deadline = (payload.get("deadline") or "").strip()
        if deadline:
            try:
                date.fromisoformat(deadline)
            except ValueError as exc:
                raise ValueError("Application deadline must be a valid date") from exc
        now = datetime.now(timezone.utc).isoformat()
        job = {
            "title": title,
            "description": description,
            "company_id": payload.get("company_id", ""),
            "company_name": (payload.get("company_name") or "").strip(),
            "recruiter_id": payload.get("recruiter_id", ""),
            "location": (payload.get("location") or "").strip(),
            "work_mode": work_mode,
            "employment_type": employment_type,
            "skills": normalize_skills(payload.get("skills")),
            **values,
            "posted_date": datetime.now(timezone.utc).isoformat(),
            "deadline": deadline,
            "status": "OPEN",
            "created_at": now,
            "updated_at": now,
        }
        job_id = self.job_repository.insert_one(job)
        job["_id"] = job_id
        return job

    def search_jobs(self, **filters):
        allowed_filters = {
            "keyword", "location", "company", "skills", "status", "work_mode",
            "employment_type", "min_salary", "max_salary", "min_experience",
            "max_experience", "salary_min", "salary_max", "experience_min",
            "experience_max", "recruiter_id",
        }
        unknown_filters = set(filters) - allowed_filters
        if unknown_filters:
            raise ValueError(f"Unsupported job filter: {sorted(unknown_filters)[0]}")
        if filters.get("work_mode") not in (None, "", "all"):
            filters["work_mode"] = str(filters["work_mode"]).upper()
            if filters["work_mode"] not in {"REMOTE", "HYBRID", "ONSITE"}:
                raise ValueError("Invalid work mode")
        if filters.get("employment_type") not in (None, "", "all"):
            filters["employment_type"] = str(filters["employment_type"]).upper()
            if filters["employment_type"] not in {"FULL_TIME", "PART_TIME", "CONTRACT", "INTERNSHIP"}:
                raise ValueError("Invalid employment type")
        if filters.get("status") not in (None, "", "all"):
            filters["status"] = str(filters["status"]).upper()
            if filters["status"] not in {"OPEN", "CLOSED"}:
                raise ValueError("Invalid job status")
        for field in ("min_salary", "max_salary", "min_experience", "max_experience"):
            value = filters.get(field)
            if value in (None, "", "all"):
                continue
            try:
                if int(value) < 0:
                    raise ValueError
            except (TypeError, ValueError) as exc:
                raise ValueError(f"{field.replace('_', ' ').title()} must be a non-negative whole number") from exc
        if filters.get("min_salary") and filters.get("max_salary"):
            if int(filters["min_salary"]) > int(filters["max_salary"]):
                raise ValueError("Minimum salary cannot exceed maximum salary")
        if filters.get("min_experience") and filters.get("max_experience"):
            if int(filters["min_experience"]) > int(filters["max_experience"]):
                raise ValueError("Minimum experience cannot exceed maximum experience")
        return self.job_repository.search(**filters)

    def update_job_status(self, job_id, status):
        status = str(status or "").upper()
        if status not in {"OPEN", "CLOSED"}:
            raise ValueError("Job status must be OPEN or CLOSED")
        self.get_job_by_id(job_id)
        return self.job_repository.update_one(
            {"_id": job_id},
            {"status": status, "updated_at": datetime.now(timezone.utc).isoformat()},
        )

    def apply_to_job(self, candidate_id, job_id):
        job = self.get_job_by_id(job_id)
        if job.get("status") != "OPEN":
            raise JobClosedError("Job is closed")
        if self.application_repository.find_by_candidate_and_job(candidate_id, job_id):
            raise DuplicateApplicationError("Duplicate application")

        application = {
            "candidate_id": candidate_id,
            "job_id": job_id,
            "status": "APPLIED",
            "applied_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "recruiter_notes": "",
        }
        try:
            app_id = self.application_repository.insert_one(application)
        except DuplicateKeyError as exc:
            raise DuplicateApplicationError("Duplicate application") from exc
        application["_id"] = app_id
        return application
