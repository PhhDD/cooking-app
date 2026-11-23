from datetime import UTC, datetime
from decimal import Decimal
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import select
from sqlalchemy.orm import Session

from cooking_app.models.ingredient import Ingredient, IngredientCategory
from cooking_app.models.recipe_ingredient import RecipeIngredient
from cooking_app.models.user import User
from cooking_app.web.authorisation import get_recipe_or_404, require_recipe_editor
from cooking_app.web.dependencies import get_current_user, get_db

router = APIRouter()

# API post to add ingredient and ingredient details for a recipe
@router.post("/recipes/{recipe_id}/ingredients")
def add_ingredient(
    recipe_id: UUID,
    ingredient_name: str = Form(...),
    category: IngredientCategory = Form(...),
    quantity: Decimal = Form(...),
    unit: str = Form(...),
    preparation: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    normalised_name = ingredient_name.strip().casefold()

    # Check if the ingredient already exist first
    ingredient_statement = select(Ingredient).where(Ingredient.name == normalised_name)
    ingredient = db.scalar(ingredient_statement)

    # If does not exist, create it, otherwise just reuse the returned
    # ingredient from the above select statement
    if ingredient is None:
        ingredient = Ingredient(
                name = normalised_name,
                category = category,
        )
        db.add(ingredient)
        db.flush() # flush first to get the id from database

    # Now check if the ingredient is already associated with the recipe
    association_statement = select(RecipeIngredient).where(
            RecipeIngredient.recipe_id == recipe_id,
            RecipeIngredient.ingredient_id == ingredient.id,
    )
    existing_association = db.scalar(association_statement)

    if existing_association is not None:
        raise HTTPException(
                status_code = 409,
                detail = "This ingredient is already in the recipe",
        )
    
    # If the ingredient is not associated with the recipe yet, add it
    recipe_ingredient = RecipeIngredient(
            recipe_id = recipe_id,
            quantity = quantity,
            unit = unit.strip(),
            preparation = preparation.strip() or None,
            ingredient_id = ingredient.id,
    )

    db.add(recipe_ingredient)
    recipe.updated_at = datetime.now(UTC)
    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit",
            status_code = 303,
    )


# API route to update the ingredient
@router.post("/recipes/{recipe_id}/ingredients/{recipe_ingredient_id}/edit")
def update_recipe_ingredient(
    recipe_id: UUID,
    recipe_ingredient_id: UUID,
    quantity: Decimal = Form(...),
    unit: str = Form(...),
    preparation: str = Form(""),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    statement = select(RecipeIngredient).where(
            RecipeIngredient.id == recipe_ingredient_id,
            RecipeIngredient.recipe_id == recipe_id,
    )
    recipe_ingredient = db.scalar(statement)

    if recipe_ingredient is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe ingredient not found",
        )

    recipe_ingredient.quantity = quantity
    recipe_ingredient.unit = unit.strip()
    recipe_ingredient.preparation = preparation.strip() or None
    recipe.updated_at = datetime.now(UTC)

    db.commit()

    return RedirectResponse(
            url = (
                f"/recipes/{recipe_id}/edit"
                f"#ingredient-{recipe_ingredient_id}"
            ),
            status_code = 303,
    )


# API route to delete an ingredient
@router.post("/recipes/{recipe_id}/ingredients/{recipe_ingredient_id}/delete")
def delete_recipe_ingredient(
    recipe_id: UUID,
    recipe_ingredient_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    statement = select(RecipeIngredient).where(
            RecipeIngredient.id == recipe_ingredient_id,
            RecipeIngredient.recipe_id == recipe_id,
    )
    recipe_ingredient = db.scalar(statement)

    if recipe_ingredient is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe ingredient not found",
        )

    db.delete(recipe_ingredient)
    recipe.updated_at = datetime.now(UTC)

    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit#ingredients",
            status_code = 303,
    )

