"""Run a victim-api app in a background thread for the length of a `with` block."""

import socket
import threading
import time
from contextlib import contextmanager

import uvicorn


@contextmanager
def serve(app, host="127.0.0.1", port=0, quiet=False):
    """Start uvicorn on host:port (0 = a free port) and yield the base URL; stop it on exit."""
    if port == 0:
        with socket.socket() as s:
            s.bind((host, 0))
            port = s.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host=host, port=port, log_level="warning", access_log=False))
    t = threading.Thread(target=server.run, daemon=True)
    t.start()
    deadline = time.time() + 20
    while not server.started:
        if not t.is_alive() or time.time() > deadline:
            raise RuntimeError(f"victim-api did not start on {host}:{port}")
        time.sleep(0.05)
    url = f"http://{host}:{port}"
    if not quiet:
        print(f"[note] victim-api listening on {url} (inside this container only)", flush=True)
    try:
        yield url
    finally:
        server.should_exit = True
        t.join(timeout=10)
