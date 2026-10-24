from datetime import datetime, timezone

from app.repositories.audit_log_repository import AuditLogRepository


class AuditLogService:
    def __init__(self, audit_log_repository=None):
        self.audit_log_repository = audit_log_repository or AuditLogRepository()

    def log_event(self, event_type, message, actor_id=None, actor_role=None, metadata=None):
        event = {
            "event_type": event_type,
            "message": message,
            "actor_id": actor_id,
            "actor_role": actor_role,
            "metadata": metadata or {},
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        event_id = self.audit_log_repository.insert_one(event)
        event["_id"] = event_id
        return event

    def list_recent(self, limit=20):
        return self.audit_log_repository.list_recent(limit=limit)
