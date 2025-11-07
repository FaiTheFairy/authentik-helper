from __future__ import annotations

from typing import Literal
from pydantic import AnyHttpUrl, PositiveInt, SecretStr
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """centralized, typed app configuration loaded from env"""

    # authentik / app
    AK_BASE_URL: AnyHttpUrl
    EXTERNAL_BASE_URL: AnyHttpUrl | None = None
    AK_TOKEN: SecretStr
    AK_GUESTS_GROUP_UUID: str
    AK_MEMBERS_GROUP_UUID: str
    AK_BRAND_UUID: str | None = None
    AK_INVITE_FLOW_SLUG: str | None = None  # allow unset
    AK_INVITE_EXPIRES_DAYS: int = 7

    # smtp
    SMTP_HOST: str | None = None
    SMTP_PORT: PositiveInt = 465
    SMTP_USERNAME: str | None = None
    SMTP_PASSWORD: SecretStr | None = None
    SMTP_FROM: str | None = None

    # email templates
    PORTAL_URL: AnyHttpUrl | None = None
    ORGANIZATION_NAME: str | None = None
    BRAND_LOGO: str | None = None
    EMAIL_SUBJECT_INVITATION: str | None = None
    EMAIL_SUBJECT_PROMOTION: str | None = None
    EMAIL_FOOTER: str = "Sent using Authentik Helper. Built with love."

    # oidc
    SESSION_SECRET: SecretStr
    OIDC_ISSUER: AnyHttpUrl | None = None  # normalized via property below
    OIDC_CLIENT_ID: str | None = None
    OIDC_CLIENT_SECRET: SecretStr | None = None
    OIDC_SCOPES: str = "openid profile email"

    # runtime flags
    LOG_LEVEL: Literal["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"] = "INFO"
    DISABLE_AUTH: bool = False

    # computed helpers
    @property
    def external_origin(self) -> str:
        """scheme://host[:port] of EXTERNAL_BASE_URL"""
        from urllib.parse import urlsplit

        if not self.EXTERNAL_BASE_URL:
            return ""
        p = urlsplit(str(self.EXTERNAL_BASE_URL))
        return f"{p.scheme}://{p.netloc}"

    @property
    def oidc_issuer_stripped(self) -> str:
        """issuer without trailing slash for consistent concatenation"""
        return str(self.OIDC_ISSUER).rstrip("/")

    @property
    def portal_url_effective(self) -> str:
        """portal url or fallback to ak base url"""
        return str(self.PORTAL_URL or self.AK_BASE_URL)

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",  # ignore unexpected env vars
    )


settings = Settings()  # type: ignore
