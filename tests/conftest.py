"""Shared pytest fixtures.

Provides a localhost static file server serving tests/fixtures, so integration
tests can audit real http:// pages without external network access (which is
required for the Node engines and the crawler).
"""

from __future__ import annotations

import functools
import http.server
import socketserver
import threading
from pathlib import Path

import pytest

FIXTURES = Path(__file__).parent / "fixtures"


class _QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *args):  # silence request logging
        pass


@pytest.fixture(scope="session")
def fixture_server():
    """Serve tests/fixtures over http://127.0.0.1:<port>/ for the test session."""
    handler = functools.partial(_QuietHandler, directory=str(FIXTURES))
    socketserver.TCPServer.allow_reuse_address = True
    httpd = socketserver.TCPServer(("127.0.0.1", 0), handler)
    port = httpd.server_address[1]
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        httpd.shutdown()
        httpd.server_close()
