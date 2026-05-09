"""Railway railpack auto-detect entry.

Railway's railpack builder auto-runs `uvicorn main:app`. We re-export the
FastAPI app from server.py so that command works without overriding the
build pipeline.
"""
from server import app  # noqa: F401

__all__ = ["app"]
