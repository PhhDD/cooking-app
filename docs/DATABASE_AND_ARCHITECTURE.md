# Cooking App — Database & Architecture Documentation

## 1. Project Overview

This document records the database design, architecture decisions, and implementation work completed for the cooking app so far.

The app is being built as a Python web application with a PostgreSQL database hosted on Neon. The core idea is more than simply storing and displaying recipes: recipes are being structured so that they can later be treated as an optimisation problem.

A recipe will eventually be represented as a set of tasks with:

- durations
- preparation/cooking types
- logical dependencies
- people/resource requirements
- cookware/resources
- scheduling constraints

The long-term goal is to generate an optimised cooking schedule, for example by minimising total cooking time or maximising participation, while respecting the dependency graph and available resources.

The current phase deliberately focuses on the **core recipe data model** needed to add, manage, and display recipes before implementing the more advanced scheduling functionality.

---

## 2. Current Technology Stack

### Database

- PostgreSQL
- Neon free tier

### Python database layer

- SQLAlchemy
- Alembic
- `psycopg` 3 PostgreSQL driver
- `uuid6` for UUIDv7 generation

The database connection uses:

```text
postgresql+psycopg://...
```

### Current architecture

The project uses SQLAlchemy declarative models with a shared `Base`:

```python
class Base(DeclarativeBase):
    pass
```

Alembic imports the model package so that all registered models are included in `Base.metadata` during migration autogeneration.

---

# 3. Design Principles

Several architectural decisions were made deliberately.

## 3.1 Recipe presentation order is not the same as logical dependency order

A recipe has a human-facing `step_number`.

For example:

```text
1. Chop the onion
2. Heat the pan
3. Add the onion
```

However, the number itself is not intended to define the actual optimisation dependency graph.

The actual logical relationship is stored separately in:

```text
recipe_step_dependencies
```

This allows the optimiser to discover that independent tasks can potentially happen in parallel.

For example:

```text
Chop onion ──────┐
                 ├──> Add onion to pan
Heat pan ────────┘
```

Therefore:

- `step_number` = presentation/order
- `recipe_step_dependencies` = logical prerequisites

This separation is fundamental to the future scheduling system.

---

## 3.2 Recipe steps and ingredients are different concepts

The database separates:

### Ingredients

What the recipe requires:

```text
1 onion
1 tbsp olive oil
0.5 tsp salt
```

### Recipe steps

What the cook does:

```text
Dice the onion.
Heat the olive oil.
Add the onion.
Season with salt.
```

This is why ingredients are represented through:

```text
ingredients
recipe_ingredients
```

while actions are represented through:

```text
recipe_steps
```

---

## 3.3 Reusable ingredient catalogue

Ingredients are stored in a reusable catalogue rather than being duplicated for every recipe.

Conceptually:

```text
ingredients
    |
    +---- recipe_ingredients ---- recipes
```

For example, `Onion` exists once in `ingredients` and can be associated with many recipes through `recipe_ingredients`.

---

## 3.4 Preparation is intentionally simple

Ingredient preparation is currently represented by a simple string:

```text
diced
sliced
minced
chopped
```

We deliberately did not create a more complicated preparation hierarchy.

The distinction is:

```text
recipe_ingredients.preparation
```

describes the required state of the ingredient, while:

```text
recipe_steps
```

describes the action used to achieve that state.

---

# 4. Current Database Schema

The current core schema contains five data models:

1. `Recipe`
2. `RecipeStep`
3. `RecipeStepDependency`
4. `Ingredient`
5. `RecipeIngredient`

The conceptual structure is:

```text
recipes
   |
   +-------------------- recipe_steps
   |                          |
   |                          +---- recipe_step_dependencies
   |
   +-------------------- recipe_ingredients
                              |
                              +---- ingredients
```

---

# 5. Data Model: Recipe

## Table

```text
recipes
```

## Purpose

Stores the core metadata for a recipe.

## Model

```python
class Recipe(Base):
    __tablename__ = "recipes"

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    recipe_name: Mapped[str] = mapped_column(
        String(100)
    )

    source_lang: Mapped[SourceLang] = mapped_column(
        SQLEnum(
            SourceLang,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        default=SourceLang.ENGLISH,
    )

    cook_time: Mapped[int] = mapped_column(
        Integer
    )

    servings: Mapped[int] = mapped_column(
        Integer
    )

    cuisine: Mapped[str] = mapped_column(
        String(30)
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now,
    )
```

## Fields

| Field | Type | Purpose |
|---|---|---|
| `id` | PostgreSQL UUID | Primary key |
| `recipe_name` | `String(100)` | Recipe name |
| `source_lang` | PostgreSQL enum | Language of the source recipe |
| `cook_time` | `Integer` | Total recipe cook time, stored in seconds |
| `servings` | `Integer` | Number of servings |
| `cuisine` | `String(30)` | Cuisine classification |
| `created_at` | `DateTime` | Creation timestamp |
| `updated_at` | `DateTime` | Last-update timestamp |

## `SourceLang` enum

```python
class SourceLang(str, Enum):
    ENGLISH = "en"
    CHINESE = "zh"
```

The PostgreSQL enum is named:

```text
sourcelang
```

and contains:

```text
en
zh
```

The enum was deliberately used rather than an unrestricted string because the application currently supports a defined set of source languages.

### Default behaviour

```python
default=SourceLang.ENGLISH
```

is an SQLAlchemy application-side default used when the row is inserted.

An important observation made during testing was that the default is not necessarily visible immediately when simply constructing the Python object. It is applied during SQLAlchemy's insert/flush process.

---

# 6. Data Model: RecipeStep

## Table

```text
recipe_steps
```

## Purpose

Stores individual preparation and cooking actions belonging to a recipe.

## Model

```python
class RecipeStep(Base):
    __tablename__ = "recipe_steps"

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "step_number",
            name="uq_recipe_step_number",
        ),
        UniqueConstraint(
            "recipe_id",
            "id",
            name="uq_recipe_step_recipe_id_id",
        ),
    )

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    recipe_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id"),
        nullable=False,
    )

    step_number: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    step_type: Mapped[StepType] = mapped_column(
        SQLEnum(
            StepType,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )

    instruction: Mapped[str] = mapped_column(
        Text,
        nullable=False,
    )

    duration: Mapped[int] = mapped_column(
        Integer,
        nullable=False,
    )

    created_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
    )

    updated_at: Mapped[datetime] = mapped_column(
        default=datetime.now,
        onupdate=datetime.now,
    )
```

## `StepType` enum

```python
class StepType(str, Enum):
    PREPARATION = "preparation"
    COOKING = "cooking"
```

The PostgreSQL enum is named:

```text
steptype
```

## Fields

| Field | Type | Nullability | Purpose |
|---|---|---|---|
| `id` | PostgreSQL UUID | NOT NULL | Primary key |
| `recipe_id` | PostgreSQL UUID | NOT NULL | Recipe owning the step |
| `step_number` | `Integer` | NOT NULL | Human-facing/display order |
| `step_type` | PostgreSQL enum | NOT NULL | Preparation or cooking |
| `instruction` | `Text` | NOT NULL | Human-readable instruction |
| `duration` | `Integer` | NOT NULL | Duration in seconds |
| `created_at` | `DateTime` | NOT NULL by application design | Creation timestamp |
| `updated_at` | `DateTime` | NOT NULL by application design | Update timestamp |

## Constraints

### Step number is unique within a recipe

```text
UNIQUE(recipe_id, step_number)
```

This means:

```text
Recipe A: steps 1, 2, 3
Recipe B: steps 1, 2, 3
```

is valid.

But:

```text
Recipe A:
step 1
step 1
```

is not.

### `(recipe_id, id)` is unique

```text
UNIQUE(recipe_id, id)
```

This exists specifically to support the composite foreign keys used by `recipe_step_dependencies`.

---

# 7. Data Model: RecipeStepDependency

## Table

```text
recipe_step_dependencies
```

## Purpose

Represents logical prerequisite relationships between recipe steps.

This table is the foundation for the future recipe DAG.

A row means:

```text
predecessor_step_id
        |
        v
successor_step_id
```

The predecessor must be completed before the successor can begin.

## Model

```python
class RecipeStepDependency(Base):
    __tablename__ = "recipe_step_dependencies"

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "predecessor_step_id",
            "successor_step_id",
            name="uq_recipe_step_dependency",
        ),
        CheckConstraint(
            "predecessor_step_id <> successor_step_id",
            name="ck_recipe_step_no_self_dependency",
        ),
        ForeignKeyConstraint(
            ["recipe_id", "predecessor_step_id"],
            ["recipe_steps.recipe_id", "recipe_steps.id"],
            name="fk_dependency_predecessor",
        ),
        ForeignKeyConstraint(
            ["recipe_id", "successor_step_id"],
            ["recipe_steps.recipe_id", "recipe_steps.id"],
            name="fk_dependency_successor",
        ),
    )

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    recipe_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id"),
        nullable=False,
    )

    predecessor_step_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )

    successor_step_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        nullable=False,
    )
```

## Fields

| Field | Type | Nullability | Purpose |
|---|---|---|---|
| `id` | PostgreSQL UUID | NOT NULL | Primary key |
| `recipe_id` | PostgreSQL UUID | NOT NULL | Recipe owning the dependency |
| `predecessor_step_id` | PostgreSQL UUID | NOT NULL | Step that must happen first |
| `successor_step_id` | PostgreSQL UUID | NOT NULL | Step that depends on the predecessor |

## Constraints

### Unique dependency

```text
UNIQUE(
    recipe_id,
    predecessor_step_id,
    successor_step_id
)
```

Prevents the same dependency from being stored twice.

### No self-dependency

```text
predecessor_step_id <> successor_step_id
```

Therefore a step cannot depend on itself.

### Same-recipe enforcement

The predecessor and successor use composite foreign keys:

```text
(recipe_id, predecessor_step_id)
    -> (recipe_steps.recipe_id, recipe_steps.id)

(recipe_id, successor_step_id)
    -> (recipe_steps.recipe_id, recipe_steps.id)
```

This is important.

It prevents a dependency from accidentally connecting steps belonging to different recipes.

For example:

```text
Recipe A / Step 1
        |
        X
        |
Recipe B / Step 2
```

is rejected by the database.

## DAG responsibility

The database currently enforces:

- valid step references
- same-recipe membership
- no self-dependencies
- no duplicate edges

However, the database does **not** by itself validate that the complete graph is acyclic.

The planned architecture is:

```text
LLM
  |
  v
Proposed dependencies
  |
  v
Application validation
  |
  +--> valid DAG
  |
  +--> reject cyclic graph
  |
  v
Deterministic optimiser
```

This keeps the LLM responsible for inference rather than allowing it to directly control scheduling logic.

---

# 8. Data Model: Ingredient

## Table

```text
ingredients
```

## Purpose

Stores the reusable ingredient catalogue.

An ingredient exists independently of any specific recipe.

## Model

```python
class Ingredient(Base):
    __tablename__ = "ingredients"

    __table_args__ = (
        UniqueConstraint(
            "name",
            name="uq_ingredient_name",
        ),
    )

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    name: Mapped[str] = mapped_column(
        String(100),
        nullable=False,
    )

    category: Mapped[IngredientCategory] = mapped_column(
        SQLEnum(
            IngredientCategory,
            values_callable=lambda enum: [member.value for member in enum],
        ),
        nullable=False,
    )
```

## `IngredientCategory` enum

```python
class IngredientCategory(str, Enum):
    VEGETABLE = "vegetable"
    FRUIT = "fruit"
    MEAT = "meat"
    FISH = "fish"
    SEAFOOD = "seafood"
    DAIRY = "dairy"
    GRAIN = "grain"
    LEGUME = "legume"
    NUT = "nut"
    HERB_SPICE = "herb_spice"
    OIL_FAT = "oil_fat"
    SAUCE_CONDIMENT = "sauce_condiment"
    OTHER = "other"
```

The PostgreSQL enum is named:

```text
ingredientcategory
```

## Fields

| Field | Type | Nullability | Purpose |
|---|---|---|---|
| `id` | PostgreSQL UUID | NOT NULL | Primary key |
| `name` | `String` | NOT NULL | Ingredient name |
| `category` | PostgreSQL enum | NOT NULL | Broad ingredient category |

## Constraint

Ingredient names are currently unique:

```text
UNIQUE(name)
```

This means the catalogue initially treats an ingredient name as identifying one reusable ingredient.

## Allergens

Allergen modelling was intentionally **not** included in the current core schema.

If required later, allergens should be introduced as a separate concept rather than making the ingredient table unnecessarily complex now.

---

# 9. Data Model: RecipeIngredient

## Table

```text
recipe_ingredients
```

## Purpose

Associates an ingredient from the reusable ingredient catalogue with a particular recipe.

This is the recipe-specific relationship containing quantity, unit, and preparation information.

## Model

```python
class RecipeIngredient(Base):
    __tablename__ = "recipe_ingredients"

    __table_args__ = (
        UniqueConstraint(
            "recipe_id",
            "ingredient_id",
            name="uq_recipe_ingredient",
        ),
    )

    id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid7,
    )

    recipe_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("recipes.id"),
        nullable=False,
    )

    ingredient_id: Mapped[UUID_Python] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("ingredients.id"),
        nullable=False,
    )

    quantity: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        nullable=False,
    )

    unit: Mapped[str] = mapped_column(
        String(30),
        nullable=False,
    )

    preparation: Mapped[str | None] = mapped_column(
        String(100),
        nullable=True,
    )
```

## Fields

| Field | Type | Nullability | Purpose |
|---|---|---|---|
| `id` | PostgreSQL UUID | NOT NULL | Primary key |
| `recipe_id` | PostgreSQL UUID | NOT NULL | Recipe |
| `ingredient_id` | PostgreSQL UUID | NOT NULL | Ingredient |
| `quantity` | `NUMERIC(10,2)` | NOT NULL | Quantity required |
| `unit` | `String(30)` | NOT NULL | Unit such as `g`, `kg`, `tbsp`, `tsp` |
| `preparation` | `String(100)` | NULL | Preparation/state such as `diced` or `sliced` |

## Why `NUMERIC(10,2)`?

Recipe quantities are not necessarily integers.

Examples:

```text
0.5 kg
1.5 tbsp
0.25 tsp
```

Using PostgreSQL `NUMERIC(10,2)` allows fractional quantities without using floating-point storage.

## Constraint

```text
UNIQUE(recipe_id, ingredient_id)
```

The same ingredient therefore appears at most once in a recipe's ingredient list under the current design.

---

# 10. Example Recipe Representation

A recipe might conceptually look like:

## Recipe

```text
recipe_name: Tomato Pasta
source_lang: en
cook_time: 900
servings: 2
cuisine: Italian
```

## Ingredients

```text
ingredients

1. Pasta
2. Onion
3. Olive oil
4. Salt
5. Tomato
```

## Recipe ingredients

```text
Tomato Pasta | Pasta      | 200  | g     |
Tomato Pasta | Onion      | 1    | piece | diced
Tomato Pasta | Olive oil  | 1    | tbsp  |
Tomato Pasta | Salt       | 0.5  | tsp   |
Tomato Pasta | Tomato     | 2    | piece | diced
```

## Recipe steps

```text
1. Dice the onion
2. Dice the tomatoes
3. Bring water to a boil
4. Cook the pasta
5. Heat olive oil
6. Add onion and cook
7. Add tomatoes
8. Add pasta and combine
9. Season with salt
```

The `step_number` represents how the recipe is presented.

The dependency table can separately represent relationships such as:

```text
1 -> 6
5 -> 6
2 -> 7
6 -> 7
3 -> 4
4 -> 8
7 -> 8
8 -> 9
```

This allows the future optimiser to identify parallelisable work.

For example:

```text
Dice onion ────────────────┐
                            ├──> Cook onion
Heat olive oil ────────────┘

Dice tomatoes ─────────────┐
Cook onion ────────────────┤
                            └──> Add tomatoes
```

---

# 11. Database Integrity Testing

The dependency model was explicitly tested after migration.

The following cases were verified:

### Cross-recipe dependency

Attempting to connect a step from one recipe to a step from another recipe was rejected.

**Result: passed.**

### Valid same-recipe dependency

A valid dependency between two steps belonging to the same recipe was successfully inserted.

**Result: passed.**

### Duplicate dependency

Attempting to insert the same dependency twice was rejected by:

```text
uq_recipe_step_dependency
```

**Result: passed.**

### Self dependency

Attempting to make a step depend on itself was rejected by:

```text
ck_recipe_step_no_self_dependency
```

**Result: passed.**

These tests confirm that the database is enforcing the most important structural rules of the dependency graph.

---

# 12. Alembic Migration History

The core schema has been built incrementally through Alembic.

## Recipe table

The initial migration created the `recipes` table.

Subsequent changes added fields such as:

- `recipe_name`
- `source_lang` enum

The source-language enum was migrated to use:

```text
en
zh
```

## Recipe steps

A migration was created for:

```text
recipe_steps
```

including:

- preparation/cooking enum
- recipe-local step numbering
- duration
- instruction
- timestamps

## Recipe step dependencies

Migration:

```text
7939aac4ce2b_add_recipe_step_dependency_table.py
```

created:

```text
recipe_step_dependencies
```

An important migration-order issue was encountered.

The dependency table uses a composite foreign key referencing:

```text
(recipe_id, id)
```

on `recipe_steps`.

PostgreSQL therefore required:

```text
UNIQUE(recipe_id, id)
```

to exist before the dependency table could be created.

The migration was adjusted so that:

1. the unique constraint was created on `recipe_steps`
2. the dependency table was then created

After that, the migration succeeded.

## Ingredients

Migration:

```text
70a1ad0a9638_create_ingredient_table.py
```

created:

```text
ingredients
```

with:

- UUID primary key
- unique ingredient name
- ingredient category enum

## Recipe ingredients

Migration:

```text
a5cb5125efe2_create_recipe_ingredient_table.py
```

created:

```text
recipe_ingredients
```

with:

- UUID primary key
- foreign key to `recipes`
- foreign key to `ingredients`
- `NUMERIC(10,2)` quantity
- unit
- optional preparation
- recipe/ingredient uniqueness constraint

The generated migration was reviewed and found structurally correct.

---

# 13. SQLAlchemy / Alembic Model Registration

The project currently uses explicit model imports.

`migrations/env.py` imports:

```python
from cooking_app import models
```

and `models/__init__.py` imports each model module:

```python
from cooking_app.models.recipe import Recipe
from cooking_app.models.recipe_step import RecipeStep
from cooking_app.models.recipe_step_dependency import RecipeStepDependency
from cooking_app.models.ingredient import Ingredient
from cooking_app.models.recipe_ingredient import RecipeIngredient
```

This is necessary because SQLAlchemy needs the model modules imported so that their tables are registered with:

```python
Base.metadata
```

### Important maintenance rule

When a new model is added:

- `migrations/env.py` normally does **not** need to change.
- `models/__init__.py` needs one new model import.

This explicit approach is simple and appropriate for the current project size.

---

# 14. UUID Strategy

The models use PostgreSQL UUIDs as primary keys.

The Python default is:

```python
default=uuid7
```

UUIDv7 was chosen to provide globally unique identifiers while also having time-ordered characteristics.

The application therefore uses:

```python
UUID(as_uuid=True)
```

for PostgreSQL UUID columns and Python's UUID type for SQLAlchemy mappings.

---

# 15. Current Core Architecture

The current data model can be viewed as four conceptual layers.

## Recipe metadata

```text
recipes
```

Answers:

> What is this recipe?

## Recipe actions

```text
recipe_steps
```

Answers:

> What does the cook do?

## Recipe dependency graph

```text
recipe_step_dependencies
```

Answers:

> What must happen before what?

## Recipe ingredients

```text
ingredients
recipe_ingredients
```

Answers:

> What ingredients are required, and in what quantities/preparations?

Together:

```text
                  ┌──────────────────┐
                  │     recipes      │
                  └───────┬──────────┘
                          │
             ┌────────────┴────────────┐
             │                         │
             v                         v
    ┌─────────────────┐       ┌────────────────────┐
    │  recipe_steps   │       │ recipe_ingredients │
    └────────┬────────┘       └──────────┬─────────┘
             │                           │
             v                           v
    ┌──────────────────────┐     ┌────────────────┐
    │ recipe_step_         │     │  ingredients   │
    │ dependencies         │     └────────────────┘
    └──────────────────────┘
```

---

# 16. Planned Advanced Architecture

The current database is intentionally not the final optimisation system.

The planned architecture is:

```text
Recipe data
    |
    v
LLM dependency inference
    |
    v
Proposed dependency graph
    |
    v
Application validation
    |
    +---- invalid / cyclic -> reject
    |
    v
Valid DAG
    |
    +---- durations
    +---- people
    +---- cookware
    +---- other resources
    |
    v
Deterministic scheduler / optimiser
    |
    v
Optimised cooking plan
```

The key principle is:

> Use the LLM for semantic inference, but use deterministic application code for validation and optimisation.

This prevents the LLM from becoming the source of truth for scheduling correctness.

---

# 17. Multi-Dish Cooking

Multi-dish scheduling is planned for a later stage.

Each recipe should maintain its own independent DAG.

For example:

```text
Recipe A DAG
A1 -> A2 -> A3

Recipe B DAG
B1 -> B2 -> B3
```

When a user chooses to cook both recipes together, a future `cooking_session` layer can combine them:

```text
Cooking Session
    |
    +---- Recipe A DAG
    |
    +---- Recipe B DAG
    |
    +---- shared people/resources
    |
    +---- cross-dish constraints where genuinely necessary
```

The recipe-level dependency table should **not** be modified to represent cross-dish scheduling.

This keeps:

```text
recipe_step_dependencies
```

focused on dependencies intrinsic to one recipe.

---

# 18. Future Resource Model

Resources such as cookware and people should eventually be represented separately rather than adding many resource-specific columns to `recipe_steps`.

Potential future concepts include:

```text
people
cookware
recipe_step_resources
```

or equivalent structures.

The goal is to allow constraints such as:

```text
Step A requires one frying pan
Step B requires one frying pan
```

so that the scheduler knows these steps cannot use the same pan simultaneously.

Similarly, people can become scheduling resources:

```text
Person 1
Person 2
```

allowing independent preparation tasks to happen in parallel.

These models are intentionally not part of the current core schema.

---

# 19. LLM Integration

A future paid/subscription feature may use an LLM to infer recipe dependencies.

For example, given:

```text
1. Chop onions
2. Heat oil
3. Cook onions
4. Add tomatoes
```

the LLM could propose:

```text
1 -> 3
2 -> 3
3 -> 4
```

The application would then:

1. validate that all referenced steps exist
2. validate that they belong to the same recipe
3. reject self-dependencies
4. detect cycles
5. persist only a valid graph
6. pass the validated graph to the deterministic optimiser

The LLM therefore proposes structure rather than directly executing the optimisation algorithm.

---

# 20. Features Intentionally Deferred

The current design intentionally does **not** include:

- allergen modelling
- detailed ingredient-preparation taxonomy
- cookware/resource tables
- people/resource tables
- cooking sessions
- cross-dish scheduling
- optimisation algorithms
- LLM dependency inference
- vector search
- chat history storage
- advanced multilingual search

These can be added later without fundamentally changing the core recipe/ingredient model.

---

# 21. Current Project Status

The current core relational model is effectively in place.

### Completed

- PostgreSQL/Neon database connection
- SQLAlchemy declarative base
- Alembic migrations
- Recipe model
- Recipe source-language enum
- Recipe step model
- Preparation/cooking step enum
- Recipe-local step numbering
- Recipe dependency graph table
- Same-recipe dependency enforcement
- Duplicate dependency prevention
- Self-dependency prevention
- Ingredient catalogue
- Ingredient category enum
- Recipe/ingredient association table
- Quantity/unit/preparation support
- Database integrity testing for dependency constraints

### Current core tables

```text
recipes
recipe_steps
recipe_step_dependencies
ingredients
recipe_ingredients
```

The project is now ready to move from the database layer toward the basic application functionality:

```text
Create recipe
    |
    +-- recipe metadata
    +-- ingredients
    +-- recipe steps
    |
    v
Store recipe
    |
    v
Retrieve recipe
    |
    v
Display recipe
```

The next logical development layer is therefore the application/API layer for adding, managing, retrieving, and displaying recipes, rather than immediately implementing the advanced optimiser.

---

# 22. Important Design Decisions at a Glance

| Decision | Rationale |
|---|---|
| UUIDv7 primary keys | Globally unique, time-ordered identifiers |
| PostgreSQL enums | Controlled categorical values |
| `step_number` separate from dependencies | Presentation order should not determine optimisation order |
| Separate dependency table | Represents a proper DAG and supports parallel scheduling |
| `recipe_id` included in dependency table | Clear recipe ownership and simpler querying |
| Composite dependency FKs | Prevent cross-recipe dependencies at the database level |
| Ingredient catalogue | Reuse ingredients across recipes |
| `recipe_ingredients` association table | Stores recipe-specific quantity/unit/preparation |
| `Numeric(10,2)` quantity | Supports fractional recipe quantities |
| Simple preparation string | Avoids premature over-modelling |
| Allergens deferred | Not required for the current core functionality |
| LLM proposes dependencies | Semantic inference is appropriate for an LLM |
| Deterministic optimiser | Scheduling correctness should not depend on LLM output |
| Recipe DAGs remain independent | Enables clean multi-dish scheduling later |

---

# 23. Known Schema Detail to Check

There is one small discrepancy worth resolving before treating the documentation/schema as completely frozen.

The `Ingredient` SQLAlchemy model shown during development uses:

```python
String(100)
```

for `Ingredient.name`.

However, the generated Alembic migration shown during development contains:

```python
sa.String(length=200)
```

for the database column.

The migration itself was otherwise correct.

Before considering the schema final, the model and migration should use the same intended length. If `100` is the desired limit, the migration should be adjusted accordingly; if `200` is intentional, the model should be changed to `String(200)`.

This is a schema consistency issue rather than an architectural issue.

---

# 24. Source of Truth

The following should be treated as the architectural decisions established during this development session:

1. Recipes have separate preparation and cooking steps.
2. `step_number` is for presentation, not optimisation.
3. Logical dependencies live in `recipe_step_dependencies`.
4. Dependencies must remain within the same recipe.
5. The dependency graph is intended to be a DAG.
6. The application, rather than the LLM, is responsible for validating the graph.
7. The optimiser should operate deterministically on the validated graph.
8. Ingredients are reusable entities.
9. `recipe_ingredients` stores recipe-specific quantity, unit, and preparation.
10. Ingredient preparation remains a simple string for now.
11. Allergens are deferred.
12. Multi-dish scheduling will be handled at a future cooking-session layer rather than by modifying recipe-level dependencies.

