from sqlalchemy import select

from cooking_app.database import SessionLocal
from cooking_app.models.recipe import Recipe


session = SessionLocal()

recipe = Recipe(
    cook_time=1800,
    servings=2,
    cuisine="Chinese",
)

session.add(recipe)
session.commit()

print("Inserted:", recipe.id)
print("Inserted language:", recipe.source_lang)


statement = select(Recipe).where(Recipe.id == recipe.id)

result = session.execute(statement)
retrieved_recipe = result.scalar_one()

print("Retrieved:", retrieved_recipe.id)
print("Retrieved language:", retrieved_recipe.source_lang)
print("Retrieved cuisine:", retrieved_recipe.cuisine)

session.delete(retrieved_recipe)
session.commit()

print("Test recipe deleted")

session.close()
