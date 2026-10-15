from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel
import time
from typing import Dict, Tuple
from services.auth_service import AuthService, get_current_user

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Rate limit xotirasi: {key: (failed_attempts_count, last_attempt_timestamp)}
_login_attempts: Dict[str, Tuple[int, float]] = {}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_SECONDS = 300  # 5 daqiqa

def _cleanup_login_attempts(current_time: float):
    if len(_login_attempts) > 300:
        keys_to_remove = [k for k, (_, t) in _login_attempts.items() if current_time - t > LOCKOUT_SECONDS * 2]
        for k in keys_to_remove:
            _login_attempts.pop(k, None)

class LoginRequest(BaseModel):
    identifier: str  # username yoki student_code
    secret: str      # parol yoki PIN

@router.post("/login")
def login(data: LoginRequest, request: Request):
    client_ip = request.client.host if request.client else "unknown"
    clean_id = data.identifier.strip().lower()
    rate_key = f"{client_ip}:{clean_id}"
    now = time.time()

    _cleanup_login_attempts(now)

    # Bloklanganlikni tekshirish
    if rate_key in _login_attempts:
        attempts, last_time = _login_attempts[rate_key]
        if attempts >= MAX_FAILED_ATTEMPTS:
            elapsed = now - last_time
            if elapsed < LOCKOUT_SECONDS:
                remaining = int(LOCKOUT_SECONDS - elapsed)
                raise HTTPException(
                    status_code=429,
                    detail=f"Xavfsizlik: Ko'p marta xato login kiritildi. Iltimos, {remaining} soniyadan keyin qayta urining."
                )
            else:
                del _login_attempts[rate_key]


    if not data.identifier.strip() or not data.secret.strip():
        raise HTTPException(status_code=400, detail="Login va parol kiritilishi shart")
    
    user = AuthService.authenticate_user(data.identifier, data.secret)
    if not user:
        # Muvaffaqiyatsiz urinishni qayd etish
        prev_attempts = _login_attempts.get(rate_key, (0, 0))[0]
        _login_attempts[rate_key] = (prev_attempts + 1, now)
        raise HTTPException(status_code=401, detail="Login, PIN yoki parol noto'g'ri, yoki hisob faol emas")

    # Muvaffaqiyatli kirishda hisoblagichni tozalash
    if rate_key in _login_attempts:
        del _login_attempts[rate_key]

    return {
        "success": True,
        "token": user["token"],
        "user": {
            "id": user["id"],
            "username": user["username"],
            "role": user["role"],
            "full_name": user["full_name"],
            "teacher_id": user.get("teacher_id"),
            "student_id": user.get("student_id"),
            "group_id": user.get("group_id"),
            "group_name": user.get("group_name"),
            "student_code": user.get("student_code")
        }
    }

@router.get("/me")
def get_me(user: dict = Depends(get_current_user)):
    return {"user": user}
