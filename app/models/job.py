from __future__ import annotations

from datetime import datetime, timezone


class Job:
    def __init__(self, title, company_id, recruiter_id, description, skills, experience_min=0, experience_max=0, location="", work_mode="REMOTE", employment_type="FULL_TIME", salary_min=0, salary_max=0, posted_date=None, deadline="", status="OPEN", _id=None):
        self._id = _id
        self.title = title
        self.company_id = company_id
        self.recruiter_id = recruiter_id
        self.description = description
        self.skills = skills or []
        self.experience_min = experience_min
        self.experience_max = experience_max
        self.location = location
        self.work_mode = work_mode
        self.employment_type = employment_type
        self.salary_min = salary_min
        self.salary_max = salary_max
        self.posted_date = posted_date or datetime.now(timezone.utc).isoformat()
        self.deadline = deadline
        self.status = status
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "_id": self._id,
            "title": self.title,
            "company_id": self.company_id,
            "recruiter_id": self.recruiter_id,
            "description": self.description,
            "skills": self.skills,
            "experience_min": self.experience_min,
            "experience_max": self.experience_max,
            "location": self.location,
            "work_mode": self.work_mode,
            "employment_type": self.employment_type,
            "salary_min": self.salary_min,
            "salary_max": self.salary_max,
            "posted_date": self.posted_date,
            "deadline": self.deadline,
            "status": self.status,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
