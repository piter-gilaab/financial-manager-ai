"""Public FastAPI factory; importing core/CLI never imports this package."""

from .app import create_app

__all__ = ["create_app"]

