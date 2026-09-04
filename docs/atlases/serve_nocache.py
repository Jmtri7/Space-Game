"""Same as `python -m http.server`, but every response carries
`Cache-Control: no-store` - plain http.server sends only `Last-Modified`,
which lets a browser reuse a stale cached copy of editor.html (or a design
JSON) across reloads instead of re-fetching the just-edited file. Run this
from the repo root exactly like http.server:

    python docs/atlases/serve_nocache.py 8777

See docs/GRAPHICS_PIPELINE.md's "Editing a design with the agent" section.
"""
import functools
import http.server
import sys


class NoCacheHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    handler = functools.partial(NoCacheHandler, directory=".")
    # explicit IPv4 bind - http.server.test()'s own default differs from
    # `python -m http.server`'s (which dual-stack-binds "::" so 127.0.0.1
    # still resolves); without this, 127.0.0.1 connections can be refused.
    http.server.test(HandlerClass=handler, port=port, bind="127.0.0.1")
