import logging
from typing import Optional
from database.db import get_db_connection

logger = logging.getLogger(__name__)

class AICache:
    @staticmethod
    def get(cache_key: str) -> Optional[str]:
        """Keshdan natijani olish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT response_data FROM ai_cache WHERE cache_key = ?", (cache_key,))
            row = cursor.fetchone()
            if row:
                return row["response_data"]
            return None
        except Exception as e:
            logger.warning(f"Keshni o'qishda xatolik: {e}")
            return None
        finally:
            conn.close()

    @staticmethod
    def set(cache_key: str, response_data: str):
        """Natijani keshga yozish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO ai_cache (cache_key, response_data, created_at)
                VALUES (?, ?, datetime('now'))
            """, (cache_key, response_data))
            conn.commit()
        except Exception as e:
            logger.warning(f"Keshga yozishda xatolik: {e}")
        finally:
            conn.close()

    @staticmethod
    def clear(cache_key: Optional[str] = None):
        """Keshni tozalash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if cache_key:
                cursor.execute("DELETE FROM ai_cache WHERE cache_key = ?", (cache_key,))
            else:
                cursor.execute("DELETE FROM ai_cache")
            conn.commit()
        finally:
            conn.close()
