from app.models.user import User


class Recruiter(User):
    def __init__(self, name, email, phone, password_hash, company_name="", role="RECRUITER", is_active=True, _id=None, company_id=None):
        super().__init__(name, email, phone, password_hash, role=role, is_active=is_active, _id=_id)
        self.company_name = company_name
        self.company_id = company_id

    @classmethod
    def from_dict(cls, data):
        return cls(
            name=data.get("name", ""),
            email=data.get("email", ""),
            phone=data.get("phone", ""),
            password_hash=data.get("password_hash", ""),
            company_name=data.get("company_name", ""),
            role=data.get("role", "RECRUITER"),
            is_active=data.get("is_active", True),
            _id=data.get("_id"),
            company_id=data.get("company_id")
        )
