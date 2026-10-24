from datetime import datetime, timezone


class Interview:
    def __init__(self, application_id, candidate_id, recruiter_id, date="", time="", interview_type="ONLINE", meeting_link="", status="SCHEDULED", feedback="", _id=None):
        self._id = _id
        self.application_id = application_id
        self.candidate_id = candidate_id
        self.recruiter_id = recruiter_id
        self.date = date
        self.time = time
        self.type = interview_type
        self.meeting_link = meeting_link
        self.status = status
        self.feedback = feedback
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "_id": self._id,
            "application_id": self.application_id,
            "candidate_id": self.candidate_id,
            "recruiter_id": self.recruiter_id,
            "date": self.date,
            "time": self.time,
            "type": self.type,
            "meeting_link": self.meeting_link,
            "status": self.status,
            "feedback": self.feedback,
            "created_at": self.created_at,
        }
