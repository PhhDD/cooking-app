from datetime import datetime
from enum import Enum
from uuid import UUID as UUID_Python

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from uuid6 import uuid7

from cooking_app.database import Base


class SourceLang(str, Enum):
    ENGLISH = "en"
    CHINESE = "zh"

class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = (
        UniqueConstraint(
            "owner_id",
            "source_recipe_id",
            name = "uq_recipe_owner_source",
        ),
    )

    id:             Mapped[UUID_Python] = mapped_column(
                                                    UUID(as_uuid=True),
                                                    primary_key=True,
                                                    default=uuid7,
                                                    )
    recipe_name:    Mapped[str]         = mapped_column(String(200))
    source_lang:    Mapped[SourceLang]  = mapped_column(
                                                    SQLEnum(
                                                        SourceLang,
                                                        values_callable=lambda enum: [member.value for member in enum],
                                                    ),
                                                    default=SourceLang.ENGLISH,
                                                    )
    cook_time:      Mapped[int]         = mapped_column(Integer) # Unit is in second
    servings:       Mapped[int]         = mapped_column(Integer)
    cuisine:        Mapped[str]         = mapped_column(String(30))
    created_at:     Mapped[datetime]    = mapped_column(default=datetime.now)
    updated_at:     Mapped[datetime]    = mapped_column(
                                                    default=datetime.now,
                                                    onupdate=datetime.now,
                                                    )
    owner_id:       Mapped[UUID_Python | None] = mapped_column(
                                                    UUID(as_uuid=True),
                                                    ForeignKey("users.id"),
                                                    nullable=True,
                                                    )
    source_recipe_id: Mapped[UUID_Python | None] = mapped_column(
                                                    UUID(as_uuid=True),
                                                    ForeignKey("recipes.id", ondelete="SET NULL"),
                                                    nullable=True,
                                                    )
    is_public:      Mapped[bool]        = mapped_column(
                                                    default=False,
                                                    nullable=False,
                                                    )
