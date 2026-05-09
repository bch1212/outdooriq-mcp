"""Railway-friendly entry point.

Railway exec's startCommand without a shell, so `$PORT` does not expand. We
read PORT from os.environ here and hand it to uvicorn programmatically.
"""
from __future__ import annotations

import os

import uvicorn


def main() -> None:
    port = int(os.getenv("PORT", "8080"))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run("server:app", host=host, port=port, log_level="info")


if __name__ == "__main__":
    main()
