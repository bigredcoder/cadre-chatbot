"""Web routes for Cadence. Routes only: logic lives in the other app/ modules."""
from pathlib import Path

from fastapi import FastAPI
from fastapi.responses import FileResponse

ROOT = Path(__file__).resolve().parent.parent  # Vercel runs from the project root

app = FastAPI(title="Cadence", docs_url=None, redoc_url=None)


@app.get("/api/health")
def health() -> dict:
    """Lets us (and Vercel) confirm the app is up."""
    return {"status": "ok"}


@app.get("/")
def home() -> FileResponse:
    """The demo page with the chat bubble."""
    return FileResponse(ROOT / "public" / "index.html")
