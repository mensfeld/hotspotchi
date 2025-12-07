"""
FastAPI application for HotSpotchi web dashboard.
"""

from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from hotspotchi import __version__
from hotspotchi.config import HotSpotchiConfig, load_config
from hotspotchi.web.routes import router

# Default config file location
DEFAULT_CONFIG_PATH = Path("/etc/hotspotchi/config.yaml")

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


def _load_server_config() -> HotSpotchiConfig:
    """Load config from file or use defaults."""
    if DEFAULT_CONFIG_PATH.exists():
        return load_config(DEFAULT_CONFIG_PATH)
    return HotSpotchiConfig()


def run_server(
    host: Optional[str] = None,
    port: Optional[int] = None,
    reload: bool = False,
) -> None:
    """Run the web server.

    Args:
        host: Host to bind to (default: from config or 0.0.0.0)
        port: Port to listen on (default: from config or 8080)
        reload: Enable auto-reload for development
    """
    import uvicorn

    # Load config from file for defaults
    config = _load_server_config()
    effective_host = host if host is not None else config.web_host
    effective_port = port if port is not None else config.web_port

    print(f"Starting HotSpotchi Web Dashboard on http://{effective_host}:{effective_port}")
    uvicorn.run(
        "hotspotchi.web.app:app",
        host=effective_host,
        port=effective_port,
        reload=reload,
    )


if __name__ == "__main__":
    run_server()
