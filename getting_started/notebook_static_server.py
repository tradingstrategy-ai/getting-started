#!/usr/bin/env python3
"""Serve saved Jupyter notebook outputs as static HTML."""

import argparse
import base64
import hmac
import html
import ipaddress
import os
import subprocess
import sys
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler
from http.server import ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote
from urllib.parse import unquote
from urllib.parse import urlparse

import nbformat
from nbconvert import HTMLExporter


PROJECT_ROOT = Path.cwd().resolve()
NOTEBOOK_ROOTS = (
    PROJECT_ROOT / "notebooks",
    PROJECT_ROOT / "scratchpad",
)
DEFAULT_HOST = "0.0.0.0"
DEFAULT_PORT = 8765
# Assumption: this server is exposed only on an intranet through Tailscale.
BASIC_AUTH_USER = "viewer"
BASIC_AUTH_PASSWORD = "viewer"
TAILSCALE_IPV4_NETWORK = ipaddress.ip_network("100.64.0.0/10")


class NotebookServerError(Exception):
    """Base class for expected notebook server errors."""

    status = HTTPStatus.BAD_REQUEST


class NotFound(NotebookServerError):
    """Requested notebook was not found."""

    status = HTTPStatus.NOT_FOUND


class Forbidden(NotebookServerError):
    """Requested path is outside the allowed notebook roots."""

    status = HTTPStatus.FORBIDDEN


def is_allowed_remote(value: str) -> bool:
    """Check whether a remote address is allowed to access the server."""

    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    return address.is_loopback or address in TAILSCALE_IPV4_NETWORK


def get_available_roots() -> tuple[Path, ...]:
    """Return notebook roots that exist in this checkout."""

    return tuple(root.resolve() for root in NOTEBOOK_ROOTS if root.exists())


def relative_notebook_path(path: Path) -> str:
    """Return the display path for a notebook under an allowed root."""

    resolved = path.resolve()
    for root in get_available_roots():
        if os.path.commonpath((resolved, root)) == str(root):
            return resolved.relative_to(PROJECT_ROOT).as_posix()
    raise Forbidden(f"Notebook is outside allowed roots: {path}")


def validate_notebook_path(raw_path: str | Path) -> Path:
    """Validate and resolve a notebook path under the allowed roots."""

    raw = Path(str(raw_path))
    if raw.is_absolute():
        raise Forbidden("Absolute notebook paths are not allowed")
    if ".." in raw.parts:
        raise Forbidden("Notebook paths may not contain parent-directory traversal")
    if raw.suffix != ".ipynb":
        raise Forbidden("Only .ipynb files can be rendered")

    target = (PROJECT_ROOT / raw).resolve()
    roots = get_available_roots()
    if not roots:
        raise NotFound("No notebook roots exist in this checkout")
    if not any(os.path.commonpath((target, root)) == str(root) for root in roots):
        raise Forbidden("Notebook path is outside notebooks/ and scratchpad/")
    if not target.exists() or not target.is_file():
        raise NotFound(f"Notebook not found: {raw}")
    return target


def list_notebooks() -> list[str]:
    """List all notebooks under the allowed roots."""

    paths: list[str] = []
    for root in get_available_roots():
        for path in root.rglob("*.ipynb"):
            if ".ipynb_checkpoints" in path.parts:
                continue
            paths.append(relative_notebook_path(path))
    return sorted(paths)


def view_path_for(notebook_path: str | Path) -> str:
    """Return the URL path for a notebook."""

    path = validate_notebook_path(notebook_path)
    return "/view/" + quote(relative_notebook_path(path), safe="/")


def get_public_base_url(port: int, public_base_url: str | None) -> str:
    """Resolve the externally usable base URL."""

    if public_base_url:
        return public_base_url.rstrip("/")

    try:
        completed = subprocess.run(
            ["tailscale", "ip", "-4"],
            check=True,
            capture_output=True,
            text=True,
        )
        ip = completed.stdout.splitlines()[0].strip()
        if ip:
            return f"http://{ip}:{port}"
    except Exception:
        pass

    return f"http://127.0.0.1:{port}"


def notebook_url_for(notebook_path: str | Path, port: int, public_base_url: str | None) -> str:
    """Return the absolute URL for a notebook."""

    return get_public_base_url(port, public_base_url) + view_path_for(notebook_path)


def render_notebook(notebook_path: Path) -> str:
    """Render a notebook to HTML without executing it."""

    notebook = nbformat.read(notebook_path, as_version=4)
    exporter = HTMLExporter()
    body, _resources = exporter.from_notebook_node(notebook)
    return body


def render_index() -> str:
    """Render the notebook index page."""

    links = []
    for notebook in list_notebooks():
        url = "/view/" + quote(notebook, safe="/")
        label = html.escape(notebook)
        links.append(f'<li><a href="{url}">{label}</a></li>')
    body = "\n".join(links)
    return f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8">
  <title>Notebook viewer</title>
  <style>
    body {{ font-family: sans-serif; margin: 2rem; line-height: 1.4; }}
    li {{ margin: 0.2rem 0; }}
  </style>
</head>
<body>
  <h1>Notebook viewer</h1>
  <p>Static saved outputs from notebooks/ and scratchpad/.</p>
  <ul>
    {body}
  </ul>
</body>
</html>
"""


class NotebookRequestHandler(BaseHTTPRequestHandler):
    """HTTP handler for static notebook rendering."""

    server_version = "NotebookStaticServer/0.1"

    def do_HEAD(self) -> None:
        self.handle_request(send_body=False)

    def do_GET(self) -> None:
        self.handle_request(send_body=True)

    def handle_request(self, send_body: bool) -> None:
        if not self.server.allow_non_tailnet and not is_allowed_remote(self.client_address[0]):
            self.send_error(HTTPStatus.FORBIDDEN, "Remote address is not loopback or Tailscale")
            return
        if not self.is_authorised():
            self.request_auth()
            return

        parsed = urlparse(self.path)
        try:
            if parsed.path in ("", "/"):
                self.send_html(render_index(), send_body=send_body)
                return
            if parsed.path.startswith("/view/"):
                relative_path = unquote(parsed.path[len("/view/") :])
                notebook_path = validate_notebook_path(relative_path)
                self.send_html(render_notebook(notebook_path), send_body=send_body)
                return
            self.send_text_error(HTTPStatus.NOT_FOUND, "Route not found", send_body=send_body)
        except NotebookServerError as exc:
            self.send_text_error(exc.status, str(exc), send_body=send_body)
        except Exception as exc:
            self.send_text_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc), send_body=send_body)

    def is_authorised(self) -> bool:
        """Check HTTP Basic Auth credentials."""

        header = self.headers.get("Authorization", "")
        prefix = "Basic "
        if not header.startswith(prefix):
            return False
        try:
            decoded = base64.b64decode(header[len(prefix) :], validate=True).decode("utf-8")
        except Exception:
            return False
        username, separator, password = decoded.partition(":")
        if not separator:
            return False
        return hmac.compare_digest(username, BASIC_AUTH_USER) and hmac.compare_digest(password, BASIC_AUTH_PASSWORD)

    def request_auth(self) -> None:
        """Request HTTP Basic Auth credentials."""

        self.send_response(HTTPStatus.UNAUTHORIZED)
        self.send_header("WWW-Authenticate", 'Basic realm="Notebook viewer"')
        self.end_headers()

    def send_html(self, body: str, send_body: bool) -> None:
        """Send an HTML response."""

        payload = body.encode("utf-8")
        self.send_response(HTTPStatus.OK)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)

    def send_text_error(self, status: HTTPStatus, message: str, send_body: bool) -> None:
        """Send an error without putting request-derived text in headers."""

        clean_message = "".join(char if char >= " " and char != "\x7f" else " " for char in message)
        payload = clean_message.encode("utf-8", errors="replace")
        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        if send_body:
            self.wfile.write(payload)


class NotebookHTTPServer(ThreadingHTTPServer):
    """HTTP server with notebook-specific configuration."""

    allow_non_tailnet: bool


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""

    parser = argparse.ArgumentParser(description="Serve saved Jupyter notebook outputs as static HTML.")
    parser.add_argument("--host", default=DEFAULT_HOST, help="Host to bind to. Defaults to 0.0.0.0.")
    parser.add_argument("--port", default=DEFAULT_PORT, type=int, help="Port to listen on.")
    parser.add_argument("--allow-non-tailnet", action="store_true", help="Allow clients outside loopback and Tailscale.")
    parser.add_argument("--public-base-url", help="Public base URL used by --url-for.")
    parser.add_argument("--url-for", help="Print the viewer URL for a notebook and exit.")
    return parser.parse_args()


def main() -> int:
    """Run the notebook server."""

    args = parse_args()

    if args.url_for:
        try:
            print(notebook_url_for(args.url_for, args.port, args.public_base_url))
            return 0
        except NotebookServerError as exc:
            print(str(exc), file=sys.stderr)
            return 2

    server = NotebookHTTPServer((args.host, args.port), NotebookRequestHandler)
    server.allow_non_tailnet = args.allow_non_tailnet

    print(f"Serving notebook viewer on http://{args.host}:{args.port}/")
    print("Allowed roots:")
    for root in get_available_roots():
        print(f"- {root}")
    print("Username: viewer")
    print("Password: viewer")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        return 130
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
