"""Local dev server for the graphics-pipeline vertex editor
(`config/editor.html`). Two things beyond `python -m http.server`:

1. Every response carries `Cache-Control: no-store`. Plain http.server sends
   only `Last-Modified`, which lets a browser silently reuse a stale cached
   copy of `editor.html` (or a design JSON) after the file is edited.

2. A `PUT` writes the request body back to that file on disk, so the editor's
   "save checked to repo" works in any browser when served (Firefox included),
   not just the Chrome/Edge File System Access API path used when the editor
   is opened straight from disk.

Run it from the repo root, like http.server:

    python config/serve_nocache.py 8777

`open_editor.bat` starts it automatically. See docs/GRAPHICS_PIPELINE.md's
"Reading repo files" and "Saving" sections.
"""
import functools
import http.server
import os
import sys

# PUT only writes files under these repo subtrees, and only `.json`. It is a
# localhost dev tool, but this keeps a stray request from touching anything
# outside the design data.
WRITABLE_ROOTS = ("config/stories",)
ALLOWED_ORIGINS = None  # set at startup to {"http://127.0.0.1:<port>", ...}


class EditorHandler(http.server.SimpleHTTPRequestHandler):
    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def do_PUT(self):
        # Cross-origin PUT is already blocked by the browser (no CORS headers
        # here, and PUT always triggers a preflight we don't answer); the
        # Origin check is defence in depth for anything not going through fetch.
        origin = self.headers.get("Origin")
        if origin and ALLOWED_ORIGINS is not None and origin not in ALLOWED_ORIGINS:
            self.send_error(403, "bad origin")
            return

        fs_path = self.translate_path(self.path)          # url -> filesystem, '..' collapsed
        root = os.path.realpath(self.directory)
        target = os.path.realpath(fs_path)
        try:
            if os.path.commonpath((target, root)) != root:
                raise ValueError
        except ValueError:
            self.send_error(403, "outside the served directory")
            return
        rel = os.path.relpath(target, root).replace(os.sep, "/")
        if not rel.endswith(".json") or not any(
            rel == r or rel.startswith(r + "/") for r in WRITABLE_ROOTS
        ):
            self.send_error(403, "only .json files under %s" % ", ".join(WRITABLE_ROOTS))
            return
        if not os.path.isfile(target):
            self.send_error(404, "not an existing file")
            return

        try:
            body = self.rfile.read(int(self.headers.get("Content-Length", 0)))
            with open(target, "wb") as f:
                f.write(body)
        except OSError as exc:
            self.send_error(500, str(exc))
            return

        self.log_message('wrote %s (%d bytes)', rel, len(body))
        self.send_response(204)
        self.end_headers()


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8000
    ALLOWED_ORIGINS = {
        "http://127.0.0.1:%d" % port,
        "http://localhost:%d" % port,
    }
    handler = functools.partial(EditorHandler, directory=".")
    # explicit IPv4 bind - http.server.test()'s own default differs from
    # `python -m http.server`'s (which dual-stack-binds "::" so 127.0.0.1
    # still resolves); without this, 127.0.0.1 connections can be refused.
    http.server.test(HandlerClass=handler, port=port, bind="127.0.0.1")
