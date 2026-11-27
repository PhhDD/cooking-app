import os
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.exception_handlers import http_exception_handler
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.middleware.sessions import SessionMiddleware

from cooking_app.database import SessionLocal
from cooking_app.models.recipe_import import (
    RecipeImport,
    RecipeImportStatus,
)
from cooking_app.web.auth_router import router as auth_router
from cooking_app.web.ingredient_router import router as ingredient_router
from cooking_app.web.recipe_router import router as recipe_router
from cooking_app.web.step_router import router as step_router
from cooking_app.web.templates import templates

BASE_DIRECTORY = Path(__file__).resolve().parent
STATIC_DIRECTORY = BASE_DIRECTORY / "static"


def recover_interrupted_imports() -> None:
    db = SessionLocal()

    try:
        interrupted_jobs = db.scalars(
            select(RecipeImport).where(
                RecipeImport.status == RecipeImportStatus.PROCESSING,
            )
        ).all()

        for job in interrupted_jobs:
            job.status = RecipeImportStatus.FAILED
            job.error_message = (
                "This import was interrupted because "
                "the application stopped before it finished."
            )

        db.commit()

    finally:
        db.close()


@asynccontextmanager
async def lifespan(_: FastAPI):
    recover_interrupted_imports()
    yield


app = FastAPI(
    title="Cooking App",
    description="A personal recipe management application",
    lifespan=lifespan,
)


@app.get("/health", include_in_schema = False)
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.exception_handler(StarletteHTTPException)
async def custom_http_exception_handler(
    request: Request,
    exc: StarletteHTTPException,
):
    if exc.status_code == 404:
        template_name = "errors/404.html"
    elif exc.status_code == 403:
        template_name = "errors/403.html"
    else:
        return await http_exception_handler(request, exc)

    return templates.TemplateResponse(
        request=request,
        name=template_name,
        context={
            "detail": exc.detail,
        },
        status_code=exc.status_code,
    )

app.add_middleware(
        SessionMiddleware,
        secret_key = os.environ["SESSION_SECRET_KEY"],
        same_site = "lax",
        https_only = False,
)


@app.get("/", include_in_schema=False)
def home() -> RedirectResponse:
    return RedirectResponse(url = "/recipes")


app.mount(
        "/static",
        StaticFiles(directory = STATIC_DIRECTORY),
        name = "static",
)


app.include_router(recipe_router)
app.include_router(step_router)
app.include_router(ingredient_router)
app.include_router(auth_router)
