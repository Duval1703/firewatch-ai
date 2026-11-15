from pathlib import Path

from src.firewatch.api import app


app.frontend(
    "/",
    directory=Path(__file__).parent / "web" / "dist",
    fallback="index.html",
    check_dir=False,
)
