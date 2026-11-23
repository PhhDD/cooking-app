from uuid import uuid4

import pytest

from cooking_app.auth import require_authenticated
from cooking_app.database import SessionLocal
from cooking_app.main import app
from cooking_app.models.user import User
from cooking_app.web.dependencies import get_current_user, get_optional_current_user


@pytest.fixture
def authenticated_user():
    db = SessionLocal()

    user = User(
        logto_subject=f"pytest-{uuid4()}",
        username="pytest-user",
        email="pytest@example.com",
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    app.dependency_overrides[get_current_user] = lambda: user
    app.dependency_overrides[get_optional_current_user] = lambda: user
    app.dependency_overrides[require_authenticated] = lambda: object()

    try:
        yield user
    finally:
        app.dependency_overrides.pop(get_current_user, None)
        app.dependency_overrides.pop(get_optional_current_user, None)
        app.dependency_overrides.pop(require_authenticated, None)
        db.close()
