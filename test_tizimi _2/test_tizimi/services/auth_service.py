from typing import Optional, Dict, Any
from fastapi import HTTPException, Security, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from database.db import get_db_connection
from core.security import hash_password, verify_password, create_token, decode_token

security_bearer = HTTPBearer(auto_error=False)

class AuthService:
    @staticmethod
    def hash_password(password: str) -> str:
        return hash_password(password)

    @staticmethod
    def verify_password(plain_password: str, hashed_password: str) -> bool:
        return verify_password(plain_password, hashed_password)

    @staticmethod
    def create_token(user_id: int, username: str, role: str, full_name: str) -> str:
        return create_token(user_id, username, role, full_name)

    @staticmethod
    def decode_token(token: str) -> Optional[Dict[str, Any]]:
        return decode_token(token)

    @staticmethod
    def authenticate_user(login_identifier: str, secret: str) -> Optional[Dict[str, Any]]:
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            
            # 1. Username orqali tekshirish
            cursor.execute("""
                SELECT u.id, u.username, u.password_hash, u.role, u.full_name, u.phone, u.is_active,
                       t.id as teacher_id, t.specialty,
                       s.id as student_id, s.group_id, s.student_code, s.pin,
                       g.name as group_name
                FROM users u
                LEFT JOIN teachers t ON t.user_id = u.id
                LEFT JOIN students s ON s.user_id = u.id
                LEFT JOIN groups g ON g.id = s.group_id
                WHERE LOWER(u.username) = LOWER(?)
            """, (login_identifier.strip(),))
            user = cursor.fetchone()

            # 2. Agar topilmasa, o'quvchi kodi (student_code) bo'yicha tekshirish
            if not user:
                cursor.execute("""
                    SELECT u.id, u.username, u.password_hash, u.role, u.full_name, u.phone, u.is_active,
                           s.id as student_id, s.group_id, s.student_code, s.pin,
                           g.name as group_name
                    FROM students s
                    JOIN users u ON u.id = s.user_id
                    LEFT JOIN groups g ON g.id = s.group_id
                    WHERE LOWER(s.student_code) = LOWER(?)
                """, (login_identifier.strip(),))
                user = cursor.fetchone()

            if not user or not user["is_active"]:
                return None

            user_dict = dict(user)

            # Agar student_code + PIN orqali kirayotgan bo'lsa
            if user_dict.get("pin") and (secret.strip() == user_dict["pin"]):
                token = create_token(user_dict["id"], user_dict["username"], user_dict["role"], user_dict["full_name"])
                user_dict["token"] = token
                del user_dict["password_hash"]
                return user_dict

            # Oddiy parol orqali tekshirish
            if verify_password(secret, user_dict["password_hash"]):
                token = create_token(user_dict["id"], user_dict["username"], user_dict["role"], user_dict["full_name"])
                user_dict["token"] = token
                del user_dict["password_hash"]
                return user_dict

            return None
        finally:
            conn.close()

# FastAPI Dependencies
def get_current_user(credentials: Optional[HTTPAuthorizationCredentials] = Security(security_bearer)):
    if not credentials:
        raise HTTPException(status_code=401, detail="Tizimga kirish talab etiladi (Token mavjud emas)")
    token = credentials.credentials
    payload = decode_token(token)
    if not payload:
        raise HTTPException(status_code=401, detail="Token yaroqsiz yoki muddati o'tgan")
    
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT u.id, u.username, u.role, u.full_name, u.is_active,
                   t.id as teacher_id,
                   s.id as student_id, s.group_id, s.student_code,
                   g.name as group_name
            FROM users u
            LEFT JOIN teachers t ON t.user_id = u.id
            LEFT JOIN students s ON s.user_id = u.id
            LEFT JOIN groups g ON g.id = s.group_id
            WHERE u.id = ?
        """, (int(payload["sub"]),))
        row = cursor.fetchone()
        if not row or not row["is_active"]:
            raise HTTPException(status_code=401, detail="Foydalanuvchi hisobi faol emas")
        return dict(row)
    finally:
        conn.close()

def require_admin(user: dict = Depends(get_current_user)):
    if user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Faqat Admin uchun ruxsat berilgan")
    return user

def require_teacher(user: dict = Depends(get_current_user)):
    if user["role"] not in ("admin", "teacher"):
        raise HTTPException(status_code=403, detail="Faqat O'qituvchi yoki Admin uchun ruxsat berilgan")
    return user

def require_student(user: dict = Depends(get_current_user)):
    if user["role"] != "student":
        raise HTTPException(status_code=403, detail="Faqat O'quvchilar uchun ruxsat berilgan")
    return user
