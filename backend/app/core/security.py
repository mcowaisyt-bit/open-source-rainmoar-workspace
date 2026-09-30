from passlib.context import CryptContext
from jose import jwt, JWTError
from datetime import datetime, timedelta, timezone
from typing import Optional
from cryptography.fernet import Fernet
from hashlib import sha256
import base64
import secrets
from app.core.config import get_settings

settings = get_settings()

pwd_context = CryptContext(schemes=["argon2"], deprecated="auto")


def hash_password(password: str) -> str:
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (
        expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    )
    # jti ensures uniqueness even when issued in the same second
    to_encode.update({
        "exp": expire,
        "jti": secrets.token_urlsafe(16),
        "iat": datetime.now(timezone.utc),
    })
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.JWT_ALGORITHM)


def decode_access_token(token: str) -> Optional[dict]:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.JWT_ALGORITHM])
        return payload
    except JWTError:
        return None


def hash_token(token: str) -> str:
    return sha256(token.encode()).hexdigest()


def generate_session_token() -> str:
    return secrets.token_urlsafe(48)


def _get_fernet() -> Fernet:
    key_material = settings.CREDENTIAL_ENCRYPTION_KEY.encode()
    key = base64.urlsafe_b64encode(sha256(key_material).digest())
    return Fernet(key)


def encrypt_credential(value: str) -> str:
    f = _get_fernet()
    return f.encrypt(value.encode()).decode()


def decrypt_credential(encrypted: str) -> str:
    f = _get_fernet()
    return f.decrypt(encrypted.encode()).decode()
