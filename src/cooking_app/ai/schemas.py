from decimal import Decimal

from pydantic import BaseModel, Field, HttpUrl

from cooking_app.models.ingredient import IngredientCategory
from cooking_app.models.recipe_step import StepType


class ExtractedIngredient(BaseModel):
    name: str = Field(min_length=1, max_length=200)
    category: IngredientCategory = IngredientCategory.OTHER
    quantity: Decimal | None = Field(default=None, ge=0)
    unit: str = Field(default="", max_length=30)
    preparation: str | None = Field(default=None, max_length=100)


class ExtractedStep(BaseModel):
    step_number: int = Field(ge=1)
    step_type: StepType = StepType.COOKING
    instruction: str = Field(min_length=1)
    duration: int = Field(default=0, ge=0)


class ExtractedRecipe(BaseModel):
    recipe_name: str = Field(min_length=1, max_length=200)
    cuisine: str | None = Field(default=None, max_length=30)
    cook_time_minutes: int = Field(ge=0, le=1440)
    servings: int = Field(ge=1, le=50)
    source_url: HttpUrl
    ingredients: list[ExtractedIngredient] = Field(min_length=1)
    steps: list[ExtractedStep] = Field(min_length=1)
