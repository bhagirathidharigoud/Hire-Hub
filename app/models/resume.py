from datetime import datetime, timezone


class Resume:
    def __init__(self, candidate_id, filename, content_type, size, path, _id=None):
        self._id = _id
        self.candidate_id = candidate_id
        self.filename = filename
        self.content_type = content_type
        self.size = size
        self.path = path
        self.uploaded_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "_id": self._id,
            "candidate_id": self.candidate_id,
            "filename": self.filename,
            "content_type": self.content_type,
            "size": self.size,
            "path": self.path,
            "uploaded_at": self.uploaded_at,
        }
