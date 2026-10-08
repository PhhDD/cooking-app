from pathlib import Path
from uuid import UUID
from decimal import Decimal
from datetime import datetime, timezone

from fastapi import APIRouter, Depends, Request, Form
from fastapi.responses import RedirectResponse
from fastapi.templating import Jinja2Templates
from fastapi import HTTPException
from sqlalchemy import select, func, delete
from sqlalchemy.orm import Session

from cooking_app.models.recipe import Recipe
from cooking_app.models.recipe_ingredient import RecipeIngredient
from cooking_app.models.ingredient import Ingredient, IngredientCategory
from cooking_app.models.recipe_step import RecipeStep, StepType
from cooking_app.models.recipe_step_dependency import RecipeStepDependency
from cooking_app.web.dependencies import get_db

router = APIRouter()

TEMPLATES_DIRECTORY = Path(__file__).resolve().parents[1] / "templates"
templates = Jinja2Templates(directory=TEMPLATES_DIRECTORY)


# API request that returns all recipes
@router.get("/recipes")
def recipe_list(
    request: Request,
    db: Session = Depends(get_db),
):
    statement = select(Recipe).order_by(Recipe.created_at.desc())
    recipes = db.scalars(statement).all()

    return templates.TemplateResponse(
            request = request,
            name = "recipes/list.html",
            context = {"recipes": recipes},
    )


# Add new recipe form, have to be before get below, otherwise new might
# be misinterpreted
@router.get("/recipes/new")
def new_recipe_form(
    request: Request
):
    return templates.TemplateResponse(
            request = request,
            name = "recipes/new.html",
            context = {},
    )


# Add new recipe using the form above
@router.post("/recipes")
def create_recipe(
    recipe_name: str = Form(...),
    cuisine: str = Form(""),
    cook_time: int = Form(...),
    servings: int = Form(...),
    db: Session = Depends(get_db),
):
    # Get the input from the html form send back from API
    recipe = Recipe(
            recipe_name = recipe_name,
            cuisine = cuisine or None,
            cook_time = cook_time,
            servings = servings,
    )

    db.add(recipe)
    db.commit()
    db.refresh(recipe)
    
    # This prevents the user resubmit the form, so upon submission,
    # it'll redirect to the detail page of the newly created recipe
    return RedirectResponse(
            url = f"/recipes/{recipe.id}",
            status_code = 303
    )


# API request that returns the recipe with the matching id,
# the request also returns the ingredients of the recipe
@router.get("/recipes/{recipe_id}")
def recipe_detail(
    recipe_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    recipe_statement = select(Recipe).where(Recipe.id == recipe_id) # get recipe sql
    recipe = db.scalar(recipe_statement)

    ingredient_statement = ( # get ingredient sql
            select(RecipeIngredient, Ingredient)
            .join(
                Ingredient,
                RecipeIngredient.ingredient_id == Ingredient.id,
            )
            .where(RecipeIngredient.recipe_id == recipe_id)
    )
    ingredient_rows = db.execute(ingredient_statement).all()

    step_statement = select(RecipeStep).where(RecipeStep.recipe_id == recipe_id).order_by(RecipeStep.step_number) # get recipe step sql
    steps = db.scalars(step_statement).all()

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    return templates.TemplateResponse(
            request = request,
            name = "recipes/detail.html",
            context = {
                "recipe": recipe,
                "ingredient_rows": ingredient_rows,
                "categories": IngredientCategory,
                "steps": steps,
                "step_types": StepType,
            },
    )


# API for generating the editing form for recipe
@router.get("/recipes/{recipe_id}/edit")
def edit_recipe_form(
    recipe_id: UUID,
    request: Request,
    db: Session = Depends(get_db),
):
    statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    return templates.TemplateResponse(
            request = request,
            name = "recipes/edit.html",
            context = {"recipe": recipe},
    )


# API to modify the recipe
@router.post("/recipes/{recipe_id}/edit")
def update_recipe(
    recipe_id: UUID,
    recipe_name: str = Form(...),
    cuisine: str = Form(""),
    cook_time: int = Form(...),
    servings: int = Form(...),
    db: Session = Depends(get_db),
):

    statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    recipe.recipe_name = recipe_name.strip()
    recipe.cuisine = cuisine.strip() or None
    recipe.cook_time = cook_time
    recipe.servings = servings
    recipe.updated_at = datetime.now(timezone.utc)

    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}",
            status_code = 303,
    )


# API to delete a recipe
@router.post("/recipes/{recipe_id}/delete")
def delete_recipe(
    recipe_id: UUID,
    db: Session = Depends(get_db),
):
    statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    db.execute(
        delete(RecipeStepDependency).where(RecipeStepDependency.recipe_id == recipe_id)
    )
    
    db.execute(
        delete(RecipeIngredient).where(RecipeIngredient.recipe_id == recipe_id)
    )

    db.execute(
        delete(RecipeStep).where(RecipeStep.recipe_id == recipe_id)
    )

    db.delete(recipe)
    db.commit()

    return RedirectResponse(
            url = "/recipes",
            status_code = 303,
    )


# API post to add ingredient and ingredient details for a recipe
@router.post("/recipes/{recipe_id}/ingredients")
def add_ingredient(
    recipe_id: UUID,
    ingredient_name: str = Form(...),
    category: IngredientCategory = Form(...),
    quantity: Decimal = Form(...),
    unit: str = Form(...),
    preparation: str = Form(""),
    db: Session = Depends(get_db),
):
    recipe_statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(recipe_statement)

    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )

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
    recipe.update_at = datetime.now(timezone.utc)
    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}",
            status_code = 303,
    )


# API for adding steps, which follows the same pattern as adding ingredient
@router.post("/recipes/{recipe_id}/steps")
def add_step(
    recipe_id: UUID,
    instruction: str = Form(...),
    duration: int = Form(...),
    step_type: StepType = Form(...),
    db: Session = Depends(get_db),
):
    recipe_statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(recipe_statement)
    
    if recipe is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe not found",
        )
    
    # To automatically increment the step number
    # Get the maximum current step number for this recipe first
    # Then the next one would be the current max + 1
    last_step_number = db.scalar(
            select(func.max(RecipeStep.step_number)).where(RecipeStep.recipe_id == recipe_id)
    )
    next_step_number = (last_step_number or 0) + 1

    step = RecipeStep(
           recipe_id = recipe_id,
           step_number = next_step_number,
           step_type = step_type,
           instruction = instruction.strip(),
           duration = duration
    )

    db.add(step)
    recipe.updated_at = datetime.now(timezone.utc)
    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}",
            status_code = 303,
    )


