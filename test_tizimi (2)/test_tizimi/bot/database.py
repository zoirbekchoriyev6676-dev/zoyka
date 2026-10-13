import sqlite3
from typing import List, Dict, Any, Optional
from database.db import get_db_connection

class BotDB:
    @staticmethod
    def get_active_groups() -> List[Dict[str, Any]]:
        """Barcha faol guruhlarni olish (is_active = 1)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name as group_name, status, school_id FROM groups WHERE is_active = 1 ORDER BY name ASC")
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_group_by_id(group_id: int) -> Optional[Dict[str, Any]]:
        """Guruh ma'lumotlarini id bo'yicha olish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name as group_name, status, school_id, ai_group_analysis FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            return dict(row) if row else None
        finally:
            conn.close()

    @staticmethod
    def get_group_results(group_id: int) -> List[Dict[str, Any]]:
        """
        Guruh natijalarini olish.
        Avval 'results' jadvalidan qidiradi, agar bo'sh bo'lsa 'exam_sessions' orqali oladi.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT student_name, score
                FROM results
                WHERE group_id = ?
                ORDER BY score DESC
            """, (group_id,))
            rows = [dict(r) for r in cursor.fetchall()]
            if rows:
                return rows

            # Zaxira (agar results jadvali hali to'ldirilmagan bo'lsa)
            cursor.execute("""
                SELECT u.full_name as student_name, MAX(es.score_percent) as score
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                WHERE st.group_id = ? AND es.status = 'completed'
                GROUP BY st.id
                ORDER BY score DESC
            """, (group_id,))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_group_ai_analysis(group_id: int) -> str:
        """Guruhning sun'iy intellekt tahlilini olish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT ai_group_analysis, name as group_name FROM groups WHERE id = ?", (group_id,))
            row = cursor.fetchone()
            if not row:
                return "Guruh topilmadi."

            if row["ai_group_analysis"]:
                return row["ai_group_analysis"]

            # Agar hali ai_group_analysis yozilmagan bo'lsa, mavjud natijalardan shakllantirish
            cursor.execute("""
                SELECT ROUND(AVG(es.score_percent), 1) as avg_score, COUNT(es.id) as cnt
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                WHERE st.group_id = ? AND es.status = 'completed'
            """, (group_id,))
            stat = cursor.fetchone()
            avg = stat["avg_score"] or 0.0
            cnt = stat["cnt"] or 0

            return (
                f"🤖 *{row['group_name']} Guruh AI Tahlili:*\n\n"
                f"• Ishtirokchilar: {cnt} nafar o'quvchi\n"
                f"• O'rtacha o'zlashtirish: {avg}%\n\n"
                f"📌 *Pedagogik xulosa:* Guruhda o'quvchilar asosiy mavzularni muvaffaqiyatli topshirdilar. "
                f"O'rtacha ko'rsatkich {avg}% ni tashkil etadi.\n"
                f"💡 *Tavsiya:* Amaliy topshiriqlar va nostandart test savollari ustida ko'proq ishlash tavsiya etiladi."
            )
        finally:
            conn.close()

    @staticmethod
    def get_school_ai_analysis(group_id: int) -> str:
        """Guruh tegishli bo'lgan maktabning umumiy AI tahlilini olish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.name as school_name, s.ai_school_analysis
                FROM schools s
                JOIN groups g ON g.school_id = s.id
                WHERE g.id = ?
            """, (group_id,))
            row = cursor.fetchone()
            if not row:
                # Standart 1-maktabni tekshirish
                cursor.execute("SELECT name as school_name, ai_school_analysis FROM schools LIMIT 1")
                row = cursor.fetchone()

            if row and row["ai_school_analysis"]:
                return f"🏫 *{row['school_name']} AI Tahlili:*\n\n{row['ai_school_analysis']}"

            return "Maktab bo'yicha umumiy AI tahlili hali kiritilmagan."
        finally:
            conn.close()

    @staticmethod
    def publish_group(group_id: int) -> bool:
        """
        Admin buyrug'i: guruh statusini 'published' qilish va
        natijalarni 'results' jadvaliga sinxronlash.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name FROM groups WHERE id = ?", (group_id,))
            g = cursor.fetchone()
            if not g:
                return False

            # Guruh statusini published qilish
            cursor.execute("UPDATE groups SET status = 'published' WHERE id = ?", (group_id,))

            # test_groups_access ni ham completed & is_results_announced=1 qilish
            cursor.execute("""
                UPDATE test_groups_access
                SET status = 'completed', is_results_announced = 1, end_time = datetime('now')
                WHERE group_id = ?
            """, (group_id,))

            # results jadvalini sinxronlash
            cursor.execute("DELETE FROM results WHERE group_id = ?", (group_id,))
            cursor.execute("""
                INSERT INTO results (group_id, student_name, score)
                SELECT st.group_id, u.full_name, MAX(es.score_percent)
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                WHERE st.group_id = ? AND es.status = 'completed'
                GROUP BY st.id
            """, (group_id,))

            # Agar ai_group_analysis bo'sh bo'lsa, generatsiya qilish
            cursor.execute("SELECT ai_group_analysis FROM groups WHERE id = ?", (group_id,))
            cur_ai = cursor.fetchone()
            if not cur_ai or not cur_ai["ai_group_analysis"]:
                cursor.execute("""
                    SELECT ROUND(AVG(es.score_percent), 1) as avg_score, COUNT(es.id) as cnt
                    FROM exam_sessions es
                    JOIN students st ON st.id = es.student_id
                    WHERE st.group_id = ? AND es.status = 'completed'
                """, (group_id,))
                stat = cursor.fetchone()
                avg = stat["avg_score"] or 0.0
                cnt = stat["cnt"] or 0
                ai_text = (
                    f"Guruh: {g['name']}. Ishtirokchilar soni: {cnt} nafar. O'rtacha o'zlashtirish: {avg}%. "
                    f"Natijalar muvaffaqiyatli e'lon qilindi. O'quvchilar mustaqil fikrlash va test yechish ko'nikmalarini namoyon etishdi."
                )
                cursor.execute("UPDATE groups SET ai_group_analysis = ? WHERE id = ?", (ai_text, group_id))

            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def is_admin(telegram_user_id: int) -> bool:
        """Foydalanuvchining admin ekanligini tekshirish."""
        import os
        admin_ids_str = os.getenv("ADMIN_TELEGRAM_IDS", "")
        if admin_ids_str:
            admin_ids = [int(i.strip()) for i in admin_ids_str.split(",") if i.strip().isdigit()]
            if telegram_user_id in admin_ids:
                return True

        admin_id_single = os.getenv("ADMIN_ID", "")
        if admin_id_single and admin_id_single.strip().isdigit():
            if telegram_user_id == int(admin_id_single.strip()):
                return True

        # Baza orqali tekshirish
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("PRAGMA table_info(users)")
            cols = [c["name"] for c in cursor.fetchall()]
            if "telegram_id" in cols:
                cursor.execute("SELECT 1 FROM users WHERE telegram_id = ? AND role = 'admin'", (telegram_user_id,))
                if cursor.fetchone():
                    return True
            return False
        finally:
            conn.close()
