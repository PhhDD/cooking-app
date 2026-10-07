from uuid import UUID as UUID_Python
from uuid6 import uuid7

from sqlalchemy import CheckConstraint
from sqlalchemy import ForeignKey
from sqlalchemy import ForeignKeyConstraint
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from cooking_app.database import Base


class RecipeStepDependency(Base):
    __tablename__ = "recipe_step_dependencies"

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "predecessor_step_id",
            "successor_step_id",
            name="uq_recipe_step_dependency",
        ),
        CheckConstraint(
            "predecessor_step_id <> successor_step_id",
            name="ck_recipe_step_no_self_dependency",
        ),
        ForeignKeyConstraint(
            ["recipe_id", "predecessor_step_id"],
            ["recipe_steps.recipe_id", "recipe_steps.id"],
            name="fk_dependency_predecessor",
        ),
        ForeignKeyConstraint(
            ["recipe_id", "successor_step_id"],
            ["recipe_steps.recipe_id", "recipe_steps.id"],
            name="fk_dependency_successor",
        ),
    )

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    recipe_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id"),
        nullable=False,
    )

    predecessor_step_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    successor_step_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
