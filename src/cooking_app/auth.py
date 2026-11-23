import os
from pathlib import Path

from dotenv import load_dotenv
from fastapi import HTTPException, Request
from logto import LogtoClient, LogtoConfig, Storage

PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(PROJECT_ROOT / ".env.local")


LOGTO_ENDPOINT = os.getenv("LOGTO_ENDPOINT")
LOGTO_APP_ID = os.getenv("LOGTO_APP_ID")
LOGTO_APP_SECRET = os.getenv("LOGTO_APP_SECRET")

if not LOGTO_ENDPOINT:
    raise RuntimeError("LOGTO_ENDPOINT is not set")

if not LOGTO_APP_ID:
    raise RuntimeError("LOGTO_APP_ID is not set")

if not LOGTO_APP_SECRET:
    raise RuntimeError("LOGTO_APP_SECRET is not set")


logto_config = LogtoConfig(
    endpoint=LOGTO_ENDPOINT,
    appId=LOGTO_APP_ID,
    appSecret=LOGTO_APP_SECRET,
)


class RequestSessionStorage(Storage):
    def __init__(self, request: Request):
        self.request = request

    def get(self, key: str):
        return self.request.session.get(key)

    def set(self, key: str, value):
        self.request.session[key] = value

    def delete(self, key: str):
        self.request.session.pop(key, None)


def get_logto_client(request: Request) -> LogtoClient:
    return LogtoClient(
        logto_config,
        storage=RequestSessionStorage(request),
    )


def require_authenticated(request: Request) -> LogtoClient:
    client = get_logto_client(request)

    if not client.isAuthenticated():
        raise HTTPException(
            status_code=307,
            headers={"Location": "/sign-in"},
        )

    return client


def get_auth_template_context(request: Request) -> dict[str, bool]:
    client = get_logto_client(request)

    return {
        "is_authenticated": client.isAuthenticated(),
    }
