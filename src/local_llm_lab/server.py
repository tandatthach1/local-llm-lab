from __future__ import annotations

import functools
import http.server
import socketserver
from pathlib import Path


def serve_directory(directory: str | Path, *, host: str = "127.0.0.1", port: int = 8787) -> None:
    root = Path(directory).resolve()
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(root))
    with socketserver.TCPServer((host, port), handler) as httpd:
        print(f"Serving {root} at http://{host}:{port}/")
        httpd.serve_forever()

