import random
from datetime import datetime
from database.db import get_db_connection

class StudentService:
    @staticmethod
    def get_my_subjects(student_id: int):
        """O'quvchi faqat o'z guruhiga biriktirilgan fanlarni ko'radi."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM students WHERE id = ?", (student_id,))
            st = cursor.fetchone()
            if not st:
                return []
            group_id = st["group_id"]

            cursor.execute("""
                SELECT DISTINCT sub.id as subject_id, sub.name as subject_name, sub.code as subject_code,
                       sub.description as subject_description,
                       u.full_name as teacher_name, t.specialty as teacher_specialty,
                       ta.id as assignment_id,
                       (SELECT COUNT(*) FROM tests t 
                        LEFT JOIN test_groups_access tga ON tga.test_id = t.id AND tga.group_id = ta.group_id
                        WHERE t.assignment_id = ta.id AND LOWER(COALESCE(tga.status, t.status, '')) IN ('active', 'started')) as active_exams_count
                FROM teacher_assignments ta
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN teachers t ON t.id = ta.teacher_id
                JOIN users u ON u.id = t.user_id
                WHERE ta.group_id = ? AND ta.is_active = 1
                ORDER BY sub.name ASC
            """, (group_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_subject_exams(student_id: int, subject_id: int):
        """Tanlangan fan ichidagi ushbu o'quvchi guruhiga ochilgan imtihonlar."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM students WHERE id = ?", (student_id,))
            st = cursor.fetchone()
            if not st:
                return []
            group_id = st["group_id"]

            cursor.execute("""
                SELECT t.id, t.title, t.exam_type, t.duration_minutes, t.passing_score,
                       t.max_attempts, t.enable_camera, t.status,
                       COALESCE(tga.status, CASE WHEN LOWER(COALESCE(t.status, '')) IN ('active', 'started') THEN 'active' WHEN LOWER(COALESCE(t.status, '')) IN ('finished', 'results_published') THEN 'completed' ELSE 'pending' END) as group_access_status,
                       COALESCE(tga.is_results_announced, CASE WHEN LOWER(COALESCE(t.status, '')) IN ('results_published', 'finished') THEN 1 ELSE 0 END) as is_results_announced,
                       u.full_name as teacher_name, sub.name as subject_name,
                       (SELECT COUNT(*) FROM test_questions WHERE test_id = t.id) as question_count,
                       (SELECT COUNT(*) FROM exam_sessions WHERE test_id = t.id AND student_id = ? AND status = 'completed') as completed_attempts,
                       (SELECT MAX(score_percent) FROM exam_sessions WHERE test_id = t.id AND student_id = ? AND status = 'completed') as best_score,
                       (SELECT id FROM exam_sessions WHERE test_id = t.id AND student_id = ? AND status = 'completed' ORDER BY id DESC LIMIT 1) as last_session_id
                FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                LEFT JOIN test_groups_access tga ON tga.test_id = t.id AND tga.group_id = ta.group_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN teachers teach ON teach.id = ta.teacher_id
                JOIN users u ON u.id = teach.user_id
                WHERE ta.group_id = ? AND ta.subject_id = ?
                ORDER BY t.id DESC
            """, (student_id, student_id, student_id, group_id, subject_id))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_test_for_solving(student_id: int, test_id: int):
        """Imtihon savollarini o'quvchi uchun yuklash (javoblar yashirilgan, aralashtirilgan)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Ruxsat tekshirish
            cursor.execute("""
                SELECT t.id, t.title, t.duration_minutes, t.passing_score, t.randomize_questions,
                       t.enable_camera, t.max_attempts, t.status, sub.name as subject_name, u.full_name as teacher_name,
                       g.name as group_name, g.id as group_id
                FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN teachers teach ON teach.id = ta.teacher_id
                JOIN users u ON u.id = teach.user_id
                JOIN groups g ON g.id = ta.group_id
                JOIN students st ON st.group_id = ta.group_id
                WHERE t.id = ? AND st.id = ?
            """, (test_id, student_id))
            test_row = cursor.fetchone()
            if not test_row:
                raise ValueError("Test topilmadi yoki sizning guruhingizga bu testga kirish ruxsati yo'q")

            # Guruh ruxsat tekshiruvi (Multi-group access & State Machine)
            from services.test_service import TestService
            access_check = TestService.check_student_access(student_id, test_id)
            if not access_check.get("allowed", False):
                raise ValueError(access_check.get("reason", "Test guruhingiz uchun faol emas. Administrator yoki o'qituvchi ruxsatini kuting."))

            # O'quvchining o'z holati (student_test_state)
            cursor.execute("""
                SELECT status, block_reason FROM student_test_state
                WHERE student_id = ? AND test_id = ?
            """, (student_id, test_id))
            st_state = cursor.fetchone()
            if st_state:
                if st_state["status"] == "BLOCKED":
                    raise ValueError(f"🔒 Sizning testingiz bloklangan ({st_state['block_reason'] or 'Qoidabuzarlik'}). Administrator qarorini kuting.")
                elif st_state["status"] == "FINISHED":
                    raise ValueError("Testingiz yakunlangan, qayta topshirish taqiqlanadi.")

            # Urinishlar sonini tekshirish
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM exam_sessions
                WHERE test_id = ? AND student_id = ? AND status = 'completed'
            """, (test_id, student_id))
            attempts_made = cursor.fetchone()["cnt"]
            if attempts_made >= test_row["max_attempts"]:
                raise ValueError(f"Siz barcha {test_row['max_attempts']} ta urinishdan foydalanib bo'lgansiz.")

            # Savollarni olish
            cursor.execute("""
                SELECT qb.id, qb.question_text, qb.difficulty, qb.points, top.name as topic_name
                FROM test_questions tq
                JOIN question_bank qb ON qb.id = tq.question_id
                JOIN topics top ON top.id = qb.topic_id
                WHERE tq.test_id = ? AND qb.is_active = 1
                ORDER BY qb.id ASC
            """, (test_id,))
            questions = [dict(row) for row in cursor.fetchall()]

            randomize = bool(test_row["randomize_questions"])

            for q in questions:
                cursor.execute("""
                    SELECT id, option_text
                    FROM question_options
                    WHERE question_id = ?
                    ORDER BY id ASC
                """, (q["id"],))
                opts = [dict(opt) for opt in cursor.fetchall()]
                if randomize:
                    random.shuffle(opts)
                q["options"] = opts

            if randomize:
                random.shuffle(questions)

            # Proctoring sozlamalarini ham jo'natish (kamera, limitlar)
            proctoring_cfg = TestService.get_proctoring_settings(test_id)

            test_dict = dict(test_row)
            test_dict["proctoring"] = proctoring_cfg
            test_dict["enable_camera"] = proctoring_cfg.get("enable_camera", test_row["enable_camera"] or 0)
            test_dict["camera_policy"] = proctoring_cfg.get("camera_policy", "allow_without_camera")

            return {
                "test": test_dict,
                "questions": questions
            }
        finally:
            conn.close()

    @staticmethod
    def submit_exam(student_id: int, test_id: int, answers: dict,
                    tab_switch_count: int = 0, time_spent_seconds: int = 0, monitoring_events: list = None):
        """
        Imtihonni topshirish va natijalarni hisoblash:
        answers: {str(question_id): int(selected_option_id)}
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Guruhni aniqlash va test holatini tekshirish
            cursor.execute("SELECT group_id FROM students WHERE id = ?", (student_id,))
            st_g = cursor.fetchone()
            gid = st_g["group_id"] if st_g else None

            from services.test_service import TestService
            access_check = TestService.check_student_access(student_id, test_id)
            if not access_check.get("allowed", False):
                raise ValueError("Test administrator yoki o'qituvchi tomonidan yakunlangan yoki guruhingiz uchun faol emas. Yangi javob qabul qilinmaydi.")

            # 1. Test parametrlari va urinishlar sonini tekshirish
            cursor.execute("SELECT id, max_attempts FROM tests WHERE id = ?", (test_id,))
            test_row = cursor.fetchone()
            if not test_row:
                raise ValueError("Bunday test mavjud emas.")
            max_attempts = int(test_row["max_attempts"] or 1)

            cursor.execute("""
                SELECT COUNT(*) as cnt FROM exam_sessions 
                WHERE student_id = ? AND test_id = ? AND status = 'completed'
            """, (student_id, test_id))
            attempts_made = cursor.fetchone()["cnt"]
            if attempts_made >= max_attempts:
                raise ValueError(f"Siz ushbu test uchun berilgan barcha {max_attempts} ta urinishdan foydalanib bo'lgansiz.")

            # 2. Bloklanganlik va takroriy topshirishni tekshirish
            cursor.execute("SELECT status FROM student_test_state WHERE student_id = ? AND test_id = ?", (student_id, test_id))
            st_s = cursor.fetchone()
            if st_s:
                if st_s["status"] == "BLOCKED":
                    raise ValueError("Sizning testingiz qoidabuzarlik tufayli bloklangan. Javob qabul qilinmaydi.")
                if st_s["status"] == "FINISHED":
                    raise ValueError("Ushbu imtihon allaqachon topshirilgan va yakunlangan. Qayta javob qabul qilinmaydi.")

            # Parallel va takroriy topshirishni oldini olish uchun darhol FINISHED holatiga o'tkazish
            cursor.execute("""
                INSERT INTO student_test_state (student_id, test_id, status)
                VALUES (?, ?, 'FINISHED')
                ON CONFLICT(student_id, test_id) DO UPDATE SET status = 'FINISHED'
            """, (student_id, test_id))
            conn.commit()

            # Testdagi savollarni olish
            cursor.execute("""
                SELECT qb.id, qb.topic_id, qb.points, top.name as topic_name
                FROM test_questions tq
                JOIN question_bank qb ON qb.id = tq.question_id
                JOIN topics top ON top.id = qb.topic_id
                WHERE tq.test_id = ?
            """, (test_id,))
            questions = [dict(row) for row in cursor.fetchall()]

            # To'g'ri variantlar xaritasi
            cursor.execute("""
                SELECT id, question_id FROM question_options
                WHERE is_correct = 1 AND question_id IN (SELECT question_id FROM test_questions WHERE test_id = ?)
            """, (test_id,))
            correct_map = {row["question_id"]: row["id"] for row in cursor.fetchall()}

            # Server-side nazorat: proctoring hodisalaridan haqiqiy tab_switch sanog'ini hisoblash
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM proctoring_events
                WHERE student_id = ? AND test_id = ? AND event_type IN ('tab_switch', 'window_blur', 'fullscreen_exit')
            """, (student_id, test_id))
            ev_cnt = cursor.fetchone()["cnt"]
            final_tab_switches = max(int(tab_switch_count or 0), int(ev_cnt))

            total_questions = len(questions)
            total_points = sum(max(1, int(q.get("points") or 1)) for q in questions)
            earned_points = 0
            correct_count = 0
            incorrect_count = 0
            topic_stats = {} # {topic_id: {"name": ..., "total": 0, "correct": 0}}
            student_answer_records = []

            for q in questions:
                qid = q["id"]
                top_id = q["topic_id"]
                top_name = q["topic_name"]
                q_pts = max(1, int(q.get("points") or 1))

                if top_id not in topic_stats:
                    topic_stats[top_id] = {"name": top_name, "total": 0, "correct": 0}
                topic_stats[top_id]["total"] += 1

                selected_opt_id = answers.get(str(qid)) or answers.get(qid)
                if selected_opt_id is not None:
                    try:
                        selected_opt_id = int(selected_opt_id)
                    except (ValueError, TypeError):
                        selected_opt_id = None

                is_correct = 1 if (selected_opt_id and correct_map.get(qid) == selected_opt_id) else 0

                if is_correct:
                    correct_count += 1
                    earned_points += q_pts
                    topic_stats[top_id]["correct"] += 1
                else:
                    incorrect_count += 1

                student_answer_records.append((qid, selected_opt_id, is_correct))

            score_percent = round((earned_points / total_points * 100), 1) if total_points > 0 else 0.0

            # 1. Exam session saqlash
            cursor.execute("""
                INSERT INTO exam_sessions (
                    test_id, student_id, score_percent, total_questions, correct_answers, 
                    incorrect_answers, tab_switch_count, time_spent_seconds, status, finished_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'completed', datetime('now'))
            """, (test_id, student_id, score_percent, total_questions, correct_count, 
                  incorrect_count, final_tab_switches, time_spent_seconds))
            session_id = cursor.lastrowid

            # 2. O'quvchi holatini FINISHED ga o'tkazish
            cursor.execute("""
                INSERT INTO student_test_state (student_id, test_id, status)
                VALUES (?, ?, 'FINISHED')
                ON CONFLICT(student_id, test_id) DO UPDATE SET status = 'FINISHED'
            """, (student_id, test_id))

            # 3. Javoblarni saqlash
            for qid, sel_id, is_c in student_answer_records:
                cursor.execute("""
                    INSERT INTO student_answers (session_id, question_id, selected_option_id, is_correct)
                    VALUES (?, ?, ?, ?)
                """, (session_id, qid, sel_id, is_c))

            # 4. Mavzular statistikasi
            for top_id, stats in topic_stats.items():
                top_pct = round((stats["correct"] / stats["total"] * 100), 1) if stats["total"] > 0 else 0.0
                cursor.execute("""
                    INSERT INTO session_topic_stats (session_id, topic_id, total_questions, correct_answers, percentage)
                    VALUES (?, ?, ?, ?, ?)
                """, (session_id, top_id, stats["total"], stats["correct"], top_pct))

            # 5. Monitoring / Shubhali hodisalar
            if tab_switch_count > 0:
                cursor.execute("""
                    INSERT INTO monitoring_events (session_id, event_type, details)
                    VALUES (?, 'tab_switch', ?)
                """, (session_id, f"Test davomida {tab_switch_count} marta oynadan chiqish qayd etildi"))

            if monitoring_events:
                for evt in monitoring_events:
                    cursor.execute("""
                        INSERT INTO monitoring_events (session_id, event_type, details)
                        VALUES (?, ?, ?)
                    """, (session_id, evt.get("type", "warning"), evt.get("details", "")))

            conn.commit()

            return {
                "session_id": session_id,
                "score_percent": score_percent,
                "total_questions": total_questions,
                "correct_answers": correct_count,
                "incorrect_answers": incorrect_count
            }
        finally:
            conn.close()

    @staticmethod
    def get_session_result(session_id: int, is_admin_or_teacher: bool = False):
        """Topshirilgan test natijasini to'liq ko'rish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT es.id as session_id, es.student_id, es.score_percent, es.total_questions, es.correct_answers,
                       es.incorrect_answers, es.tab_switch_count, es.time_spent_seconds, es.ai_analysis,
                       es.started_at, es.finished_at,
                       t.id as test_id, t.title as test_title, t.passing_score,
                       sub.name as subject_name, sub.code as subject_code,
                       u.full_name as student_name, st.student_code, g.name as group_name, g.id as group_id
                FROM exam_sessions es
                JOIN tests t ON t.id = es.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                WHERE es.id = ?
            """, (session_id,))
            session_row = cursor.fetchone()
            if not session_row:
                return None

            result = dict(session_row)
            test_id = result["test_id"]
            group_id = result["group_id"]

            from services.test_service import TestService
            cursor.execute("""
                SELECT is_results_announced, status FROM test_groups_access
                WHERE test_id = ? AND group_id = ?
            """, (test_id, group_id))
            tga_res = cursor.fetchone()
            is_published = False
            if tga_res:
                if tga_res["is_results_announced"] == 1 or tga_res["status"] == "completed":
                    is_published = True
            if not is_published:
                test_state = TestService.get_test_state(test_id, group_id)
                is_published = (test_state in ("RESULTS_PUBLISHED", "FINISHED"))

            # 1-qoida: O'quvchi natijani e'lon qilinmaguncha ko'rmaydi
            if not is_admin_or_teacher and not is_published:
                return {
                    "is_published": False,
                    "session_id": session_id,
                    "student_id": result["student_id"],
                    "test_title": result["test_title"],
                    "student_name": result["student_name"],
                    "student_code": result["student_code"],
                    "group_name": result["group_name"],
                    "subject_name": result["subject_name"],
                    "message": "Test yakunlandi. Natijangiz administrator tomonidan tasdiqlangandan keyin ko'rsatiladi."
                }

            result["is_published"] = True

            # Mavzular statistikasi
            cursor.execute("""
                SELECT sts.topic_id, top.name as topic_name, sts.total_questions,
                       sts.correct_answers, sts.percentage
                FROM session_topic_stats sts
                JOIN topics top ON top.id = sts.topic_id
                WHERE sts.session_id = ?
                ORDER BY sts.percentage ASC
            """, (session_id,))
            result["topics"] = [dict(row) for row in cursor.fetchall()]

            # Savollar va variantlar
            cursor.execute("""
                SELECT sa.question_id, sa.selected_option_id, sa.is_correct,
                       qb.question_text, qb.difficulty, qb.explanation,
                       top.name as topic_name
                FROM student_answers sa
                JOIN question_bank qb ON qb.id = sa.question_id
                JOIN topics top ON top.id = qb.topic_id
                WHERE sa.session_id = ?
                ORDER BY qb.id ASC
            """, (session_id,))
            questions_ans = [dict(row) for row in cursor.fetchall()]

            for q in questions_ans:
                cursor.execute("""
                    SELECT id, option_text, is_correct
                    FROM question_options
                    WHERE question_id = ?
                    ORDER BY id ASC
                """, (q["question_id"],))
                q["options"] = [dict(opt) for opt in cursor.fetchall()]

            result["questions"] = questions_ans
            return result
        finally:
            conn.close()

    @staticmethod
    def get_student_learning_map(student_id: int):
        """
        'Ta'lim xaritasi' (Knowledge Map) — O'quvchining barcha fanlar bo'yicha
        o'zlashtirish darajasi, zaif mavzulari va vaqt bo'yicha dinamikasi.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT u.full_name as student_name, st.student_code, g.name as group_name
                FROM students st
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                WHERE st.id = ?
            """, (student_id,))
            header = cursor.fetchone()
            if not header:
                return None

            # 1. Fanlar bo'yicha o'rtacha ballar
            cursor.execute("""
                SELECT sub.id as subject_id, sub.name as subject_name,
                       COUNT(es.id) as tests_taken,
                       ROUND(AVG(es.score_percent), 1) as avg_score
                FROM exam_sessions es
                JOIN tests t ON t.id = es.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                WHERE es.student_id = ? AND es.status = 'completed'
                GROUP BY sub.id
                ORDER BY avg_score DESC
            """, (student_id,))
            subject_mastery = [dict(row) for row in cursor.fetchall()]

            # 2. Mavzular bo'yicha o'zlashtirish va muammoli mavzular
            cursor.execute("""
                SELECT top.name as topic_name, sub.name as subject_name,
                       SUM(sts.total_questions) as total_q,
                       SUM(sts.correct_answers) as correct_q,
                       ROUND(AVG(sts.percentage), 1) as avg_percentage
                FROM session_topic_stats sts
                JOIN exam_sessions es ON es.id = sts.session_id
                JOIN topics top ON top.id = sts.topic_id
                JOIN subjects sub ON sub.id = top.subject_id
                WHERE es.student_id = ? AND es.status = 'completed'
                GROUP BY top.id
                ORDER BY avg_percentage ASC
            """, (student_id,))
            topic_mastery = [dict(row) for row in cursor.fetchall()]

            # 3. So'nggi testlar dinamikasi (Trend)
            cursor.execute("""
                SELECT es.id, t.title as test_title, sub.name as subject_name,
                       es.score_percent, es.finished_at
                FROM exam_sessions es
                JOIN tests t ON t.id = es.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                WHERE es.student_id = ? AND es.status = 'completed'
                ORDER BY es.id ASC LIMIT 10
            """, (student_id,))
            trend_history = [dict(row) for row in cursor.fetchall()]

            return {
                "student_info": dict(header),
                "subject_mastery": subject_mastery,
                "topic_mastery": topic_mastery,
                "trend_history": trend_history
            }
        finally:
            conn.close()
