from datetime import datetime
from enum import Enum
from uuid import UUID as UUID_Python
from uuid6 import uuid7

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import UniqueConstraint
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from cooking_app.database import Base


class StepType(str, Enum):
    PREPARATION = "preparation"
    COOKING = "cooking"


class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "step_number",
            name="uq_recipe_step_number",
        ),
        UniqueConstraint(
            "recipe_id",
            "id",
            name="uq_recipe_step_recipe_id_id",
        ),
    )

    id:             Mapped[UUID_Python] = mapped_column(
                        UUID(as_uuid=True),
                        primary_key=True,
                        default=uuid7,
                    )
    recipe_id:      Mapped[UUID_Python] = mapped_column(
                        UUID(as_uuid=True),
                        ForeignKey("recipes.id"),
                        nullable=False,
                    )
    step_number:    Mapped[int] = mapped_column(
                        Integer,
                        nullable=False,
                    )
    step_type:      Mapped[StepType] = mapped_column(
                        SQLEnum(
                            StepType,
                            values_callable=lambda enum: [member.value for member in enum],
                        ),
                        nullable=False,
                    )
    instruction:    Mapped[str] = mapped_column(
                        Text,
                        nullable=False,
                    )
    duration:       Mapped[int] = mapped_column(
                        Integer,
                        nullable=False,
                    )
    created_at:     Mapped[datetime] = mapped_column(
                        default=datetime.now,
                    )
    updated_at:     Mapped[datetime] = mapped_column(
                        default=datetime.now,
                        onupdate=datetime.now,
                    )


