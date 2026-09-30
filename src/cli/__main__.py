"""Launch with python -m src.cli from the repository root."""

from .main import main
import sys


if __name__ == "__main__":
    code = main()
    # A broken pipe may retain buffered text after main catches the write error.
    # Close it here so interpreter shutdown cannot emit a second traceback.
    try:
        sys.stdout.close()
    except OSError:
        code = 1
    raise SystemExit(code)
