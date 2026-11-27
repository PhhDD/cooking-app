from datetime import datetime
from enum import Enum
from uuid import UUID as UUID_Python

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from cooking_app.database import Base


class RecipeImportStatus(str, Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class RecipeImport(Base):
    __tablename__ = "recipe_imports"

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    owner_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("users.id"),
        nullable=False,
    )

    source_url: Mapped[str] = mapped_column(
        String(500),
        nullable=False,
    )

    status: Mapped[RecipeImportStatus] = mapped_column(
        SQLEnum(
            RecipeImportStatus,
            values_callable=lambda enum: [
                member.value for member in enum
            ],
        ),
        nullable=False,
        default=RecipeImportStatus.PENDING,
    )

    error_message: Mapped[str | None] = mapped_column(
        Text,
        nullable=True,
    )

    recipe_id: Mapped[UUID_Python | None] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id", ondelete="SET NULL"),
        nullable=True,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now,
    )
