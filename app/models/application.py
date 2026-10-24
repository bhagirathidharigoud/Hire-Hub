from datetime import datetime, timezone


class Application:
    def __init__(self, candidate_id, job_id, status="APPLIED", recruiter_notes="", interview_id=None, _id=None):
        self._id = _id
        self.candidate_id = candidate_id
        self.job_id = job_id
        self.status = status
        self.applied_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()
        self.recruiter_notes = recruiter_notes
        self.interview_id = interview_id

    def to_dict(self):
        return {
            "_id": self._id,
            "candidate_id": self.candidate_id,
            "job_id": self.job_id,
            "status": self.status,
            "applied_at": self.applied_at,
            "updated_at": self.updated_at,
            "recruiter_notes": self.recruiter_notes,
            "interview_id": self.interview_id,
        }
