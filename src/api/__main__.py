"""Safe local development entry point: python -m src.api."""

import os
from urllib.parse import urlsplit
import uvicorn

from . import create_app


def _development_cors_origins(value: str | None) -> tuple[str, ...]:
    """Parse an explicit loopback-only development origin allowlist."""
    if not value:
        return ()
    origins = tuple(item.strip().rstrip("/") for item in value.split(",") if item.strip())
    for origin in origins:
        parsed = urlsplit(origin)
        if (parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}
                or parsed.path or parsed.query or parsed.fragment):
            raise ValueError("FINANCIAL_API_CORS_ORIGINS accepts only explicit HTTP loopback origins.")
    return origins


if __name__ == "__main__":
    app = create_app(cors_origins=_development_cors_origins(
        os.environ.get("FINANCIAL_API_CORS_ORIGINS"),
    ))
    uvicorn.run(app, host="127.0.0.1", port=8000)
