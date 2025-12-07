"""
FastAPI application for HotSpotchi web dashboard.
"""

from pathlib import Path

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from hotspotchi import __version__
from hotspotchi.config import HotSpotchiConfig
from hotspotchi.web.routes import router

# Paths
WEB_DIR = Path(__file__).parent
STATIC_DIR = WEB_DIR / "static"
TEMPLATES_DIR = WEB_DIR / "templates"

# Create FastAPI app
app = FastAPI(
    title="HotSpotchi Dashboard",
    description="Web interface for Tamagotchi Uni WiFi Hotspot",
    version=__version__,
)

# Mount static files if directory exists
if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Templates
templates = Jinja2Templates(directory=TEMPLATES_DIR)

# Include API routes
app.include_router(router, prefix="/api")


@app.get("/", response_class=HTMLResponse)
async def dashboard(request: Request) -> HTMLResponse:
    """Render the main dashboard page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "version": __version__,
        },
    )


@app.get("/health")
async def health() -> dict:
    """Health check endpoint."""
    return {"status": "ok", "version": __version__}


def run_server(
    host: str = "0.0.0.0",
    port: int = 8080,
    reload: bool = False,
) -> None:
    """Run the web server.

    Args:
        host: Host to bind to
        port: Port to listen on
        reload: Enable auto-reload for development
    """
    import uvicorn

    config = HotSpotchiConfig()
    print(f"Starting HotSpotchi Web Dashboard on http://{host}:{port}")
    uvicorn.run(
        "hotspotchi.web.app:app",
        host=host,
        port=port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
