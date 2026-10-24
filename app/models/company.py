from datetime import datetime, timezone


class Company:
    def __init__(self, name, industry="", website="", location="", verified=False, _id=None):
        self._id = _id
        self.name = name
        self.industry = industry
        self.website = website
        self.location = location
        self.verified = verified
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "_id": self._id,
            "name": self.name,
            "industry": self.industry,
            "website": self.website,
            "location": self.location,
            "verified": self.verified,
            "created_at": self.created_at,
        }
