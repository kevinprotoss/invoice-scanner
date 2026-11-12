import base64
import hashlib
import hmac
import time

from fastapi import HTTPException, Request, Response

from .config import settings

COOKIE_NAME = "invoice_session"


def _b64e(b: bytes) -> str:
    return base64.urlsafe_b64encode(b).decode().rstrip("=")


def _b64d(s: str) -> bytes:
    pad = "=" * (-len(s) % 4)
    return base64.urlsafe_b64decode(s + pad)


def verify_password(password: str) -> bool:
    stored = settings.password_hash
    if not stored or not stored.startswith("pbkdf2_sha256$"):
        return False
    try:
        _, iters_s, salt_s, hash_s = stored.split("$")
        iters = int(iters_s)
        salt = _b64d(salt_s)
        expected = _b64d(hash_s)
    except Exception:
        return False
    actual = hashlib.pbkdf2_hmac("sha256", password.encode(), salt, iters)
    return hmac.compare_digest(actual, expected)


def _sign(payload: str) -> str:
    sig = hmac.new(settings.secret_key.encode(), payload.encode(), hashlib.sha256).digest()
    return _b64e(sig)


def issue_session(response: Response) -> None:
    exp = int(time.time()) + settings.session_ttl_seconds
    payload = f"ok.{exp}"
    value = f"{payload}.{_sign(payload)}"
    response.set_cookie(
        COOKIE_NAME,
        value,
        max_age=settings.session_ttl_seconds,
        httponly=True,
        secure=settings.cookie_secure,
        samesite="lax",
        path="/",
    )


def clear_session(response: Response) -> None:
    response.delete_cookie(COOKIE_NAME, path="/")


def is_authenticated(request: Request) -> bool:
    raw = request.cookies.get(COOKIE_NAME)
    if not raw:
        return False
    parts = raw.split(".")
    if len(parts) != 3:
        return False
    status, exp_s, sig = parts
    payload = f"{status}.{exp_s}"
    if not hmac.compare_digest(sig, _sign(payload)):
        return False
    try:
        exp = int(exp_s)
    except ValueError:
        return False
    if status != "ok" or exp < int(time.time()):
        return False
    return True


def require_auth(request: Request) -> None:
    if not is_authenticated(request):
        raise HTTPException(status_code=401, detail="Unauthorized")