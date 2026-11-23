from datetime import UTC, datetime
from uuid import UUID

from fastapi import APIRouter, Depends, Form, HTTPException
from fastapi.responses import RedirectResponse
from sqlalchemy import delete, func, or_, select
from sqlalchemy.orm import Session

from cooking_app.models.recipe_step import RecipeStep, StepType
from cooking_app.models.recipe_step_dependency import RecipeStepDependency
from cooking_app.models.user import User
from cooking_app.web.authorisation import get_recipe_or_404, require_recipe_editor
from cooking_app.web.dependencies import get_current_user, get_db


def swap_step_numbers(
    current_step: RecipeStep,
    other_step: RecipeStep,
    steps: list[RecipeStep],
    db: Session,
) -> None:
    current_number = current_step.step_number
    other_number = other_step.step_number

    temporary_number = max(
            step.step_number for step in steps
    ) + 1

    current_step.step_number = temporary_number
    db.flush()

    other_step.step_number = current_number
    db.flush()
    
    current_step.step_number = other_number
    db.flush()


router = APIRouter()

# API for adding steps, which follows the same pattern as adding ingredient
@router.post("/recipes/{recipe_id}/steps")
def add_step(
    recipe_id: UUID,
    instruction: str = Form(...),
    duration: int = Form(...),
    step_type: StepType = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)
    
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
    recipe.updated_at = datetime.now(UTC)
    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit",
            status_code = 303,
    )


# API route for updating the steps
@router.post("/recipes/{recipe_id}/steps/{step_id}/edit")
def update_step(
    recipe_id: UUID,
    step_id: UUID,
    step_type: StepType = Form(...),
    instruction: str = Form(...),
    duration: int = Form(...),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    step_statement = select(RecipeStep).where(
            RecipeStep.id == step_id,
            RecipeStep.recipe_id == recipe_id,
    )
    step = db.scalar(step_statement)

    if step is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe step not found",
        )

    step.step_type = step_type
    step.instruction = instruction.strip()
    step.duration = duration
    recipe.updated_at = datetime.now(UTC)

    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit#step-{step_id}",
            status_code = 303,
    )


# API route to delete a step
@router.post("/recipes/{recipe_id}/steps/{step_id}/delete")
def delete_step(
    recipe_id: UUID,
    step_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    step_statement = select(RecipeStep).where(
            RecipeStep.id == step_id,
            RecipeStep.recipe_id == recipe_id,
    )
    step = db.scalar(step_statement)

    if step is None:
        raise HTTPException(
                status_code = 404,
                detail = "Recipe step not found",
        )
    current_number = step.step_number
    
    db.execute(
            delete(RecipeStepDependency).where(
                or_(
                    RecipeStepDependency.predecessor_step_id == step_id,
                    RecipeStepDependency.successor_step_id == step_id,
                )
            )
    )
    db.delete(step)
    db.flush()

    # Renumber the remaining steps
    remaining_steps = db.scalars(
            select(RecipeStep)
            .where(
                RecipeStep.recipe_id == recipe_id,
                RecipeStep.step_number > current_number
            )
            .order_by(RecipeStep.step_number)
    ).all()

    for number, remaining_step in enumerate(remaining_steps, start=current_number):
        remaining_step.step_number = number

    recipe.updated_at = datetime.now(UTC)

    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit#steps",
            status_code = 303,
    )


# API for move up one step
@router.post("/recipes/{recipe_id}/steps/{step_id}/move-up")
def move_step_up(
    recipe_id: UUID,
    step_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    steps = db.scalars(
            select(RecipeStep)
            .where(RecipeStep.recipe_id == recipe_id)
            .order_by(RecipeStep.step_number)
    ).all()

    current_index = next(
        (index for index, step in enumerate(steps) if step.id == step_id),
        None,
    )

    if current_index is None:
        raise HTTPException(
                status_code = 404,
                detail = "Step not found",
        )

    if current_index == 0:
        return RedirectResponse(
                url = f"/recipes/{recipe_id}/edit#step-{step_id}",
                status_code = 303,
        )

    current_step = steps[current_index]
    other_step = steps[current_index - 1]

    swap_step_numbers(
            current_step = current_step,
            other_step = other_step,
            steps = steps,
            db = db,
    )

    recipe.updated_at = datetime.now(UTC)

    db.commit()

    return RedirectResponse(
            url = f"/recipes/{recipe_id}/edit#step-{step_id}",
            status_code = 303,
    )


# API route for move down one step
@router.post("/recipes/{recipe_id}/steps/{step_id}/move-down")
def move_step_down(
    recipe_id: UUID,
    step_id: UUID,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    recipe = get_recipe_or_404(recipe_id, db)
    require_recipe_editor(recipe, current_user)

    steps = db.scalars(
        select(RecipeStep)
        .where(RecipeStep.recipe_id == recipe_id)
        .order_by(RecipeStep.step_number)
    ).all()

    current_index = next(
        (index for index, step in enumerate(steps) if step.id == step_id),
        None,
    )

    if current_index is None:
        raise HTTPException(
            status_code=404,
            detail="Step not found",
        )

    if current_index < len(steps) - 1:
        current_step = steps[current_index]
        other_step = steps[current_index + 1]

        swap_step_numbers(
            current_step=current_step,
            other_step=other_step,
            steps=steps,
            db=db,
        )

        recipe.updated_at = datetime.now(UTC)
        db.commit()

    return RedirectResponse(
        url=f"/recipes/{recipe_id}/edit#step-{step_id}",
        status_code=303,
    )
