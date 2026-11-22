"""Vercel Serverless Function entry point for the backend web service.

Vercel's Python runtime looks for an ASGI/WSGI callable named ``app`` (or a
module-level WSGI ``handler``).  FastAPI is ASGI, which Vercel supports via
this module attribute; all routes live in :mod:`backend.main`.
"""

from backend.main import app  # noqa: F401  (Vercel picks up `app` as ASGI handler)

__all__ = ["app"]
