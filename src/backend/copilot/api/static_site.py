"""Serves the built React frontend from the API service, so one Cloud Run service hosts the whole app on one origin.

Built assets are served as static files; any other path that is not an API route returns index.html, so client-side
routes such as /approvals load directly. Without a build (local development with Vite) nothing is mounted.
"""
from __future__ import annotations

import logging
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

logger = logging.getLogger(__name__)
INDEX_FILE = "index.html"
ASSETS_DIR = "assets"
API_PREFIX = "api/"
NOT_FOUND = 404


def mount_frontend(app: FastAPI, dist_dir: Path) -> bool:
    """Serve the build in dist_dir if it exists; return whether it was mounted."""
    index = dist_dir / INDEX_FILE
    if not index.exists():
        logger.info("No frontend build at %s; serving the API only", dist_dir)
        return False
    if (dist_dir / ASSETS_DIR).is_dir():
        app.mount("/" + ASSETS_DIR, StaticFiles(directory=dist_dir / ASSETS_DIR), name=ASSETS_DIR)

    @app.get("/{path:path}", include_in_schema=False)
    async def frontend(path: str) -> FileResponse:
        if path.startswith(API_PREFIX):
            raise HTTPException(NOT_FOUND, f"No API route /{path}")
        candidate = (dist_dir / path).resolve()
        if path and candidate.is_file() and dist_dir.resolve() in candidate.parents:
            return FileResponse(candidate)
        return FileResponse(index)

    return True
