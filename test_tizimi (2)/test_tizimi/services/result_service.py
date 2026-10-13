from typing import Optional, Dict, Any, List
from database.db import get_db_connection

class ResultService:
    """
    ResultService — Enterprise Natijalar Servisi.
    exam_sessions, student_answers, session_topic_stats va question_bank jadvallari bilan ishlaydi.
    """

    @staticmethod
    def submit_test(
        first_name: str,
        last_name: str,
        group_id: int,
        test_id: int,
        answers: dict,
        tab_switch_count: int = 0,
        time_spent_seconds: int = 0
    ) -> Dict[str, Any]:
        """
        Nom va guruh bo'yicha test topshirish (Legacy muvofiqlik bilan yangi arxitekturaga bog'lash).
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            full_search = f"{first_name.strip()} {last_name.strip()}".lower()

            # O'quvchini qidirish
            cursor.execute("""
                SELECT s.id as student_id
                FROM students s
                JOIN users u ON u.id = s.user_id
                WHERE s.group_id = ? AND LOWER(u.full_name) = ?
            """, (group_id, full_search))
            st_row = cursor.fetchone()

            if not st_row:
                # Agar to'liq mos kelmasa, faqat guruh va ism qismi bo'yicha
                cursor.execute("""
                    SELECT s.id as student_id
                    FROM students s
                    JOIN users u ON u.id = s.user_id
                    WHERE s.group_id = ? AND LOWER(u.full_name) LIKE ?
                    LIMIT 1
                """, (group_id, f"%{first_name.strip().lower()}%"))
                st_row = cursor.fetchone()

            if not st_row:
                # Guruhdagi birinchi o'quvchi zaxira sifatida
                cursor.execute("SELECT id as student_id FROM students WHERE group_id = ? LIMIT 1", (group_id,))
                st_row = cursor.fetchone()

            if not st_row:
                raise ValueError("Ko'rsatilgan guruhda o'quvchi topilmadi.")

            student_id = st_row["student_id"]
        finally:
            conn.close()

        from services.student_service import StudentService
        res = StudentService.submit_exam(
            student_id=student_id,
            test_id=test_id,
            answers=answers,
            tab_switch_count=tab_switch_count,
            time_spent_seconds=time_spent_seconds
        )
        return {
            "attempt_id": res.get("session_id"),
            "session_id": res.get("session_id"),
            "student_id": student_id,
            "score_percent": res.get("score_percent", 0.0),
            "total_questions": res.get("total_questions", 0),
            "correct_answers": res.get("correct_answers", 0),
            "incorrect_answers": res.get("incorrect_answers", 0),
            "message": res.get("message", "Test muvaffaqiyatli yakunlandi")
        }

    @staticmethod
    def get_result_detail(session_id: int) -> Optional[Dict[str, Any]]:
        """Imtihon natijasi tafsilotlari."""
        from services.student_service import StudentService
        return StudentService.get_session_result(session_id=session_id, is_admin_or_teacher=True)

    @staticmethod
    def save_ai_analysis(session_id: int, ai_analysis: str) -> bool:
        """Sessiyaga AI tahlilini yozish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE exam_sessions SET ai_analysis = ? WHERE id = ?", (ai_analysis, session_id))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def get_all_results(
        group_id: Optional[int] = None,
        test_id: Optional[int] = None,
        search: Optional[str] = None,
        limit: int = 100
    ) -> List[Dict[str, Any]]:
        """Barcha topshirilgan imtihon natijalari ro'yxati."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT es.id, es.id as attempt_id, es.score_percent, es.total_questions,
                       es.correct_answers, es.incorrect_answers, es.tab_switch_count,
                       es.time_spent_seconds, es.finished_at as created_at,
                       u.full_name as student_name, st.student_code,
                       g.name as group_name,
                       t.title as test_title, t.passing_score
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                JOIN tests t ON t.id = es.test_id
                WHERE es.status = 'completed'
            """
            params: List[Any] = []
            if group_id:
                query += " AND g.id = ?"
                params.append(group_id)
            if test_id:
                query += " AND t.id = ?"
                params.append(test_id)
            if search:
                query += " AND (u.full_name LIKE ? OR st.student_code LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])

            query += " ORDER BY es.id DESC LIMIT ?"
            params.append(limit)

            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_dashboard_stats() -> Dict[str, Any]:
        """Boshqaruv paneli uchun umumiy statistikalar."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM students")
            total_students = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM tests")
            total_tests = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM question_bank WHERE is_active = 1")
            total_questions = cursor.fetchone()["count"]

            cursor.execute("""
                SELECT COUNT(*) as count, AVG(score_percent) as avg_score
                FROM exam_sessions
                WHERE status = 'completed'
            """)
            attempt_row = cursor.fetchone()
            total_attempts = attempt_row["count"]
            avg_score = round(attempt_row["avg_score"] or 0, 1)

            # Oxirgi 10 ta urinish
            cursor.execute("""
                SELECT es.id, es.score_percent, es.finished_at as created_at,
                       u.full_name as student_name, g.name as group_name, t.title as test_title
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                JOIN tests t ON t.id = es.test_id
                WHERE es.status = 'completed'
                ORDER BY es.id DESC LIMIT 10
            """)
            recent_attempts = [dict(row) for row in cursor.fetchall()]

            # Guruhlar bo'yicha o'rtacha ballar
            cursor.execute("""
                SELECT g.name as group_name, COUNT(es.id) as attempts_count,
                       ROUND(AVG(es.score_percent), 1) as avg_score
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN groups g ON g.id = st.group_id
                WHERE es.status = 'completed'
                GROUP BY g.id
                ORDER BY avg_score DESC
            """)
            group_performance = [dict(row) for row in cursor.fetchall()]

            return {
                "total_students": total_students,
                "total_tests": total_tests,
                "total_questions": total_questions,
                "total_attempts": total_attempts,
                "avg_score": avg_score,
                "recent_attempts": recent_attempts,
                "group_performance": group_performance
            }
        finally:
            conn.close()

    @staticmethod
    def get_group_test_stats(group_id: int, test_id: int) -> Optional[Dict[str, Any]]:
        """Guruh bo'yicha umumiy statistik ma'lumotlar (AI tahlili uchun)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT name FROM groups WHERE id = ?", (group_id,))
            grp = cursor.fetchone()
            cursor.execute("SELECT title FROM tests WHERE id = ?", (test_id,))
            tst = cursor.fetchone()

            if not grp or not tst:
                return None

            group_name = grp["name"]
            test_title = tst["title"]

            cursor.execute("""
                SELECT es.id, es.score_percent, es.correct_answers, es.total_questions,
                       u.full_name as student_name, st.student_code
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                WHERE st.group_id = ? AND es.test_id = ? AND es.status = 'completed'
            """, (group_id, test_id))
            attempts = [dict(row) for row in cursor.fetchall()]

            if not attempts:
                return {
                    "group_name": group_name,
                    "test_title": test_title,
                    "student_count": 0,
                    "avg_score": 0,
                    "topic_stats": [],
                    "attempts": []
                }

            student_count = len(attempts)
            avg_score = round(sum(a["score_percent"] for a in attempts) / student_count, 1)

            # Guruh bo'yicha mavzular statistikasi
            cursor.execute("""
                SELECT top.name as topic_name,
                       SUM(sts.total_questions) as total_q,
                       SUM(sts.correct_answers) as correct_q,
                       ROUND(AVG(sts.percentage), 1) as avg_percentage
                FROM session_topic_stats sts
                JOIN exam_sessions es ON es.id = sts.session_id
                JOIN students st ON st.id = es.student_id
                JOIN topics top ON top.id = sts.topic_id
                WHERE st.group_id = ? AND es.test_id = ? AND es.status = 'completed'
                GROUP BY top.id
                ORDER BY avg_percentage ASC
            """, (group_id, test_id))
            topic_stats = [dict(row) for row in cursor.fetchall()]

            return {
                "group_name": group_name,
                "test_title": test_title,
                "student_count": student_count,
                "avg_score": avg_score,
                "topic_stats": topic_stats,
                "attempts": attempts
            }
        finally:
            conn.close()
