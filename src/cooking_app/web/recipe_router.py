from datetime import UTC, datetime
from uuid import UUID

from fastapi import (
    APIRouter,
    BackgroundTasks,
    Depends,
    Form,
    HTTPException,
    Request,
)
from fastapi.responses import RedirectResponse
from logto import LogtoClient
from sqlalchemy import String, delete, func, or_, select
from sqlalchemy.orm import Session

from cooking_app.ai.youtube import extract_video_id
from cooking_app.ai.youtube_import import process_youtube_import
from cooking_app.auth import require_authenticated
from cooking_app.models.ingredient import Ingredient, IngredientCategory
from cooking_app.models.recipe import Recipe
from cooking_app.models.recipe_import import RecipeImport, RecipeImportStatus
from cooking_app.models.recipe_ingredient import RecipeIngredient
from cooking_app.models.recipe_step import RecipeStep, StepType
from cooking_app.models.recipe_step_dependency import RecipeStepDependency
from cooking_app.models.user import User
from cooking_app.web.authorisation import get_recipe_or_404
from cooking_app.web.dependencies import (
    get_current_user,
    get_db,
    get_optional_current_user,
)
from cooking_app.web.templates import templates  # Jinja2 Templates class pre-defined

router = APIRouter()

# API request that returns all recipes
@router.get("/recipes")
def recipe_list(
    request: Request, # Browser request
    q: str = "", # Used for search query
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    if current_user is None:
        statement = select(Recipe).where(Recipe.is_public.is_(True))
    else:
        statement = select(Recipe).where(
            or_(
                Recipe.is_public.is_(True),
                Recipe.owner_id == current_user.id,
                current_user.is_admin,
            )
        )

    search_term = q.strip()
    if search_term:
        search_pattern = f"%{search_term}%"
        # Convert category with _ to a space for search
        category_text = func.replace(
                Ingredient.category.cast(String),
                "_",
                " ",
        )

        ingredient_match = (
                select(RecipeIngredient.id)
                .join(
                    Ingredient,
                    RecipeIngredient.ingredient_id == Ingredient.id,
                )
                .where(
                    RecipeIngredient.recipe_id == Recipe.id,
                    or_(
                        Ingredient.name.ilike(search_pattern),
                        category_text.ilike(search_pattern),
                    ),
                )
                .exists()
        )

        statement = statement.where(
                or_(
                    Recipe.recipe_name.ilike(search_pattern),
                    Recipe.cuisine.ilike(search_pattern),
                    ingredient_match,
                )
        )

    statement = statement.order_by(Recipe.created_at.desc())
    recipes = db.scalars(statement).all()

    return templates.TemplateResponse(
            request = request,
            name = "recipes/list.html",
            context = {
                "recipes": recipes,
                "query": search_term,
                "active_tab": "public",
                "is_admin": (
                    current_user is not None
                    and current_user.is_admin
                ),
            },
    )


# API route to go to vault page for signed-in user
# where only their recipes are displayed
@router.get("/vault")
def vault(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = (
        select(Recipe)
        .where(Recipe.owner_id == current_user.id)
        .order_by(Recipe.updated_at.desc())
    )

    recipes = db.scalars(statement).all()

    import_jobs = db.scalars(
        select(RecipeImport)
        .where(RecipeImport.owner_id == current_user.id)
        .order_by(RecipeImport.created_at.desc())
        .limit(10)
    ).all()

    return templates.TemplateResponse(
        request = request,
        name = "recipes/list.html",
        context = {
            "recipes": recipes,
            "import_jobs": import_jobs,
            "query": "",
            "page_title": "Recipes",
            "page_description": "Your private recipes and saved public recipes.",
            "active_tab": "vault",
            "is_admin": current_user.is_admin,
        },
    )


# Add new recipe form, have to be before get below, otherwise new might
# be misinterpreted
@router.get("/recipes/new")
def new_recipe_form(
    request: Request,
    client: LogtoClient = Depends(require_authenticated),
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
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    # Get the input from the html form send back from API
    recipe = Recipe(
            recipe_name = recipe_name,
            cuisine = cuisine or None,
            cook_time = cook_time,
            servings = servings,
            owner_id = current_user.id,
            is_public = current_user.is_admin,
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


# API route for youtube import
@router.get("/recipes/import/youtube")
def youtube_import_form(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    return templates.TemplateResponse(
            request = request,
            name = "recipes/import_youtube.html",
            context = {"error": None},
    )


# API route for posting imported Youtube recipe
@router.post("/recipes/import/youtube")
def import_youtube(
    request: Request,
    background_tasks: BackgroundTasks,
    video_url: str = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    try:
        video_id = extract_video_id(video_url)
    except ValueError as error:
        return templates.TemplateResponse(
            request=request,
            name="recipes/import_youtube.html",
            context={"error": str(error)},
            status_code=400,
        )

    canonical_url = (
        f"https://www.youtube.com/watch?v={video_id}"
    )

    existing_recipe = db.scalar(
        select(Recipe).where(
            Recipe.owner_id == current_user.id,
            Recipe.source_url == canonical_url,
        )
    )

    if existing_recipe is not None:
        return RedirectResponse(
            url=f"/recipes/{existing_recipe.id}",
            status_code=303,
        )

    existing_import = db.scalar(
        select(RecipeImport)
        .where(
            RecipeImport.owner_id == current_user.id,
            RecipeImport.source_url == canonical_url,
            RecipeImport.status.in_(
                [
                    RecipeImportStatus.PENDING,
                    RecipeImportStatus.PROCESSING,
                ]
            ),
        )
        .order_by(RecipeImport.created_at.desc())
    )

    if existing_import is not None:
        return RedirectResponse(
            url=f"/recipes/import/youtube/{existing_import.id}",
            status_code=303,
        )

    import_job = RecipeImport(
        owner_id=current_user.id,
        source_url=canonical_url,
        status=RecipeImportStatus.PENDING,
    )

    db.add(import_job)
    db.commit()
    db.refresh(import_job)

    background_tasks.add_task(
        process_youtube_import,
        import_job.id,
    )

    return RedirectResponse(
        url=f"/recipes/import/youtube/{import_job.id}",
        status_code=303,
    )


# Delete failed import
@router.post("/recipes/import/youtube/{import_id}/delete")
def delete_failed_youtube_import(
    import_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import_job = db.scalar(
        select(RecipeImport).where(
            RecipeImport.id == import_id,
            RecipeImport.owner_id == current_user.id,
        )
    )

    if (
        import_job is None
        or import_job.status != RecipeImportStatus.FAILED
    ):
        raise HTTPException(
            status_code=404,
            detail="Failed recipe import not found",
        )

    db.delete(import_job)
    db.commit()

    return RedirectResponse(
        url="/vault",
        status_code=303,
    )


# Check the import status
@router.get("/recipes/import/youtube/{import_id}")
def youtube_import_status(
    import_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    import_job = db.scalar(
        select(RecipeImport).where(
            RecipeImport.id == import_id,
            RecipeImport.owner_id == current_user.id,
        )
    )

    if import_job is None:
        raise HTTPException(
            status_code=404,
            detail="Recipe import not found",
        )

    return templates.TemplateResponse(
        request=request,
        name="recipes/import_status.html",
        context={"job": import_job},
    )


# API route to copy a public recipe to vault
@router.post("/recipes/{recipe_id}/copy")
def copy_recipe(
    recipe_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    source_recipe = get_recipe_or_404(recipe_id, db)
    
    if not source_recipe.is_public:
        raise HTTPException(
                status_code = 404,
                detail = "Only public recipes can be copied",
        )

    existing_copy = db.scalar(
        select(Recipe).where(
            Recipe.owner_id == current_user.id,
            Recipe.source_recipe_id == source_recipe.id,
        )
    )

    if existing_copy is not None:
        return RedirectResponse(
                url = f"/recipes/{existing_copy.id}",
                status_code = 303,
        )
    
    # Generate the copied recipe, and add to the database
    copied_recipe = Recipe(
        recipe_name = source_recipe.recipe_name,
        source_lang = source_recipe.source_lang,
        cook_time = source_recipe.cook_time,
        servings = source_recipe.servings,
        cuisine = source_recipe.cuisine,
        owner_id = current_user.id,
        is_public = False,
        source_recipe_id = source_recipe.id,
    )

    db.add(copied_recipe)
    db.flush()

    # Generate the copied ingredients, and add to the database
    ingredient_rows = db.scalars(
        select(RecipeIngredient).where(
            RecipeIngredient.recipe_id == source_recipe.id
        )
    ).all()
    for ingredient_row in ingredient_rows:
        db.add(
            RecipeIngredient(
                recipe_id = copied_recipe.id,
                ingredient_id = ingredient_row.ingredient_id,
                quantity = ingredient_row.quantity,
                unit = ingredient_row.unit,
                preparation = ingredient_row.preparation,
            )
        )

    # Generate the copied steps, and add to the database
    source_steps = db.scalars(
        select(RecipeStep)
        .where(RecipeStep.recipe_id == source_recipe.id)
        .order_by(RecipeStep.step_number)
    ).all()
    copied_steps = {} # For adding dependencies later
    for source_step in source_steps:
        copied_step = RecipeStep(
                recipe_id = copied_recipe.id,
                step_number = source_step.step_number,
                step_type = source_step.step_type,
                instruction = source_step.instruction,
                duration = source_step.duration,
        )

        db.add(copied_step)
        db.flush()

        copied_steps[source_step.id] = copied_step
    
    # Generate the copied dependencies, and add to the database
    source_dependencies = db.scalars(
        select(RecipeStepDependency).where(
            RecipeStepDependency.recipe_id == source_recipe.id
        )
    ).all()

    for dependency in source_dependencies:
        db.add(
            RecipeStepDependency(
                recipe_id = copied_recipe.id,
                predecessor_step_id = copied_steps[
                    dependency.predecessor_step_id
                ].id,
                successor_step_id = copied_steps[
                    dependency.successor_step_id
                ].id,
            )
        )

    db.commit()
    db.refresh(copied_recipe)

    return RedirectResponse(
            url = f"/recipes/{copied_recipe.id}",
            status_code = 303,
    )

# API request that returns the recipe with the matching id,
# the request also returns the ingredients of the recipe
@router.get("/recipes/{recipe_id}")
def recipe_detail(
    recipe_id: UUID,
    request: Request,
    current_user: User | None = Depends(get_optional_current_user),
    db: Session = Depends(get_db),
):
    recipe_statement = select(Recipe).where(Recipe.id == recipe_id) # get recipe sql
    recipe = db.scalar(recipe_statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    can_view = (
        recipe.is_public
        or (
            current_user is not None
            and (
                recipe.owner_id == current_user.id
                or current_user.is_admin
            )
        )
    )

    if not can_view:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    can_edit = (
        current_user is not None
        and (
            current_user.is_admin
            or recipe.owner_id == current_user.id
        )
    )

    is_owned_private_recipe = (
        current_user is not None
        and recipe.owner_id == current_user.id
        and not recipe.is_public
    )

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

    return templates.TemplateResponse(
            request = request,
            name = "recipes/detail.html",
            context = {
                "recipe": recipe,
                "ingredient_rows": ingredient_rows,
                "categories": IngredientCategory,
                "steps": steps,
                "step_types": StepType,
                "is_admin": (
                    current_user is not None
                    and current_user.is_admin
                ),
                "can_edit": can_edit,
                "is_owned_private_recipe": is_owned_private_recipe,
            },
    )


# API for generating the editing form for recipe
@router.get("/recipes/{recipe_id}/edit")
def edit_recipe_form(
    recipe_id: UUID,
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    if (
        recipe.owner_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this recipe",
        )

    ingredient_statement = (
            select(RecipeIngredient, Ingredient)
            .join(
                Ingredient,
                RecipeIngredient.ingredient_id == Ingredient.id,
            )
            .where(RecipeIngredient.recipe_id == recipe_id)
    )
    ingredient_rows = db.execute(ingredient_statement).all()

    step_statement = (
            select(RecipeStep)
            .where(RecipeStep.recipe_id == recipe_id)
            .order_by(RecipeStep.step_number)
    )
    steps = db.scalars(step_statement).all()

    return templates.TemplateResponse(
            request = request,
            name = "recipes/edit.html",
            context = {
                "recipe": recipe,
                "ingredient_rows": ingredient_rows,
                "steps": steps,
                "categories": IngredientCategory,
                "step_types": StepType,
            },
    )


# API to modify the recipe
@router.post("/recipes/{recipe_id}/edit")
def update_recipe(
    recipe_id: UUID,
    recipe_name: str = Form(...),
    cuisine: str = Form(""),
    cook_time: int = Form(...),
    servings: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):

    statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    if (
        recipe.owner_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
            status_code=403,
            detail="You are not allowed to edit this recipe",
        )

    recipe.recipe_name = recipe_name.strip()
    recipe.cuisine = cuisine.strip() or None
    recipe.cook_time = cook_time
    recipe.servings = servings
    recipe.updated_at = datetime.now(UTC)

    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit",
            status_code = 303,
    )


# API to delete a recipe
@router.post("/recipes/{recipe_id}/delete")
def delete_recipe(
    recipe_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    statement = select(Recipe).where(Recipe.id == recipe_id)
    recipe = db.scalar(statement)

    if recipe is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe not found",
        )

    if (
        recipe.owner_id != current_user.id
        and not current_user.is_admin
    ):
        raise HTTPException(
                status_code = 403,
                detail = "You are not allowed to delete this recipe",
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

