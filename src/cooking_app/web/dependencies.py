from collections.abc import Generator

from fastapi import Depends, HTTPException, Request
from sqlalchemy import select
from sqlalchemy.orm import Session

from cooking_app.auth import get_logto_client
from cooking_app.database import SessionLocal
from cooking_app.models.user import User


def get_db() -> Generator[Session]:
    db = SessionLocal()

    try:
        yield db
    finally:
        db.close()


async def get_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User:
    client = get_logto_client(request)

    if not client.isAuthenticated():
        raise HTTPException(
            status_code=307,
            headers={"Location": "/sign-in"},
        )

    claims = client.getIdTokenClaims()

    user = db.scalar(
        select(User).where(
            User.logto_subject == claims.sub
        )
    )

    if user is None:
        user = User(
            logto_subject=claims.sub,
            username=getattr(claims, "username", None),
            email=getattr(claims, "email", None),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    return user


async def get_optional_current_user(
    request: Request,
    db: Session = Depends(get_db),
) -> User | None:
    client = get_logto_client(request)

    if not client.isAuthenticated():
        return None

    claims = client.getIdTokenClaims()

    user = db.scalar(
        select(User).where(
            User.logto_subject == claims.sub
        )
    )

    if user is None:
        user = User(
            logto_subject=claims.sub,
            username=getattr(claims, "username", None),
            email=getattr(claims, "email", None),
        )

        db.add(user)
        db.commit()
        db.refresh(user)

    return user
