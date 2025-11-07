# core/security.py
from __future__ import annotations

from typing import Any, Dict, Protocol, cast

from authlib.integrations.starlette_client import OAuth
from fastapi import HTTPException, Request

from tools.settings import settings  # global singleton


class OIDCClientProto(Protocol):
    async def authorize_redirect(self, request: Request, redirect_uri: str): ...
    async def authorize_access_token(self, request: Request) -> Dict[str, Any]: ...
    async def userinfo(self, token: Dict[str, Any]) -> Dict[str, Any]: ...
    async def parse_id_token(self, request: Request, token: Dict[str, Any]) -> Dict[str, Any]: ...
    @property
    def server_metadata(self) -> Dict[str, Any]: ...


def _create_oauth() -> OAuth:
    """register the oidc client unless auth is disabled"""
    oauth = OAuth()
    if not settings.DISABLE_AUTH:
        client_secret = (
            settings.OIDC_CLIENT_SECRET.get_secret_value()
            if hasattr(settings.OIDC_CLIENT_SECRET, "get_secret_value")
            else settings.OIDC_CLIENT_SECRET
        )
        oauth.register(
            name="oidc",
            server_metadata_url=f"{settings.oidc_issuer_stripped}/.well-known/openid-configuration",
            client_id=settings.OIDC_CLIENT_ID,
            client_secret=client_secret,
            client_kwargs={"scope": settings.OIDC_SCOPES, "timeout": 10.0},
        )
    return oauth


# singleton for modules to use
oauth: OAuth = _create_oauth()


def get_oidc() -> OIDCClientProto:
    """return the registered OIDC client or 503 if disabled/not registered"""
    if settings.DISABLE_AUTH:
        raise HTTPException(status_code=503, detail="oidc is disabled")
    try:
        return cast(OIDCClientProto, getattr(oauth, "oidc"))
    except AttributeError:
        raise HTTPException(status_code=503, detail="oidc provider not registered")
