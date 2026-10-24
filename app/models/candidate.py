from app.models.user import User


class Candidate(User):
    def __init__(self, name, email, phone, password_hash, role="CANDIDATE", is_active=True, _id=None, location="", skills=None, education="", experience=0, expected_salary=0, notice_period="", resume=None, saved_jobs=None):
        super().__init__(name, email, phone, password_hash, role=role, is_active=is_active, _id=_id)
        self.location = location
        self.skills = skills or []
        self.education = education
        self.experience = experience
        self.expected_salary = expected_salary
        self.notice_period = notice_period
        self.resume = resume
        self.saved_jobs = saved_jobs or []

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            password_hash=data.get("password_hash", ""),
            role=data.get("role", "CANDIDATE"),
            is_active=data.get("is_active", True),
            _id=data.get("_id"),
            location=data.get("location", ""),
            skills=data.get("skills", []),
            education=data.get("education", ""),
            experience=data.get("experience", 0),
            expected_salary=data.get("expected_salary", 0),
            notice_period=data.get("notice_period", ""),
            resume=data.get("resume"),
            saved_jobs=data.get("saved_jobs", [])
        )

    def profile_completion(self):
        values = [self.name, self.email, self.phone, self.location, self.skills, self.education, self.experience, self.resume]
        completed = sum(1 for value in values if value not in (None, "", [], 0, 0.0))
        return min(100, round((completed / len(values)) * 100))
