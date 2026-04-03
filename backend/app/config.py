from __future__ import annotations
from typing import List

"""Application configuration via environment variables."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    # Database
    DATABASE_URL: str = "sqlite+aiosqlite:///./flagsmith.db"

    # JWT
    JWT_SECRET_KEY: str = "change-me-in-production-use-a-real-secret"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24  # 24 hours

    # OAuth
    GOOGLE_CLIENT_ID: str = ""

    # Email
    SMTP_HOST: str = ""
    SMTP_PORT: int = 587
    SMTP_USERNAME: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    SMTP_USE_SSL: bool = False
    SMTP_FROM_EMAIL: str = ""
    FRONTEND_APP_URL: str = "http://localhost:3000"
    INVITE_EMAILS_ENABLED: bool = False
    INVITE_EMAIL_SUBJECT_TEMPLATE: str = (
        "You're invited to join {organization_name} on ConfigHub"
    )
    INVITE_EMAIL_BODY_TEMPLATE: str = (
        "{inviter_name} invited you to join {organization_name} on ConfigHub as a "
        "{role_name}.\n\n"
        "Create your account here:\n"
        "{signup_url}\n\n"
        "If you already have an account with this email, sign in here and the invite "
        "will be accepted automatically:\n"
        "{login_url}\n"
    )

    # App
    APP_NAME: str = "FlagSmith"
    DEBUG: bool = True
    CORS_ORIGINS: List[str] = ["http://localhost:3000"]

    model_config = {"env_file": ".env", "extra": "ignore"}


settings = Settings()
