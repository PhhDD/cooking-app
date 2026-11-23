from pathlib import Path

from fastapi.templating import Jinja2Templates

from cooking_app.auth import get_auth_template_context

TEMPLATES_DIRECTORY = Path(__file__).resolve().parent.parent / "templates"

templates = Jinja2Templates(
        directory = TEMPLATES_DIRECTORY,
        context_processors = [get_auth_template_context],
)
