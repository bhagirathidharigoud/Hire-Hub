from datetime import datetime, timezone


class Notification:
    def __init__(self, user_id, message, notification_type="INFO", is_read=False, _id=None):
        self._id = _id
        self.user_id = user_id
        self.message = message
        self.type = notification_type
        self.is_read = is_read
        self.created_at = datetime.now(timezone.utc).isoformat()

    def to_dict(self):
        return {
            "_id": self._id,
            "user_id": self.user_id,
            "message": self.message,
            "type": self.type,
            "is_read": self.is_read,
            "created_at": self.created_at,
        }
