from datetime import datetime, timezone

from app.repositories.notification_repository import NotificationRepository


class NotificationService:
    def __init__(self, notification_repository=None):
        self.notification_repository = notification_repository or NotificationRepository()

    def create(self, user_id, message, message_type="INFO"):
        notification = {
            "user_id": user_id,
            "message": message,
            "type": message_type,
            "is_read": False,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        notification_id = self.notification_repository.insert_one(notification)
        notification["_id"] = notification_id
        return notification

    def list_for_user(self, user_id):
        return self.notification_repository.list_for_user(user_id)

    def mark_read(self, user_id, notification_id=None):
        filters = {"user_id": user_id}
        if notification_id:
            filters["_id"] = notification_id
            if not self.notification_repository.find_one(filters):
                return False
            return bool(
                self.notification_repository.update_one(
                    filters,
                    {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()},
                )
            )
        notifications = self.notification_repository.find_all(filters)
        for notification in notifications:
            if not notification.get("is_read"):
                self.notification_repository.update_one(
                    {"_id": notification["_id"], "user_id": user_id},
                    {"is_read": True, "read_at": datetime.now(timezone.utc).isoformat()},
                )
        return True
