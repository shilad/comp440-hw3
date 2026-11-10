"""Start the results viewer on its own, for when the homework page is not running.

    uv run python -m viewer              # opens http://127.0.0.1:8452/ in your browser
    uv run python -m viewer --no-open    # the same, without opening the browser
    uv run python -m viewer --port 8460

It listens on this computer only (127.0.0.1), makes no network calls, and only reads the files
in runs/. Stop it with Ctrl-C.
"""

from __future__ import annotations

import argparse
import errno
import sys
import threading
import webbrowser
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlsplit

from . import app

HOST = "127.0.0.1"
DEFAULT_PORT = 8452
CSP = ("default-src 'none'; script-src 'self'; style-src 'self'; img-src 'self' data:; "
       "base-uri 'none'; form-action 'self'; frame-ancestors 'none'")


def make_handler(repo: Path):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):  # keep the terminal quiet
            pass

        def respond(self, send_body: bool):
            url = urlsplit(self.path)
            status, ctype, body = app.handle(self.command, url.path, parse_qs(url.query), repo)
            self.send_response(status)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", CSP)
            self.end_headers()
            if send_body:
                self.wfile.write(body)

        def do_GET(self):
            self.respond(True)

        def do_HEAD(self):
            self.respond(False)

        def do_POST(self):
            self.respond(True)  # handle() answers 405: the viewer only reads

    return Handler


def serve(repo: Path, port: int, tries: int = 20) -> ThreadingHTTPServer:
    """A server on the first free port from `port` up."""
    last = None
    for p in range(port, port + tries):
        try:
            return ThreadingHTTPServer((HOST, p), make_handler(repo))
        except OSError as error:
            if error.errno not in (errno.EADDRINUSE, errno.EACCES):
                raise
            last = error
    raise SystemExit(f"No free port between {port} and {port + tries - 1}: {last}")


def main(argv=None) -> None:
    parser = argparse.ArgumentParser(prog="python -m viewer", description="Read your runs in a browser.")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT,
                        help=f"the port to try first (default {DEFAULT_PORT}; the next free one if taken)")
    parser.add_argument("--no-open", action="store_true", help="don't open the browser")
    parser.add_argument("--repo", type=Path, default=Path(__file__).resolve().parent.parent,
                        help="the homework repository (default: the one this viewer is in)")
    args = parser.parse_args(argv)

    app.PREFIX = ""  # on its own, the pages are at the top of the site
    repo = args.repo.resolve()
    server = serve(repo, args.port)
    url = f"http://{HOST}:{server.server_address[1]}/"
    print(f"The results viewer is at {url}\nIt reads {repo / 'runs'}. Stop it with Ctrl-C.", flush=True)
    if not args.no_open:
        threading.Timer(0.3, lambda: webbrowser.open(url)).start()
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopped.")
    finally:
        server.server_close()


if __name__ == "__main__":
    sys.exit(main())
