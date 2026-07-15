from fastapi import Depends, HTTPException, status, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from bson import ObjectId
from datetime import datetime, timezone
import hashlib
from ..utils.security import verify_token
from ..database import get_db

security = HTTPBearer(auto_error=False)


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
            if user_id:
                return {
                    "user_id": user_id,
                    "email": payload.get("email"),
                    "role": payload.get("role", "customer")
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
