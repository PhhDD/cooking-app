import logging
from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from cooking_app.ai.gemini_provider import GeminiRecipeProvider
from cooking_app.ai.schemas import ExtractedRecipe
from cooking_app.ai.youtube_metadata import fetch_video_metadata
from cooking_app.database import SessionLocal
from cooking_app.models.ingredient import Ingredient
from cooking_app.models.recipe import Recipe
from cooking_app.models.recipe_import import (
    RecipeImport,
    RecipeImportStatus,
)
from cooking_app.models.recipe_ingredient import RecipeIngredient
from cooking_app.models.recipe_step import RecipeStep

logger = logging.getLogger(__name__)

def import_youtube_recipe(
    video_url: str,
    owner_id: UUID,
    db: Session,
    provider: GeminiRecipeProvider | None = None,
) -> Recipe:
    metadata = fetch_video_metadata(video_url)

    recipe_provider = provider or GeminiRecipeProvider()
    extracted: ExtractedRecipe = recipe_provider.extract_recipe(metadata)

    recipe = Recipe(
        recipe_name=extracted.recipe_name,
        cook_time=extracted.cook_time_minutes,
        servings=extracted.servings,
        cuisine=extracted.cuisine or "",
        owner_id=owner_id,
        source_url=str(extracted.source_url),
        is_ai_imported=True,
        is_public=False,
    )

    try:
        db.add(recipe)
        db.flush()

        ingredient_cache: dict[str, Ingredient] = {}

        for extracted_ingredient in extracted.ingredients:
            ingredient_name = extracted_ingredient.name.strip()
            ingredient_key = ingredient_name.casefold()

            ingredient = ingredient_cache.get(ingredient_key)

            if ingredient is None:
                ingredient = db.scalar(
                    select(Ingredient).where(
                        Ingredient.name == ingredient_name,
                    )
                )

            if ingredient is None:
                ingredient = Ingredient(
                    name=ingredient_name,
                    category=extracted_ingredient.category,
                )
                db.add(ingredient)
                db.flush()

            ingredient_cache[ingredient_key] = ingredient

            db.add(
                RecipeIngredient(
                    recipe_id=recipe.id,
                    ingredient_id=ingredient.id,
                    quantity=(
                        extracted_ingredient.quantity
                        if extracted_ingredient.quantity is not None
                        else Decimal(0)
                    ),
                    unit=extracted_ingredient.unit,
                    preparation=extracted_ingredient.preparation,
                )
            )

        for extracted_step in extracted.steps:
            db.add(
                RecipeStep(
                    recipe_id=recipe.id,
                    step_number=extracted_step.step_number,
                    step_type=extracted_step.step_type,
                    instruction=extracted_step.instruction,
                    duration=extracted_step.duration,
                )
            )

        db.commit()
        db.refresh(recipe)

    except Exception:
        db.rollback()
        raise

    return recipe


def process_youtube_import(import_id: UUID) -> None:
    db = SessionLocal()

    try:
        import_job = db.get(RecipeImport, import_id)

        if import_job is None:
            logger.error(
                "Recipe import job not found: %s",
                import_id,
            )
            return

        import_job.status = RecipeImportStatus.PROCESSING
        db.commit()

        recipe = import_youtube_recipe(
            video_url=import_job.source_url,
            owner_id=import_job.owner_id,
            db=db,
        )

        import_job.status = RecipeImportStatus.COMPLETED
        import_job.recipe_id = recipe.id
        import_job.error_message = None
        db.commit()

    except Exception:
        logger.exception(
            "YouTube recipe import failed: %s",
            import_id,
        )
        db.rollback()

        import_job = db.get(RecipeImport, import_id)

        if import_job is not None:
            import_job.status = RecipeImportStatus.FAILED
            import_job.error_message = (
                "We could not import this recipe. "
                "Please try again."
            )
            db.commit()

    finally:
        db.close()
