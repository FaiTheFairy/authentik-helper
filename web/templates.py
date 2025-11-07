# web/templates.py
from __future__ import annotations

from importlib.resources import files
from fastapi.templating import Jinja2Templates

# single shared jinja2 environment for all routers
_TEMPLATES_DIR = files(__package__).joinpath("templates")
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR))
