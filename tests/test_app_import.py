import sys
from pathlib import Path
import importlib

# Ensure project root (where app.py lives) is importable
ROOT = Path(__file__).resolve().parents[1]
p = str(ROOT)
if p not in sys.path:
    sys.path.insert(0, p)


def test_import_app_module_creates_app():
    m = importlib.import_module("app")
    assert hasattr(m, "app")
