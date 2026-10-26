from datetime import datetime, timezone

from werkzeug.security import check_password_hash, generate_password_hash

from app.exceptions import InvalidCredentialsError, UserAlreadyExistsError, UserDeactivatedError, UserNotFoundError
from app.repositories.user_repository import UserRepository
from app.utils.validators import is_valid_email, is_valid_password, is_valid_phone


class AuthService:
    def __init__(self, user_repository=None):
        self.user_repository = user_repository or UserRepository()

    def register_user(self, payload):
        email = (payload.get("email") or "").strip().lower()
        password = payload.get("password")
        role = (payload.get("role") or "CANDIDATE").upper()
        if not is_valid_email(email):
            raise ValueError("Invalid email")
        if not is_valid_password(password):
            raise ValueError("Password must be at least 8 characters")
        if role not in {"CANDIDATE", "RECRUITER"}:
            raise ValueError("Only candidate and recruiter accounts can be registered")
        if not (payload.get("name") or "").strip():
            raise ValueError("Name is required")
        phone = (payload.get("phone") or "").strip()
        if phone and not is_valid_phone(phone):
            raise ValueError("Invalid phone number")
        if self.user_repository.find_by_email(email):
            raise UserAlreadyExistsError("User already exists")

        user = {
            "name": (payload.get("name") or "").strip(),
            "email": email,
            "phone": phone,
            "password_hash": generate_password_hash(password),
            "role": role,
            "is_active": True,
            "created_at": datetime.now(timezone.utc).isoformat(),
            "updated_at": datetime.now(timezone.utc).isoformat(),
        }
        user_id = self.user_repository.insert_one(user)
        user["_id"] = user_id
        return user

    def login_user(self, email, password):
        user = self.user_repository.find_by_email((email or "").strip().lower())
        if not user:
            raise UserNotFoundError("User not found")
        if not user.get("is_active", True):
            raise UserDeactivatedError("User is deactivated")
        if not user.get("password_hash") or not password or not check_password_hash(user["password_hash"], password):
            raise InvalidCredentialsError("Invalid credentials")
        return user
