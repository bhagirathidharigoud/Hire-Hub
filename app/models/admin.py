from app.models.user import User


class Admin(User):
    def __init__(self, name, email, phone, password_hash, role="ADMIN", is_active=True, _id=None):
        super().__init__(name, email, phone, password_hash, role=role, is_active=is_active, _id=_id)

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            password_hash=data.get("password_hash", ""),
            role=data.get("role", "ADMIN"),
            is_active=data.get("is_active", True),
            _id=data.get("_id")
        )
