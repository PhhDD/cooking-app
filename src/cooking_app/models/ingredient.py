from enum import Enum
from uuid import UUID as UUID_Python
from uuid6 import uuid7

from sqlalchemy import Enum as SQLEnum
from sqlalchemy import String
from sqlalchemy import UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column

from cooking_app.database import Base


class IngredientCategory(str, Enum):
    VEGETABLE   = "vegetable"
    FRUIT       = "fruit"
    MEAT        = "meat"
    FISH        = "fish"
    SEAFOOD     = "seafood"
    DAIRY       = "dairy"
    GRAIN       = "grain"
    LEGUME      = "legume"
    NUT         = "nut"
    HERB_SPICE  = "herb_spice"
    OIL_FAT     = "oil_fat"
    SAUCE_CONDIMENT = "sauce_condiment"
    OTHER       = "other"


class Ingredient(Base):
    __tablename__ = "ingredients"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_ingredient_name",
        ),
    )

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    name: Mapped[str] = mapped_column(
        String(200),
        nullable=False,
    )

    category: Mapped[IngredientCategory] = mapped_column(
        SQLEnum(
            IngredientCategory,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
