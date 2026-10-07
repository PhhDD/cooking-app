from sqlalchemy.exc import IntegrityError

from cooking_app.database import SessionLocal
from cooking_app.models.recipe import Recipe
from cooking_app.models.recipe_step import RecipeStep, StepType
from cooking_app.models.recipe_step_dependency import RecipeStepDependency


session = SessionLocal()

try:
    recipe_a = Recipe(
        recipe_name="Recipe A",
        cook_time=600,
        servings=2,
        cuisine="Test",
    )

    recipe_b = Recipe(
        recipe_name="Recipe B",
        cook_time=600,
        servings=2,
        cuisine="Test",
    )

    session.add_all([recipe_a, recipe_b])
    session.flush()

    step_a = RecipeStep(
        recipe_id=recipe_a.id,
        step_number=1,
        step_type=StepType.PREPARATION,
        instruction="Step A1",
        duration=60,
    )

    step_b = RecipeStep(
        recipe_id=recipe_b.id,
        step_number=1,
        step_type=StepType.PREPARATION,
        instruction="Step B1",
        duration=60,
    )

    session.add_all([step_a, step_b])
    session.flush()

    # Deliberately invalid:
    # recipe_id belongs to Recipe A,
    # but successor_step_id belongs to Recipe B.
    dependency = RecipeStepDependency(
        recipe_id=recipe_a.id,
        predecessor_step_id=step_a.id,
        successor_step_id=step_b.id,
    )

    session.add(dependency)

    try:
        session.commit()
        print("ERROR: Cross-recipe dependency was accepted!")
    except IntegrityError:
        session.rollback()
        print("SUCCESS: Cross-recipe dependency was rejected.")

finally:
    # Clean up the temporary recipes and steps.
    session.query(RecipeStep).filter(
        RecipeStep.recipe_id.in_([recipe_a.id, recipe_b.id])
    ).delete(synchronize_session=False)

    session.query(Recipe).filter(
        Recipe.id.in_([recipe_a.id, recipe_b.id])
    ).delete(synchronize_session=False)

    session.commit()
    session.close()
