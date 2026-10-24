from app.repositories.base_repository import BaseRepository


class NotificationRepository(BaseRepository):
    collection_name = "notifications"

    def list_for_user(self, user_id):
        return self.find_all({"user_id": user_id})
