import hashlib
import hmac
import secrets

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import settings
from .db import get_db
from .models import AuthToken, User

_ITERATIONS = 200_000


def hash_password(password: str) -> str:
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), _ITERATIONS).hex()
    return f"pbkdf2${_ITERATIONS}${salt}${digest}"


def verify_password(password: str, stored: str) -> bool:
    _, iterations, salt, digest = stored.split("$")
    candidate = hashlib.pbkdf2_hmac("sha256", password.encode(), bytes.fromhex(salt), int(iterations)).hex()
    return hmac.compare_digest(candidate, digest)


def _token_hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


def issue_token(db: Session, user: User) -> str:
    token = secrets.token_urlsafe(32)
    db.add(AuthToken(user_id=user.id, token_hash=_token_hash(token)))
    return token


def current_user(authorization: str = Header(default=""), db: Session = Depends(get_db)) -> User:
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta el token")
    row = db.execute(select(AuthToken).where(AuthToken.token_hash == _token_hash(token))).scalar_one_or_none()
    if row is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token no válido")
    return db.get(User, row.user_id)


def require_admin(x_admin_key: str = Header(default="")) -> None:
    if not hmac.compare_digest(x_admin_key, settings.admin_api_key):
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Clave de administración no válida")


def require_webhook_secret(x_webhook_secret: str = Header(default="")) -> None:
    # En producción: verificar la firma HMAC del cuerpo que envía el proveedor PSD2/CLO
    if not hmac.compare_digest(x_webhook_secret, settings.webhook_secret):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Firma del webhook no válida")
