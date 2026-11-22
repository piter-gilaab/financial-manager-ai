"""Export the authoritative local FastAPI schema for TypeScript generation."""

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from src.api import create_app  # noqa: E402

destination = Path(__file__).resolve().parents[1] / "openapi.json"
destination.write_text(json.dumps(create_app().openapi(), indent=2) + "\n", encoding="utf-8")
