# Web Application Implementation

## Overview

The Cooking App is a server-rendered recipe-management web application built with FastAPI, Jinja2, SQLAlchemy, and PostgreSQL hosted on Neon.

The current application focuses on core recipe management. Users can create, view, edit, and delete recipes, then add shared ingredients and ordered cooking steps.

## Application Architecture

```text
Browser
   ↓ HTTP request
Uvicorn
   ↓
FastAPI route
   ↓
SQLAlchemy session
   ↓
Neon PostgreSQL
   ↑
Database results
   ↑
Jinja2 template
   ↑
HTML response
   ↑
Browser
```

The browser does not connect directly to Neon. All database access is handled by the FastAPI application.

## Web Layer

The application uses FastAPI routers to group related recipe routes.

Current recipe routes include:

| Method | Path | Purpose |
|---|---|---|
| GET | `/` | Redirects to `/recipes` |
| GET | `/recipes` | Displays all recipes |
| GET | `/recipes/new` | Displays the create-recipe form |
| POST | `/recipes` | Creates a recipe |
| GET | `/recipes/{recipe_id}` | Displays one recipe |
| GET | `/recipes/{recipe_id}/edit` | Displays the edit form |
| POST | `/recipes/{recipe_id}/edit` | Updates a recipe |
| POST | `/recipes/{recipe_id}/delete` | Deletes a recipe |
| POST | `/recipes/{recipe_id}/ingredients` | Adds an ingredient to a recipe |
| POST | `/recipes/{recipe_id}/steps` | Adds a cooking step to a recipe |

GET routes are primarily used to display pages. POST routes process form submissions and usually redirect back to a GET page after completing the operation.

## Database Sessions

Database sessions are created through a FastAPI dependency.

Each request:

1. Creates a new SQLAlchemy session.
2. Provides the session to the route.
3. Performs database operations.
4. Closes the session when the request finishes.

This prevents a database session from being shared across unrelated requests.

## Recipe Management

A recipe contains core information such as:

- Name
- Cuisine
- Cooking time
- Servings
- Creation timestamp
- Updated timestamp

Recipe creation and editing are handled through standard HTML forms. After a successful POST request, the application redirects to the relevant recipe page using a `303 See Other` response.

This follows the Post/Redirect/Get pattern and prevents accidental duplicate submissions when a user refreshes the page.

## Shared Ingredients

Ingredients are stored in a shared `ingredients` table.

Recipe-specific usage is stored separately in `recipe_ingredients`.

```text
ingredients
    ├── name
    └── category

recipe_ingredients
    ├── recipe_id
    ├── ingredient_id
    ├── quantity
    ├── unit
    └── preparation
```

When an ingredient is added to a recipe:

1. The submitted name is normalized.
2. The application searches for an existing ingredient.
3. If the ingredient exists, it is reused.
4. If it does not exist, a new shared ingredient is created.
5. A recipe-specific association is created.

The shared ingredient is not deleted when a recipe is deleted.

Ingredient categories are represented by a Python and PostgreSQL enum. The HTML category dropdown is generated from the Python enum so the form remains synchronized with the model.

## Cooking Steps

Cooking steps are stored in `recipe_steps`.

Each step contains:

- Recipe ID
- Step number
- Instruction
- Duration
- Step type

Step numbers are assigned automatically by finding the current highest step number for the recipe and adding one.

Steps are displayed in ascending step order on the recipe detail page.

## Recipe Deletion

Deleting a recipe requires removing its dependent rows first:

```text
recipe_step_dependencies
        ↓
recipe_ingredients
        ↓
recipe_steps
        ↓
recipes
```

Shared ingredients are deliberately preserved because they may be used by other recipes.

## Updated Timestamps

`recipes.updated_at` represents the last modification to the complete recipe.

It is updated when:

- Recipe details are edited
- An ingredient is added
- A cooking step is added
- Future ingredient or step changes occur

This treats a recipe and its ingredients and steps as one aggregate.

## Templates and Styling

The application uses Jinja2 templates.

Templates are organised as:

```text
templates/
├── base.html
└── recipes/
    ├── list.html
    ├── detail.html
    ├── new.html
    └── edit.html
```

`base.html` provides the shared HTML structure. Individual pages extend it using Jinja2 template blocks.

The current UI uses:

- Warm neutral backgrounds
- Sage green accents
- Muted terracotta highlights
- Futura with fallback fonts
- Responsive recipe cards
- Server-rendered HTML
- CSS-only layout and styling

The design aims to make the application feel calm and supportive while cooking.

## Security Considerations

Current protections include:

- Database credentials remain server-side.
- `.env.local` is not committed.
- SQLAlchemy query expressions are used instead of string-built SQL.
- Jinja2 escapes rendered values by default.
- FastAPI validates typed form fields and enum values.
- PostgreSQL constraints enforce data integrity.

Current limitations include:

- Authentication is not implemented.
- Authorization and recipe ownership are not implemented.
- CSRF protection is not implemented.
- Write and delete routes should not be publicly exposed until access control is added.

The application is currently suitable for local development and portfolio development, not production use with private user data.

## Current Development Status

Completed:

- FastAPI application setup
- Database session dependency
- Recipe list page
- Recipe detail page
- Recipe creation
- Recipe editing
- Recipe deletion
- Shared ingredient creation and reuse
- Ingredient quantities and preparation details
- Cooking step creation
- Dynamic enum-based dropdowns
- Responsive recipe-card layout
- Initial calm cooking-focused UI

## Next Development Tasks

- Edit and delete individual ingredients
- Edit and delete cooking steps
- Add keyword search
- Add English and Chinese interface support
- Add web route tests
- Add authentication and authorization
- Add deployment configuration
- Deploy a public version once access control is addressed
