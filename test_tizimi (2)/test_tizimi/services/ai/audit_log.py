import json
import logging
from typing import Optional, Dict, Any
from database.db import get_db_connection

logger = logging.getLogger(__name__)

class AIAuditLog:
    @staticmethod
    def log(
        task: str,
        model: str,
        request_data: Any,
        response_data: Any,
        status: str = "success",
        latency: float = 0.0,
        tokens: int = 0,
        error: Optional[str] = None,
        user_id: Optional[int] = None,
        requested_count: int = 0,
        accepted_count: int = 0,
        rejected_count: int = 0
    ):
        """AI so'rovini audit jurnaliga yozish."""
        conn = get_db_connection()
        try:
            req_str = json.dumps(request_data, ensure_ascii=False) if not isinstance(request_data, str) else request_data
            res_str = json.dumps(response_data, ensure_ascii=False) if not isinstance(response_data, str) else response_data

            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO ai_audit_log (
                    user_id, task, model, request_data, response_data,
                    status, latency, tokens, error, requested_count,
                    accepted_count, rejected_count, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
            """, (
                user_id, task, model, req_str, res_str,
                status, round(latency, 3), tokens, error,
                requested_count, accepted_count, rejected_count
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Audit log yozishda xatolik: {e}")
        finally:
            conn.close()

    @staticmethod
    def get_logs(limit: int = 50):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM ai_audit_log ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()
