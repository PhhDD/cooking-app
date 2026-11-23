from datetime import UTC, datetime
from uuid import UUID as UUID_Python

from sqlalchemy import Boolean, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from cooking_app.database import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    logto_subject: Mapped[str] = mapped_column(
        String(100),
        unique=True,
        nullable=False,
    )

    username: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )

    email: Mapped[str | None] = mapped_column(
        String(255),
        nullable=True,
    )

    is_admin: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now(UTC),
        nullable=False,
    )
