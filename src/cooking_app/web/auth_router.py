import os

from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from logto import LogtoException

from cooking_app.auth import get_logto_client

router = APIRouter()

APP_BASE_URL = os.getenv(
    "APP_BASE_URL",
    "http://127.0.0.1:8000",
).rstrip("/")

LOGTO_CALLBACK_URI = f"{APP_BASE_URL}/callback"
LOGTO_POST_LOGOUT_REDIRECT_URI = f"{APP_BASE_URL}/"


@router.get("/sign-in")
async def sign_in(request: Request):
    client = get_logto_client(request)

    sign_in_url = await client.signIn(
        redirectUri=LOGTO_CALLBACK_URI,
    )

    return RedirectResponse(url=sign_in_url)


@router.get("/callback")
async def callback(request: Request):
    client = get_logto_client(request)

    try:
        await client.handleSignInCallback(str(request.url))
    except LogtoException as error:
        return f"Authentication failed: {error}"

    return RedirectResponse(url="/")


@router.get("/sign-out")
async def sign_out(request: Request):
    client = get_logto_client(request)

    sign_out_url = await client.signOut(
        postLogoutRedirectUri=LOGTO_POST_LOGOUT_REDIRECT_URI,
    )

    return RedirectResponse(url=sign_out_url)


@router.get("/auth-status")
async def auth_status(request: Request):
    client = get_logto_client(request)

    if not client.isAuthenticated():
        return {
            "authenticated": False,
            "message": "You are not signed in",
        }

    claims = client.getIdTokenClaims()

    return {
        "authenticated": True,
        "user_id": claims.sub,
        "username": claims.username,
    }
