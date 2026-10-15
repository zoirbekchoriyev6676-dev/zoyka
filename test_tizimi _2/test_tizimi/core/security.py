import os
from pathlib import Path
from dotenv import load_dotenv
import bcrypt
import jwt
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any
import secrets

ENV_PATH = Path(__file__).resolve().parent.parent / ".env"
load_dotenv(dotenv_path=ENV_PATH)

_raw_secret = os.getenv("JWT_SECRET", "").strip()
if not _raw_secret:
    _raw_secret = secrets.token_hex(32)
    # Persist generated secret to .env so user sessions persist across restarts
    try:
        lines = []
        if ENV_PATH.exists():
            with open(ENV_PATH, "r", encoding="utf-8") as f:
                lines = f.readlines()
        has_key = False
        for i, line in enumerate(lines):
            if line.startswith("JWT_SECRET="):
                lines[i] = f"JWT_SECRET={_raw_secret}\n"
                has_key = True
                break
        if not has_key:
            lines.append(f"\nJWT_SECRET={_raw_secret}\n")
        with open(ENV_PATH, "w", encoding="utf-8") as f:
            f.writelines(lines)
    except Exception:
        pass
    os.environ["JWT_SECRET"] = _raw_secret

JWT_SECRET = _raw_secret
JWT_ALGORITHM = "HS256"
JWT_EXPIRATION_HOURS = 24

def hash_password(password: str) -> str:
    """Parolni bcrypt yordamida xesh qilish."""
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Parolni tekshirish."""
    try:
        return bcrypt.checkpw(plain_password.encode("utf-8"), hashed_password.encode("utf-8"))
    except Exception:
        return False

def create_token(user_id: int, username: str, role: str, full_name: str) -> str:
    """JWT token yaratish."""
    payload = {
        "sub": str(user_id),
        "username": username,
        "role": role,
        "full_name": full_name,
        "exp": datetime.now(timezone.utc) + timedelta(hours=JWT_EXPIRATION_HOURS)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)

def decode_token(token: str) -> Optional[Dict[str, Any]]:
    """JWT tokenni ochish va tekshirish."""
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
    except jwt.PyJWTError:
        return None
