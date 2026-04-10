"""
Static file serving — serves the frontend index.html from /
Add this to main.py when deploying as a single service on Render.
"""
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
import os

FRONTEND_DIR = os.path.join(os.path.dirname(__file__), "..", "frontend")


def mount_frontend(app):
    """Mount frontend and serve index.html for all non-API routes."""
    if os.path.exists(FRONTEND_DIR):
        app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")

        @app.get("/{full_path:path}", include_in_schema=False)
        async def serve_frontend(full_path: str):
            index = os.path.join(FRONTEND_DIR, "index.html")
            return FileResponse(index)
