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
import json
import uuid
from datetime import datetime, timezone

PORT = 8080
DIRECTORY = Path(__file__).resolve().parent / "frontend"
DATA_FILE = Path(__file__).resolve().parent / "backend" / "data" / "blog_community.json"


def _read_data():
    if not DATA_FILE.exists():
        return {"comments": [], "topics": []}
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {"comments": [], "topics": []}


def _write_data(data):
    try:
        DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print(f"Error saving data: {e}")


class CleanUrlHandler(http.server.SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(DIRECTORY), **kwargs)

    def _send_json(self, data, status=200):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Headers", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, POST, OPTIONS")
        self.end_headers()

    def do_GET(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path
        query = urllib.parse.parse_qs(parsed.query)

        # API: Get Comments
        if clean_path == "/api/blog/comments":
            data = _read_data()
            comments = data.get("comments", [])
            slug = query.get("slug", [""])[0]
            if slug:
                matched = [c for c in comments if c.get("slug") == slug]
                res = matched if matched else [c for c in comments if c.get("approved", True)]
            else:
                res = [c for c in comments if c.get("approved", True)]
            return self._send_json({"success": True, "comments": res, "total": len(res)})

        # API: Get Topics
        if clean_path == "/api/blog/topics":
            data = _read_data()
            topics = data.get("topics", [])
            cat = query.get("category", ["All"])[0]
            if cat and cat != "All":
                topics = [t for t in topics if t.get("category") == cat]
            topics.sort(key=lambda x: x.get("votes", 0), reverse=True)
            return self._send_json({"success": True, "topics": topics, "total": len(topics)})

        # API: Check Auth
        if clean_path == "/api/blog/auth/me":
            return self._send_json({"success": True, "user": None})

        # Static clean URL routing
        super().do_GET()

    def do_POST(self):
        parsed = urllib.parse.urlparse(self.path)
        clean_path = parsed.path
        length = int(self.headers.get("Content-Length", 0))
        raw_body = self.rfile.read(length).decode("utf-8") if length > 0 else "{}"
        try:
            body = json.loads(raw_body)
        except Exception:
            body = {}

        # API: Reader Login
        if clean_path == "/api/blog/auth/login":
            email = (body.get("email") or "").strip().lower()
            name = (body.get("name") or "").strip() or email.split("@")[0].title()
            if not email or "@" not in email:
                return self._send_json({"detail": "Valid email is required"}, 400)
            return self._send_json({
                "success": True,
                "token": f"dev-reader-token-{email}",
                "user": {"email": email, "name": name}
            })

        # API: Post Comment
        if clean_path == "/api/blog/comments":
            email = (body.get("email") or "").strip().lower()
            name = (body.get("name") or "").strip() or email.split("@")[0].title()
            what_liked = (body.get("what_liked") or "").strip()
            content = (body.get("content") or "").strip()
            slug = (body.get("slug") or "").strip()
            title = (body.get("article_title") or "Study Guide").strip()

            if not email or not content:
                return self._send_json({"detail": "Email and comment content are required"}, 400)

            new_c = {
                "id": f"c-{uuid.uuid4().hex[:8]}",
                "slug": slug,
                "article_title": title,
                "author_name": name,
                "author_email": email,
                "what_liked": what_liked or "Actionable Strategy",
                "content": content,
                "created_at": datetime.now(timezone.utc).isoformat(),
                "approved": True
            }
            data = _read_data()
            data.setdefault("comments", []).insert(0, new_c)
            _write_data(data)
            return self._send_json({"success": True, "comment": new_c})

        # API: Submit Topic
        if clean_path == "/api/blog/topics":
            email = (body.get("email") or "").strip().lower()
            name = (body.get("name") or "").strip() or email.split("@")[0].title()
            title = (body.get("title") or "").strip()
            category = (body.get("category") or "Academics").strip()
            why = (body.get("why_needed") or "").strip()

            if not email or not title:
                return self._send_json({"detail": "Email and topic title are required"}, 400)

            new_t = {
                "id": f"t-{uuid.uuid4().hex[:8]}",
                "title": title,
                "category": category,
                "why_needed": why,
                "author_name": name,
                "author_email": email,
                "votes": 1,
                "voters": [email],
                "status": "Community Request",
                "created_at": datetime.now(timezone.utc).isoformat()
            }
            data = _read_data()
            data.setdefault("topics", []).insert(0, new_t)
            _write_data(data)
            return self._send_json({"success": True, "topic": new_t})

        # API: Upvote Topic
        if clean_path.startswith("/api/blog/topics/") and clean_path.endswith("/vote"):
            topic_id = clean_path.split("/")[4]
            data = _read_data()
            voter = (body.get("email") or "guest").strip().lower()
            votes = 1
            for t in data.get("topics", []):
                if t.get("id") == topic_id:
                    voters = t.setdefault("voters", [])
                    if voter not in voters or voter == "guest":
                        t["votes"] = t.get("votes", 0) + 1
                        if voter != "guest":
                            voters.append(voter)
                    votes = t["votes"]
                    break
            _write_data(data)
            return self._send_json({"success": True, "votes": votes})

        return self._send_json({"detail": "Not found"}, 404)

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
        if clean_path in ("/affiliate/register", "/affiliate/register/"):
            p = DIRECTORY / "affiliate-register.html"
            if p.is_file():
                return str(p)
        if clean_path in ("/affiliate/login", "/affiliate/login/"):
            p = DIRECTORY / "affiliate-login.html"
            if p.is_file():
                return str(p)
        if clean_path in ("/affiliate/activate", "/affiliate/activate/"):
            p = DIRECTORY / "affiliate-activate.html"
            if p.is_file():
                return str(p)
        if clean_path in ("/affiliate/dashboard", "/affiliate/dashboard/"):
            p = DIRECTORY / "affiliate-dashboard.html"
            if p.is_file():
                return str(p)
        if clean_path in ("/admin/blog", "/admin/blog/"):
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
