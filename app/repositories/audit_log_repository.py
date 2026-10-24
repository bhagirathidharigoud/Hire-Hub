from app.repositories.base_repository import BaseRepository


class AuditLogRepository(BaseRepository):
    collection_name = "audit_logs"

    def list_recent(self, limit=20):
        logs = self.find_all(sort=("created_at", True))
        return logs[:limit]
