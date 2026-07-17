from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from datetime import datetime, timezone
import hashlib
from ..utils.security import verify_token
from ..database import get_db

security = HTTPBearer(auto_error=False)


async def _account_still_active(db, user_id: str, role: str) -> bool:
    """A signed JWT is trusted at face value for up to JWT_EXPIRE_DAYS —
    this closes the gap where a deleted or demoted account could keep
    acting on a still-valid token until it naturally expired. Different
    roles live in different collections, so each is checked where it
    actually lives; the env-configured super-admin login (sub == "admin",
    no DB record by design) is controlled by rotating ADMIN_PASSWORD, not
    a deletable row, so it's always considered active here.
    """
    if role == "admin" and user_id == "admin":
        return True
    try:
        oid = ObjectId(user_id)
    except Exception:
        return False
    if role == "admin":
        admin = await db.admin_accounts.find_one({"_id": oid})
        return admin is not None
    if role == "sales_rep":
        rep = await db.sales_reps.find_one({"_id": oid, "active": True})
        return rep is not None
    user = await db.users.find_one({"_id": oid, "is_active": True})
    return user is not None


async def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db=Depends(get_db),
):
    # 1. Try Bearer token
    if credentials:
        token = credentials.credentials
        payload = verify_token(token)
        if payload:
            user_id = payload.get("sub")
            role = payload.get("role", "customer")
            if user_id and db is not None and await _account_still_active(db, user_id, role):
                return {
                    "user_id": user_id,
                    "email": payload.get("email"),
                    "role": role,
                }

    # 2. Try Cookie session fallback
    session_cookie = request.cookies.get("ac_session")
    if session_cookie and db is not None:
        h = hashlib.sha256(session_cookie.encode()).hexdigest()
        session_doc = await db.sessions.find_one({
            "session_hash": h,
            "expires_at": {"$gt": datetime.now(timezone.utc)}
        })
        if session_doc:
            user_id = str(session_doc["user_id"])
            user = await db.users.find_one({"_id": ObjectId(user_id)})
            if user:
                return {
                    "user_id": user_id,
                    "email": user["email"],
                    "role": user.get("role", "customer")
                }

    # 3. Both failed
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid or expired session. Please log in.",
        headers={"WWW-Authenticate": "Bearer"},
    )


async def require_admin(current_user=Depends(get_current_user)):
    if current_user.get("role") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")
    return current_user


async def require_sales_rep(current_user=Depends(get_current_user)):
    if current_user.get("role") not in ["sales_rep", "admin"]:
        raise HTTPException(status_code=403, detail="Sales Representative access required")
    return current_user
