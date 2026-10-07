from decimal import Decimal
from uuid import UUID as UUID_Python
from uuid6 import uuid7

from sqlalchemy import ForeignKey
from sqlalchemy import Numeric
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from cooking_app.database import Base


class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "ingredient_id",
            name="uq_recipe_ingredient",
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

    ingredient_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    preparation: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
