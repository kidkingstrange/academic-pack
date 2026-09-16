"""
Simple local development static server with clean URL support.
Serves frontend directory on port 8000.
"""
import http.server
import socketserver
from pathlib import Path

PORT = 8000
FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"

class CleanUrlHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(FRONTEND_DIR), **kwargs)

    def do_GET(self):
        # Strip query params
        path_part = self.path.split('?')[0].strip('/')
        query_part = ('?' + self.path.split('?')[1]) if '?' in self.path else ''
        
        # URL aliases
        if path_part in ("academic-comeback-package", "academic-comeback", "academic%20comeback%20package"):
            self.path = "/academic-comeback-package.html" + query_part
        elif path_part == "library":
            self.path = "/library.html" + query_part
        elif path_part in ("us", "usa"):
            self.path = "/us.html" + query_part
        elif path_part and not path_part.endswith(".html") and not '.' in path_part:
            potential_file = FRONTEND_DIR / f"{path_part}.html"
            if potential_file.exists():
                self.path = f"/{path_part}.html" + query_part
                
        return super().do_GET()

if __name__ == "__main__":
    socketserver.TCPServer.allow_reuse_address = True
    with socketserver.TCPServer(("127.0.0.1", PORT), CleanUrlHandler) as httpd:
        print(f"Dev server running at http://localhost:{PORT}")
        httpd.serve_forever()
