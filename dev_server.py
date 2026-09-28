"""
Local Development Static Server with Clean URL Routing
Matches production SPA/Clean URL routing behavior for:
- /academic-comeback-package -> /academic-comeback-package.html
- /affiliate/register -> /affiliate-register.html
- /affiliate/dashboard -> /affiliate-dashboard.html
- /admin/blog -> /admin/blog.html
- /blog/{category}/{slug} -> /blog/{category}/{slug}/index.html
"""
import http.server
import socketserver
from pathlib import Path
import urllib.parse

PORT = 8080
DIRECTORY = Path(__file__).resolve().parent / "frontend"


class CleanUrlHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def translate_path(self, path):
        parsed = urllib.parse.urlparse(path)
        clean_path = urllib.parse.unquote(parsed.path)

        translated = super().translate_path(path)
        target = Path(translated)

        if target.exists():
            return translated

        # Check if .html version exists (e.g. /academic-comeback-package -> /academic-comeback-package.html)
        html_target = target.with_suffix(".html")
        if html_target.is_file():
            return str(html_target)

        # Check special route aliases
        if clean_path == "/affiliate/register":
            p = DIRECTORY / "affiliate-register.html"
            if p.is_file():
                return str(p)
        if clean_path == "/affiliate/dashboard":
            p = DIRECTORY / "affiliate-dashboard.html"
            if p.is_file():
                return str(p)
        if clean_path == "/admin/blog":
            p = DIRECTORY / "admin" / "blog.html"
            if p.is_file():
                return str(p)

        return translated

    def end_headers(self):
        self.send_header("Cache-Control", "no-cache, must-revalidate")
        super().end_headers()


if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("", PORT), CleanUrlHandler) as httpd:
        print(f"Dev server running at http://localhost:{PORT}")
        try:
            httpd.serve_forever()
        except KeyboardInterrupt:
            pass
