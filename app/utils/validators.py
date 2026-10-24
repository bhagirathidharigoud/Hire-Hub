import re
from werkzeug.utils import secure_filename

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PHONE_RE = re.compile(r"^\+?[0-9\s-]{7,20}$")


def is_valid_email(value):
    return bool(value and EMAIL_RE.match((value or "").strip()))


def is_valid_phone(value):
    return bool(value and PHONE_RE.match(str(value).strip()))


def is_valid_password(value):
    return bool(value and len(value) >= 8)


def normalize_skills(skills):
    if not skills:
        return []
    if isinstance(skills, str):
        items = [item.strip() for item in skills.split(",")]
    else:
        items = [str(item).strip() for item in skills]
    return [item for item in items if item]


def secure_upload_name(filename):
    name = secure_filename(filename or "resume")
    return name or "resume.pdf"


def is_allowed_resume(filename, content_type=None):
    allowed_exts = {"pdf", "doc", "docx"}
    allowed_mimes = {
        "application/pdf",
        "application/msword",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
    }
    name = (filename or "").lower()
    ext = name.rsplit(".", 1)[-1] if "." in name else ""
    if ext not in allowed_exts:
        return False
    if content_type and content_type not in allowed_mimes:
        return False
    return True
