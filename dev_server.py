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


_PAYSTACK_DEV_STORE = {
    "balance": 184500.0,
    "local_sales": [
        {
            "reference": "ACP-DB-1001",
            "name": "Ibrahim Danjuma",
            "email": "ibrahim.d@example.com",
            "amount": 5000.0,
            "payment_method": "card",
            "gateway": "Paystack",
            "status": "success",
            "email_sent": True,
            "created_at": "2026-10-15T10:14:00Z",
            "verified_at": "2026-10-15T10:15:22Z"
        },
        {
            "reference": "ACP-DB-1002",
            "name": "Amaka Nnamdi",
            "email": "amaka.n@example.com",
            "amount": 5000.0,
            "payment_method": "bank_transfer",
            "gateway": "Paystack",
            "status": "success",
            "email_sent": True,
            "created_at": "2026-10-15T11:20:00Z",
            "verified_at": "2026-10-15T11:21:40Z"
        },
        {
            "reference": "ACP-DB-1003",
            "name": "Kelechi Eze",
            "email": "kelechi.eze@example.com",
            "amount": 5000.0,
            "payment_method": "card",
            "gateway": "Paystack",
            "status": "success",
            "email_sent": False,
            "created_at": "2026-10-15T14:02:00Z",
            "verified_at": "2026-10-15T14:03:10Z"
        }
    ],
    "paystack_txs": [
        {
            "id": 8923011,
            "reference": "ACP-DB-1001",
            "status": "success",
            "amount": 5000.0,
            "currency": "NGN",
            "channel": "card",
            "paid_at": "2026-10-15T10:15:22Z",
            "customer_email": "ibrahim.d@example.com",
            "customer_name": "Ibrahim Danjuma",
            "sync_status": "synced"
        },
        {
            "id": 8923012,
            "reference": "ACP-DB-1002",
            "status": "success",
            "amount": 5000.0,
            "currency": "NGN",
            "channel": "bank_transfer",
            "paid_at": "2026-10-15T11:21:40Z",
            "customer_email": "amaka.n@example.com",
            "customer_name": "Amaka Nnamdi",
            "sync_status": "synced"
        },
        {
            "id": 8923015,
            "reference": "ACP-PAYSTACK-UNSYNCED-1",
            "status": "success",
            "amount": 5000.0,
            "currency": "NGN",
            "channel": "bank_transfer",
            "paid_at": "2026-10-15T13:45:10Z",
            "customer_email": "tunde.babalola@example.com",
            "customer_name": "Tunde Babalola",
            "sync_status": "not_in_db"
        },
        {
            "id": 8923018,
            "reference": "ACP-FLAGGED-001",
            "status": "success",
            "amount": 4920.0,
            "currency": "NGN",
            "channel": "card",
            "paid_at": "2026-10-15T14:10:00Z",
            "customer_email": "chidinma.okafor@example.com",
            "customer_name": "Chidinma Okafor",
            "sync_status": "flagged",
            "flagged_reason": "fee_pass_through_discrepancy"
        }
    ],
    "flagged_payments": [
        {
            "reference": "ACP-FLAGGED-001",
            "customer_name": "Chidinma Okafor",
            "customer_email": "chidinma.okafor@example.com",
            "amount_paid": 4920.0,
            "expected_amount": 5000.0,
            "reason": "fee_pass_through_discrepancy",
            "flagged_at": "2026-10-15T14:10:05Z",
            "resolved": False
        }
    ]
}


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

        # API: Admin Master Overview
        if clean_path.startswith("/api/admin/master-overview"):
            return self._send_json({
                "revenue_today": "₦42,000",
                "sales_today": 21,
                "active_affiliates": 18,
                "total_customers": 4200,
                "mrr": "₦180,000",
                "open_reviews_count": 0,
                "failed_delivery_alerts_count": 0,
                "articles_count": 201
            })

        # API: Admin Analytics Overview
        if clean_path.startswith("/api/admin/analytics/overview"):
            return self._send_json({
                "period": "all",
                "total_revenue": 8400000,
                "total_orders": 4200,
                "avg_order_value": 2000,
                "conversion_rate": 3.8,
                "sales_count": 4200,
                "recent_sales": []
            })

        # API: Admin Blog Categories
        if clean_path == "/api/admin/blog/categories":
            try:
                from backend.services.blog_service import get_categories
                return self._send_json({"categories": get_categories()})
            except Exception:
                return self._send_json({"categories": []})

        # API: Admin Blog Articles
        if clean_path == "/api/admin/blog/articles":
            try:
                from backend.services.blog_service import get_all_articles
                articles = get_all_articles(include_drafts=True)
                summary = []
                for a in articles:
                    summary.append({
                        "slug": a["slug"],
                        "title": a["title"],
                        "category": a["category"],
                        "category_name": a["category_name"],
                        "status": a.get("status", "published"),
                        "author": a.get("author", "Itoya David"),
                        "date_published": a.get("date_published", "2026-10-08"),
                        "read_time": a.get("read_time", "6 min read"),
                        "url": f"/blog/{a['category']}/{a['slug']}"
                    })
                return self._send_json({"articles": summary, "total": len(summary)})
            except Exception as e:
                return self._send_json({"articles": [], "total": 0})

        # API: Admin Paystack Status
        if clean_path == "/api/admin/paystack/status":
            unresolved = len([f for f in _PAYSTACK_DEV_STORE["flagged_payments"] if not f.get("resolved")])
            return self._send_json({
                "connected": True,
                "configured": True,
                "mode": "live",
                "balance": {"currency": "NGN", "available_balance": _PAYSTACK_DEV_STORE["balance"]},
                "error": None,
                "webhook": {
                    "expected_url": "https://academic-pack.onrender.com/api/payments/webhook",
                    "total_received": 142,
                    "last_received_at": datetime.now(timezone.utc).isoformat(),
                    "last_ip": "52.31.139.248"
                },
                "unresolved_flagged_count": unresolved,
                "total_local_sales": len(_PAYSTACK_DEV_STORE["local_sales"])
            })

        # API: Admin Paystack Live Transactions Feed
        if clean_path.startswith("/api/admin/paystack/transactions"):
            return self._send_json({
                "transactions": _PAYSTACK_DEV_STORE["paystack_txs"],
                "meta": {"total": len(_PAYSTACK_DEV_STORE["paystack_txs"])},
                "total": len(_PAYSTACK_DEV_STORE["paystack_txs"])
            })

        # API: Admin Flagged Payments
        if clean_path.startswith("/api/admin/flagged-payments"):
            unresolved = [f for f in _PAYSTACK_DEV_STORE["flagged_payments"] if not f.get("resolved")]
            return self._send_json({
                "flagged_payments": unresolved,
                "count": len(unresolved)
            })

        # API: Admin Analytics Sales
        if clean_path.startswith("/api/admin/analytics/sales"):
            return self._send_json({
                "transactions": _PAYSTACK_DEV_STORE["local_sales"],
                "total": len(_PAYSTACK_DEV_STORE["local_sales"])
            })

        # API: Admin Sale Details
        if clean_path.startswith("/api/admin/sales/") and clean_path.endswith("/details"):
            ref = clean_path.split("/")[4]
            sale = next((s for s in _PAYSTACK_DEV_STORE["local_sales"] if s["reference"] == ref), None)
            if not sale:
                sale = {
                    "reference": ref,
                    "name": "Customer",
                    "email": "customer@example.com",
                    "amount": 5000.0,
                    "payment_method": "card",
                    "gateway": "Paystack",
                    "status": "success",
                    "verified_at": datetime.now(timezone.utc).isoformat()
                }
            return self._send_json({
                "payment": sale,
                "customer": {"email": sale.get("email"), "name": sale.get("name")},
                "referral": {"affiliate_code": "DIRECT", "commission_amount": 0.0}
            })

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

        # API: Admin Login
        if clean_path == "/api/admin/login":
            return self._send_json({
                "access_token": "dev-admin-jwt-token-access",
                "token_type": "bearer",
                "role": "admin"
            })

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

        # API: Paystack 1-Click Sync
        if clean_path == "/api/admin/paystack/sync":
            newly = []
            for tx in _PAYSTACK_DEV_STORE["paystack_txs"]:
                if tx.get("sync_status") == "not_in_db":
                    tx["sync_status"] = "synced"
                    _PAYSTACK_DEV_STORE["local_sales"].insert(0, {
                        "reference": tx["reference"],
                        "name": tx["customer_name"],
                        "email": tx["customer_email"],
                        "amount": tx["amount"],
                        "payment_method": tx["channel"],
                        "gateway": "Paystack",
                        "status": "success",
                        "email_sent": True,
                        "created_at": datetime.now(timezone.utc).isoformat(),
                        "verified_at": datetime.now(timezone.utc).isoformat()
                    })
                    newly.append(tx)
            return self._send_json({
                "success": True,
                "scanned": len(_PAYSTACK_DEV_STORE["paystack_txs"]),
                "already_synced": len(_PAYSTACK_DEV_STORE["paystack_txs"]) - len(newly),
                "newly_reconciled_count": len(newly),
                "newly_reconciled": newly,
                "message": f"Scanned {len(_PAYSTACK_DEV_STORE['paystack_txs'])} Paystack transactions: {len(newly)} newly reconciled and granted access."
            })

        # API: Paystack Reconcile Single Reference
        if clean_path == "/api/admin/paystack/reconcile-ref":
            ref = (body.get("reference") or "").strip()
            found = None
            for tx in _PAYSTACK_DEV_STORE["paystack_txs"]:
                if tx.get("reference") == ref:
                    tx["sync_status"] = "synced"
                    found = tx
                    break
            
            if not found:
                found = {
                    "id": int(uuid.uuid4().int % 10000000),
                    "reference": ref,
                    "status": "success",
                    "amount": 5000.0,
                    "currency": "NGN",
                    "channel": "bank_transfer",
                    "paid_at": datetime.now(timezone.utc).isoformat(),
                    "customer_email": "reconciled.student@example.com",
                    "customer_name": "Reconciled Student",
                    "sync_status": "synced"
                }
                _PAYSTACK_DEV_STORE["paystack_txs"].insert(0, found)

            if not any(s["reference"] == ref for s in _PAYSTACK_DEV_STORE["local_sales"]):
                _PAYSTACK_DEV_STORE["local_sales"].insert(0, {
                    "reference": ref,
                    "name": found["customer_name"],
                    "email": found["customer_email"],
                    "amount": found["amount"],
                    "payment_method": found["channel"],
                    "gateway": "Paystack",
                    "status": "success",
                    "email_sent": True,
                    "created_at": datetime.now(timezone.utc).isoformat(),
                    "verified_at": datetime.now(timezone.utc).isoformat()
                })

            return self._send_json({
                "success": True,
                "reference": ref,
                "email": found["customer_email"],
                "name": found["customer_name"],
                "amount": found["amount"],
                "message": f"Successfully verified and reconciled {ref} for {found['customer_email']}. Customer access granted."
            })

        # API: Resolve Flagged Payment
        if clean_path == "/api/admin/flagged-payments/resolve":
            ref = (body.get("reference") or "").strip()
            for f in _PAYSTACK_DEV_STORE["flagged_payments"]:
                if f.get("reference") == ref:
                    f["resolved"] = True
                    f["resolved_at"] = datetime.now(timezone.utc).isoformat()
                    f["resolved_by"] = "admin"
                    if not any(s["reference"] == ref for s in _PAYSTACK_DEV_STORE["local_sales"]):
                        _PAYSTACK_DEV_STORE["local_sales"].insert(0, {
                            "reference": ref,
                            "name": f["customer_name"],
                            "email": f["customer_email"],
                            "amount": f["amount_paid"],
                            "payment_method": "card",
                            "gateway": "Paystack",
                            "status": "success",
                            "email_sent": True,
                            "created_at": datetime.now(timezone.utc).isoformat(),
                            "verified_at": datetime.now(timezone.utc).isoformat()
                        })
                    for tx in _PAYSTACK_DEV_STORE["paystack_txs"]:
                        if tx.get("reference") == ref:
                            tx["sync_status"] = "synced"
            return self._send_json({
                "success": True,
                "message": f"Payment {ref} resolved successfully. Customer access granted."
            })

        # API: Resend Welcome Email
        if clean_path.startswith("/api/admin/sales/") and clean_path.endswith("/resend-email"):
            ref = clean_path.split("/")[4]
            for s in _PAYSTACK_DEV_STORE["local_sales"]:
                if s["reference"] == ref:
                    s["email_sent"] = True
            return self._send_json({
                "success": True,
                "message": "Access email re-queued! The customer will receive it within minutes."
            })

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
