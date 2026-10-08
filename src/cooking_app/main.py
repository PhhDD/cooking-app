from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.responses import RedirectResponse

from cooking_app.web.routes import router as recipe_router

BASE_DIRECTORY = Path(__file__).resolve().parent
STATIC_DIRECTORY = BASE_DIRECTORY / "static"

app = FastAPI(
        title = "Cooking App",
        description = "A personal recipe management application",
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
