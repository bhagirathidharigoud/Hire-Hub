import os
from datetime import timedelta
from dotenv import load_dotenv

load_dotenv()


class Config:
    USE_MONGO = True
    MONGO_REQUIRED = True
    SECRET_KEY = os.getenv("SECRET_KEY")
    MONGO_URI = os.getenv("MONGO_URI") or "mongodb://localhost:27017"
    MONGO_DATABASE = os.getenv("MONGO_DATABASE") or "hirehub"
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER") or "app/uploads/resumes"
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH") or "5242880")
    PERMANENT_SESSION_LIFETIME = timedelta(hours=int(os.getenv("SESSION_LIFETIME_HOURS") or "12"))
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "false").lower() == "true"
    SESSION_REFRESH_EACH_REQUEST = True
    JSON_SORT_KEYS = False


class DevelopmentConfig(Config):
    DEBUG = True


class TestingConfig(Config):
    TESTING = True
    USE_MONGO = False
    MONGO_REQUIRED = False
    MONGO_DATABASE = "hirehub_test"
    SECRET_KEY = "test-only-secret-key"


config = {
    "default": DevelopmentConfig,
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": Config,
}
