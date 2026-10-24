from __future__ import annotations

from datetime import datetime, timezone


class User:
    def __init__(self, name, email, phone, password_hash, role="CANDIDATE", is_active=True, _id=None):
        self.name = name
        self.email = email
        self.phone = phone
        self.password_hash = password_hash
        self.role = role
        self.is_active = is_active
        self._id = _id
        self.created_at = datetime.now(timezone.utc).isoformat()
        self.updated_at = datetime.now(timezone.utc).isoformat()

    @classmethod
    def from_dict(cls, data):
        user = cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            password_hash=data.get("password_hash", ""),
            role=data.get("role", "CANDIDATE"),
            is_active=data.get("is_active", True),
            _id=data.get("_id"),
        )
        user.created_at = data.get("created_at", user.created_at)
        user.updated_at = data.get("updated_at", user.updated_at)
        return user

    def to_dict(self):
        data = {
            "_id": self._id,
            "name": self.name,
            "email": self.email,
            "phone": self.phone,
            "password_hash": self.password_hash,
            "role": self.role,
            "is_active": self.is_active,
            "created_at": self.created_at,
            "updated_at": self.updated_at,
        }
        return {k: v for k, v in data.items() if v is not None}

    @property
    def is_admin(self):
        return self.role == "ADMIN"

    @staticmethod
    def hash_password(password):
        from werkzeug.security import generate_password_hash
        return generate_password_hash(password)

    @staticmethod
    def verify_password(password_hash, password):
        from werkzeug.security import check_password_hash
        return check_password_hash(password_hash, password)
