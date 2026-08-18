#!/usr/bin/env python3
"""Local static server that disables browser caching (avoids stale events JSON)."""
import functools
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer


class NoCacheHandler(SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()


if __name__ == "__main__":
    port = 8000
    handler = functools.partial(NoCacheHandler, directory=".")
    with ThreadingHTTPServer(("127.0.0.1", port), NoCacheHandler) as httpd:
        print(f"Serving on http://127.0.0.1:{port} (cache disabled)")
        httpd.serve_forever()
