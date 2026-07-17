"""
JWT + password hashing utilities.
"""
import uuid
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from ..config import get_settings

settings = get_settings()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain: str, hashed: str) -> bool:
    return pwd_context.verify(plain, hashed)


def create_access_token(
    data: Dict[str, Any],
    expires_delta: Optional[timedelta] = None
) -> str:
    payload = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(days=settings.JWT_EXPIRE_DAYS)
    )
    payload.update({"exp": expire, "iat": datetime.now(timezone.utc)})
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def create_download_token(user_id: str, product_id: str) -> str:
    """Signed URL token for file download. Time-bound (JWT_DOWNLOAD_EXPIRE_MINUTES),
    not single-use — a stalled download's automatic browser retry hitting
    the same URL a second time must not get permanently locked out (see the
    single-use gate removal in routes/library.py's download_file), but the
    link still shouldn't stay valid forever once issued."""
    expire = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_DOWNLOAD_EXPIRE_MINUTES)
    payload = {
        "sub": user_id,
        "product_id": product_id,
        "type": "download",
        "jti": uuid.uuid4().hex,
        "exp": expire,
        "iat": datetime.now(timezone.utc),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    return jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])


def verify_token(token: str) -> Optional[Dict[str, Any]]:
    try:
        return decode_token(token)
    except JWTError:
        return None
