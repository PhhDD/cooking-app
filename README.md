# Cooking App

A recipe management web app for organising recipes, saving favourites, and importing recipes from YouTube into a personal vault.

## Live Website

[Open the Cooking App](https://cooking-app-2qcn.onrender.com/)

## Features

- Public recipe browsing
- Private user recipe vault
- Logto authentication
- Recipe ingredients and preparation steps
- Recipe copying into a user’s vault
- YouTube recipe import
- Gemini-powered recipe extraction
- Import status tracking
- Duplicate import detection
- Failed import retry and deletion
- PostgreSQL database with Alembic migrations

## AI Workflow

The current YouTube workflow is:

1. The user pastes a YouTube URL.
2. The app retrieves public video metadata.
3. Gemini extracts a structured recipe.
4. Pydantic validates the AI response.
5. The recipe, ingredients, and steps are saved to the user’s private vault.

Transcript extraction is being kept as a future optional adapter. The current workflow does not depend on unofficial transcript scraping.

## Technology

- Python
- FastAPI
- SQLAlchemy
- PostgreSQL
- Alembic
- Jinja2
- Logto
- Gemini API
- Render

## Local Development

Install dependencies:

```bash
uv sync
