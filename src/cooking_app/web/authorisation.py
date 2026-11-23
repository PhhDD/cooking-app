'''
Contains the utility functions for verification

get_recipe_or_404:
    Verify that the recipe with the id actually exists

require_recipe_editor:
    Verify the recipe belongs to the user or the user
    is admin, before allowing any edit

Usage:
    from cooking_app.web.authorisation import(
        get_recipe_or_404,
        require_recipe_editor,
    )
'''

from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from cooking_app.models.recipe import Recipe
from cooking_app.models.user import User


def get_recipe_or_404(
    recipe_id: UUID,
    db: Session,
) -> Recipe:
    recipe = db.scalar(
        select(Recipe).where(Recipe.id == recipe_id)
    )

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

    return recipe


def require_recipe_editor(
    recipe: Recipe,
    current_user: User,
) -> None:
    if (
        recipe.owner_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to modify this recipe",
        )
