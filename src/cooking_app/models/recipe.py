from cooking_app.database import Base
from sqlalchemy.orm import Mapped
from sqlalchemy.orm import mapped_column
from sqlalchemy import String
from sqlalchemy import Integer
from sqlalchemy.dialects.postgresql import UUID
from uuid import UUID as UUID_Python
from uuid6 import uuid7
from datetime import datetime
from enum import Enum
from sqlalchemy import Enum as SQLEnum

class SourceLang(str, Enum):
    ENGLISH = "en"
    CHINESE = "zh"

class Recipe(Base):
    __tablename__ = "recipes"

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
