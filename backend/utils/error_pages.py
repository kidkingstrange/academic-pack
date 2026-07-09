"""
Friendly HTML dead-end pages for expired/already-used link errors.

A customer who follows a stale link (an already-used download token, an
expired magic link) is a real person on their phone, not an API client —
a bare JSON 403 is a dead end. These return a proper page instead.
"""
from fastapi.responses import HTMLResponse

_TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Link expired — Academic Comeback Package</title>
</head>
<body style="margin:0;background:#0c0e12;color:#fff;font-family:'Manrope',sans-serif;display:flex;min-height:100vh;align-items:center;justify-content:center;text-align:center;padding:24px;box-sizing:border-box">
  <div style="max-width:420px">
    <div style="width:64px;height:64px;background:rgba(201,151,58,.1);color:#c9973a;border-radius:50%;display:flex;align-items:center;justify-content:center;font-size:1.8rem;margin:0 auto 24px;border:1px solid rgba(201,151,58,.2)">↺</div>
    <h1 style="font-size:1.5rem;font-weight:600;margin-bottom:12px">{heading}</h1>
    <p style="color:rgba(255,255,255,.7);line-height:1.7;margin-bottom:28px">{message}</p>
    <a href="{cta_href}" style="display:inline-block;background:linear-gradient(135deg,#c9973a,#e3b55a);color:#0c0e12;font-weight:700;padding:14px 32px;border-radius:999px;text-decoration:none">{cta_text}</a>
  </div>
</body>
</html>"""


def expired_link_page(
    message: str,
    heading: str = "This link has expired",
    cta_text: str = "Back to Library",
    cta_href: str = "/library",
    status_code: int = 403,
) -> HTMLResponse:
    html = _TEMPLATE.format(heading=heading, message=message, cta_text=cta_text, cta_href=cta_href)
    return HTMLResponse(content=html, status_code=status_code)
