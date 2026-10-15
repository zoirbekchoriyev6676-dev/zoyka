import random
from database.db import get_db_connection

class TeacherService:
    @staticmethod
    def get_my_assignments(teacher_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ta.id as assignment_id, ta.subject_id, ta.group_id, ta.academic_year, ta.semester,
                       sub.name as subject_name, sub.code as subject_code,
                       g.name as group_name,
                       (SELECT COUNT(*) FROM students WHERE group_id = g.id) as student_count,
                       (SELECT COUNT(*) FROM tests WHERE assignment_id = ta.id) as test_count
                FROM teacher_assignments ta
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN groups g ON g.id = ta.group_id
                WHERE ta.teacher_id = ? AND ta.is_active = 1
                ORDER BY sub.name ASC, g.name ASC
            """, (teacher_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_my_subjects(teacher_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT DISTINCT sub.id, sub.name, sub.code, sub.description
                FROM teacher_assignments ta
                JOIN subjects sub ON sub.id = ta.subject_id
                WHERE ta.teacher_id = ? AND ta.is_active = 1
                ORDER BY sub.name ASC
            """, (teacher_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_topics_by_subject(subject_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.subject_id, t.name, t.description,
                       (SELECT COUNT(*) FROM question_bank WHERE topic_id = t.id) as question_count
                FROM topics t
                WHERE t.subject_id = ?
                ORDER BY t.name ASC
            """, (subject_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def add_topic(subject_id: int, name: str, description: str = ""):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO topics (subject_id, name, description) VALUES (?, ?, ?)",
                           (subject_id, name.strip(), description.strip()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def verify_teacher_subject(teacher_id: int, subject_id: int) -> bool:
        """O'qituvchining ushbu fanga biriktirilganligini tekshirish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM teacher_assignments 
                WHERE teacher_id = ? AND subject_id = ? AND is_active = 1
                LIMIT 1
            """, (teacher_id, subject_id))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    @staticmethod
    def verify_teacher_assignment(teacher_id: int, assignment_id: int) -> bool:
        """O'qituvchining ushbu biriktiruvga (guruh/fan) egaligini tekshirish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT 1 FROM teacher_assignments 
                WHERE id = ? AND teacher_id = ? AND is_active = 1
                LIMIT 1
            """, (assignment_id, teacher_id))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    @staticmethod
    def verify_question_ownership(teacher_id: int, question_id: int) -> bool:
        """Savol ushbu o'qituvchiga yoki uning biriktirilgan faniga tegishliligini tekshirish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT qb.id FROM question_bank qb
                WHERE qb.id = ? AND (
                    qb.teacher_id = ? 
                    OR qb.subject_id IN (
                        SELECT subject_id FROM teacher_assignments 
                        WHERE teacher_id = ? AND is_active = 1
                    )
                )
                LIMIT 1
            """, (question_id, teacher_id, teacher_id))
            return cursor.fetchone() is not None
        finally:
            conn.close()

    # ------------------ SAVOLLAR BANKI ------------------
    @staticmethod
    def get_question_bank(subject_id: int = None, topic_id: int = None, difficulty: str = None, teacher_id: int = None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT qb.id, qb.subject_id, qb.topic_id, qb.question_text, qb.difficulty,
                       qb.points, qb.explanation, qb.is_active, qb.created_at,
                       t.name as topic_name, sub.name as subject_name
                FROM question_bank qb
                JOIN topics t ON t.id = qb.topic_id
                JOIN subjects sub ON sub.id = qb.subject_id
                WHERE 1=1
            """
            params = []
            if teacher_id is not None:
                query += " AND (qb.teacher_id = ? OR qb.subject_id IN (SELECT subject_id FROM teacher_assignments WHERE teacher_id = ? AND is_active = 1))"
                params.extend([teacher_id, teacher_id])
            if subject_id:
                query += " AND qb.subject_id = ?"
                params.append(subject_id)
            if topic_id:
                query += " AND qb.topic_id = ?"
                params.append(topic_id)
            if difficulty:
                query += " AND qb.difficulty = ?"
                params.append(difficulty)
            query += " ORDER BY qb.id DESC"
            cursor.execute(query, params)
            questions = [dict(row) for row in cursor.fetchall()]

            for q in questions:
                cursor.execute("""
                    SELECT id, option_text, is_correct
                    FROM question_options
                    WHERE question_id = ?
                    ORDER BY id ASC
                """, (q["id"],))
                q["options"] = [dict(opt) for opt in cursor.fetchall()]

            return questions
        finally:
            conn.close()

    @staticmethod
    def create_question(subject_id: int, topic_id: int, teacher_id: int, question_text: str,
                        difficulty: str = "medium", points: int = 1, explanation: str = "", options: list = []):
        if not options:
            raise ValueError("Savolda kamida 2 ta variant bo'lishi shart")
        if not any(bool(opt.get("is_correct")) for opt in options):
            raise ValueError("Savolda kamida bitta to'g'ri variant ko'rsatilishi shart")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO question_bank (subject_id, topic_id, teacher_id, question_text, difficulty, points, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (subject_id, topic_id, teacher_id, question_text.strip(), difficulty, points, explanation.strip()))
            qid = cursor.lastrowid

            for opt in options:
                cursor.execute("""
                    INSERT INTO question_options (question_id, option_text, is_correct)
                    VALUES (?, ?, ?)
                """, (qid, opt["option_text"].strip(), 1 if opt.get("is_correct") else 0))

            conn.commit()
            return qid
        finally:
            conn.close()

    @staticmethod
    def delete_question(question_id: int, teacher_id: int = None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if teacher_id is not None:
                cursor.execute("""
                    DELETE FROM question_bank 
                    WHERE id = ? AND (
                        teacher_id = ? 
                        OR subject_id IN (SELECT subject_id FROM teacher_assignments WHERE teacher_id = ? AND is_active = 1)
                    )
                """, (question_id, teacher_id, teacher_id))
            else:
                cursor.execute("DELETE FROM question_bank WHERE id = ?", (question_id,))
            conn.commit()
            return cursor.rowcount > 0
        finally:
            conn.close()

    # ------------------ TESTLAR VA BLUEPRINT ------------------
    @staticmethod
    def get_my_tests(teacher_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.title, t.exam_type, t.duration_minutes, t.passing_score,
                       t.randomize_questions, t.enable_camera, t.status, t.created_at,
                       sub.name as subject_name, g.name as group_name, ta.id as assignment_id,
                       (SELECT COUNT(*) FROM test_questions WHERE test_id = t.id) as question_count,
                       (SELECT COUNT(*) FROM exam_sessions WHERE test_id = t.id AND status = 'completed') as attempts_count,
                       (SELECT ROUND(AVG(score_percent), 1) FROM exam_sessions WHERE test_id = t.id AND status = 'completed') as avg_score
                FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN groups g ON g.id = ta.group_id
                WHERE ta.teacher_id = ?
                ORDER BY t.id DESC
            """, (teacher_id,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_test_blueprint(teacher_id: int, assignment_id: int, title: str,
                              duration_minutes: int = 30, passing_score: int = 60,
                              exam_type: str = "midterm", enable_camera: int = 0,
                              blueprint: dict = None, specific_question_ids: list = None):
        """
        Test yaratish va savollarni biriktirish:
        blueprint: {'by_topic': {topic_id: count, ...}, 'by_difficulty': {'easy': count, 'medium': count, 'hard': count}}
        specific_question_ids: [1, 2, 3...]
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # 1. Assignment o'qituvchiga tegishliligini tekshirish
            cursor.execute("""
                SELECT ta.subject_id, ta.group_id FROM teacher_assignments ta
                WHERE ta.id = ? AND ta.teacher_id = ?
            """, (assignment_id, teacher_id))
            assign_row = cursor.fetchone()
            if not assign_row:
                raise ValueError("Biriktirilgan fan/guruh topilmadi yoki sizga tegishli emas")

            subject_id = assign_row["subject_id"]
            group_id = assign_row["group_id"]
            db_exam_type = TeacherService._normalize_exam_type(exam_type)

            cursor.execute("""
                INSERT INTO tests (title, assignment_id, exam_type, duration_minutes, passing_score, enable_camera, status)
                VALUES (?, ?, ?, ?, ?, ?, 'ready')
            """, (title.strip(), assignment_id, db_exam_type, duration_minutes, passing_score, enable_camera))
            test_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO test_sessions (group_id, test_id, status)
                VALUES (?, ?, 'READY')
            """, (group_id, test_id))

            selected_q_ids = set()

            # Maxsus tanlangan savollar bo'lsa
            if specific_question_ids:
                for qid in specific_question_ids:
                    selected_q_ids.add(qid)

            # Blueprint bo'yicha avtomatik yig'ish (Mavzu bo'yicha)
            if blueprint and blueprint.get("by_topic"):
                for top_id, count in blueprint["by_topic"].items():
                    cursor.execute("""
                        SELECT id FROM question_bank
                        WHERE subject_id = ? AND topic_id = ? AND is_active = 1
                        ORDER BY RANDOM() LIMIT ?
                    """, (subject_id, int(top_id), int(count)))
                    for row in cursor.fetchall():
                        selected_q_ids.add(row["id"])

            # Agar savollar belgilanmagan bo'lsa, mavjud barcha savollardan testga qo'shish
            if not selected_q_ids:
                cursor.execute("""
                    SELECT id FROM question_bank
                    WHERE subject_id = ? AND is_active = 1
                    ORDER BY RANDOM() LIMIT 20
                """, (subject_id,))
                for row in cursor.fetchall():
                    selected_q_ids.add(row["id"])

            for qid in selected_q_ids:
                cursor.execute("INSERT OR IGNORE INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, qid))

            conn.commit()
            return test_id
        finally:
            conn.close()

    # ------------------ O'QITUVCHI HISOBOTLARI ------------------
    @staticmethod
    def get_assignment_report(assignment_id: int):
        """10-A Matematika bo'yicha umumiy sinf ko'rsatkichi, o'rtacha ball, mavzular foizlari."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ta.id, sub.name as subject_name, g.name as group_name
                FROM teacher_assignments ta
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN groups g ON g.id = ta.group_id
                WHERE ta.id = ?
            """, (assignment_id,))
            header = cursor.fetchone()
            if not header:
                return None

            # Barcha topshirilgan natijalar
            cursor.execute("""
                SELECT es.id, es.score_percent, es.correct_answers, es.total_questions, es.finished_at,
                       u.full_name as student_name, st.student_code
                FROM exam_sessions es
                JOIN tests t ON t.id = es.test_id
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                WHERE t.assignment_id = ? AND es.status = 'completed'
                ORDER BY es.score_percent DESC
            """, (assignment_id,))
            attempts = [dict(row) for row in cursor.fetchall()]

            student_count = len(attempts)
            avg_score = round(sum(a["score_percent"] for a in attempts) / student_count, 1) if student_count > 0 else 0.0

            # Mavzular bo'yicha tahlil (Algebra 81%, Geometriya 69% va h.k.)
            cursor.execute("""
                SELECT top.name as topic_name,
                       SUM(sts.total_questions) as total_q,
                       SUM(sts.correct_answers) as correct_q,
                       ROUND(AVG(sts.percentage), 1) as avg_percentage
                FROM session_topic_stats sts
                JOIN exam_sessions es ON es.id = sts.session_id
                JOIN tests t ON t.id = es.test_id
                JOIN topics top ON top.id = sts.topic_id
                WHERE t.assignment_id = ? AND es.status = 'completed'
                GROUP BY top.id
                ORDER BY avg_percentage ASC
            """, (assignment_id,))
            topic_stats = [dict(row) for row in cursor.fetchall()]

            return {
                "assignment_id": assignment_id,
                "subject_name": header["subject_name"],
                "group_name": header["group_name"],
                "student_count": student_count,
                "avg_score": avg_score,
                "attempts": attempts,
                "topic_stats": topic_stats
            }
        finally:
            conn.close()

    # ------------------ KENGAYTIRILGAN TEST BAZASI VA BOSHQARUVI ------------------
    @staticmethod
    def _normalize_status(st: str) -> str:
        if not st:
            return 'draft'
        st = str(st).lower().strip()
        if st in ('active', 'faol'):
            return 'active'
        if st in ('finished', 'archived', 'arxiv'):
            return 'finished'
        return 'draft'

    @staticmethod
    def _normalize_exam_type(et: str) -> str:
        if not et:
            return 'midterm'
        et = str(et).lower().strip()
        mapping = {
            'oraliq': 'midterm',
            'yakuniy': 'final',
            'joriy': 'quiz',
            'kirish': 'diagnostic',
            'midterm': 'midterm',
            'final': 'final',
            'quiz': 'quiz',
            'diagnostic': 'diagnostic'
        }
        return mapping.get(et, 'midterm')

    @staticmethod
    def get_test_detail(test_id: int, teacher_id: int = None):
        """Testning to'liq ma'lumotlari va unga biriktirilgan barcha savollar."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT t.id, t.title, t.assignment_id, t.exam_type, t.duration_minutes,
                       t.passing_score, t.randomize_questions, t.max_attempts, t.enable_camera,
                       t.status, t.created_at,
                       sub.id as subject_id, sub.name as subject_name, sub.code as subject_code,
                       g.id as group_id, g.name as group_name,
                       u.full_name as teacher_name,
                       (SELECT COUNT(*) FROM exam_sessions WHERE test_id = t.id AND status = 'completed') as attempts_count
                FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN groups g ON g.id = ta.group_id
                JOIN teachers teach ON teach.id = ta.teacher_id
                JOIN users u ON u.id = teach.user_id
                WHERE t.id = ?
            """
            params = [test_id]
            if teacher_id:
                query += " AND ta.teacher_id = ?"
                params.append(teacher_id)

            cursor.execute(query, params)
            test_row = cursor.fetchone()
            if not test_row:
                return None

            test_dict = dict(test_row)

            # Savollarni olish
            cursor.execute("""
                SELECT qb.id as question_id, qb.subject_id, qb.topic_id, qb.question_text,
                       qb.difficulty, qb.points, qb.explanation, qb.is_active,
                       top.name as topic_name, tq.id as test_question_id
                FROM test_questions tq
                JOIN question_bank qb ON qb.id = tq.question_id
                LEFT JOIN topics top ON top.id = qb.topic_id
                WHERE tq.test_id = ?
                ORDER BY tq.id ASC
            """, (test_id,))
            questions = [dict(r) for r in cursor.fetchall()]

            for q in questions:
                cursor.execute("""
                    SELECT id, option_text, is_correct
                    FROM question_options
                    WHERE question_id = ?
                    ORDER BY id ASC
                """, (q["question_id"],))
                q["options"] = [dict(opt) for opt in cursor.fetchall()]

            test_dict["questions"] = questions
            test_dict["question_count"] = len(questions)
            return test_dict
        finally:
            conn.close()

    @staticmethod
    def create_full_test(teacher_id: int, assignment_id: int, title: str,
                         duration_minutes: int = 30, passing_score: int = 60,
                         exam_type: str = "midterm", status: str = "active",
                         questions: list = None):
        """
        Qo'lda kiritilgan, Word'dan yuklangan yoki AI tomonidan yaratilgan savollardan to'liq test tuzish.
        questions: [{'question_text': ..., 'options': [...], 'topic_name': ..., 'difficulty': ..., 'points': ..., 'explanation': ...}]
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # O'qituvchiga tegishliligini tekshirish
            cursor.execute("""
                SELECT ta.subject_id FROM teacher_assignments ta
                WHERE ta.id = ? AND ta.teacher_id = ?
            """, (assignment_id, teacher_id))
            assign_row = cursor.fetchone()
            if not assign_row:
                raise ValueError("Biriktirilgan fan/guruh topilmadi yoki sizga tegishli emas")

            subject_id = assign_row["subject_id"]
            db_status = TeacherService._normalize_status(status)
            db_exam_type = TeacherService._normalize_exam_type(exam_type)

            cursor.execute("""
                INSERT INTO tests (title, assignment_id, exam_type, duration_minutes, passing_score, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title.strip(), assignment_id, db_exam_type, duration_minutes, passing_score, db_status))
            test_id = cursor.lastrowid

            if questions:
                for q in questions:
                    # Agar allaqachon mavjud savol ID berilgan bo'lsa
                    if q.get("question_id"):
                        cursor.execute("INSERT OR IGNORE INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, q["question_id"]))
                        continue

                    # Yangi savolni yaratish
                    top_name = (q.get("topic_name") or "Umumiy mavzu").strip()
                    cursor.execute("SELECT id FROM topics WHERE subject_id = ? AND LOWER(name) = LOWER(?)", (subject_id, top_name))
                    top_row = cursor.fetchone()
                    if top_row:
                        top_id = top_row["id"]
                    else:
                        cursor.execute("INSERT INTO topics (subject_id, name, description) VALUES (?, ?, '')", (subject_id, top_name))
                        top_id = cursor.lastrowid

                    diff = q.get("difficulty", "medium")
                    if diff not in ("easy", "medium", "hard"):
                        diff = "medium"
                    pts = max(1, int(q.get("points", 1)))
                    exp = (q.get("explanation") or "").strip()
                    q_text = (q.get("question_text") or "").strip()

                    cursor.execute("""
                        INSERT INTO question_bank (subject_id, topic_id, teacher_id, question_text, difficulty, points, explanation)
                        VALUES (?, ?, ?, ?, ?, ?, ?)
                    """, (subject_id, top_id, teacher_id, q_text, diff, pts, exp))
                    qid = cursor.lastrowid

                    # Variantlarni kiritish
                    opts = q.get("options", [])
                    has_corr = any(bool(opt.get("is_correct")) for opt in opts)
                    if not has_corr and opts:
                        raise ValueError(f"'{q_text[:30]}...' savolida kamida bitta to'g'ri variant ko'rsatilishi shart")

                    for idx, opt in enumerate(opts):
                        opt_text = (opt.get("option_text") or "").strip()
                        is_corr = 1 if opt.get("is_correct") else 0
                        cursor.execute("""
                            INSERT INTO question_options (question_id, option_text, is_correct)
                            VALUES (?, ?, ?)
                        """, (qid, opt_text, is_corr))

                    cursor.execute("INSERT INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, qid))

            conn.commit()
            return test_id
        finally:
            conn.close()

    @staticmethod
    def update_test_details(test_id: int, teacher_id: int, title: str = None,
                            duration_minutes: int = None, passing_score: int = None,
                            exam_type: str = None, status: str = None, assignment_id: int = None):
        """Mavjud test parametrlarini tahrirlash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            # Tekshirish
            cursor.execute("""
                SELECT t.id FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                WHERE t.id = ? AND ta.teacher_id = ?
            """, (test_id, teacher_id))
            if not cursor.fetchone():
                raise ValueError("Test topilmadi yoki sizga tegishli emas")

            updates = []
            params = []
            if title is not None:
                updates.append("title = ?")
                params.append(title.strip())
            if duration_minutes is not None:
                updates.append("duration_minutes = ?")
                params.append(max(5, int(duration_minutes)))
            if passing_score is not None:
                updates.append("passing_score = ?")
                params.append(max(1, min(100, int(passing_score))))
            if exam_type is not None:
                updates.append("exam_type = ?")
                params.append(TeacherService._normalize_exam_type(exam_type))
            if status is not None:
                updates.append("status = ?")
                params.append(TeacherService._normalize_status(status))
            if assignment_id is not None:
                # Yangi assignment tekshiruvi
                cursor.execute("SELECT id FROM teacher_assignments WHERE id = ? AND teacher_id = ?", (assignment_id, teacher_id))
                if cursor.fetchone():
                    updates.append("assignment_id = ?")
                    params.append(assignment_id)

            if updates:
                params.append(test_id)
                cursor.execute(f"UPDATE tests SET {', '.join(updates)} WHERE id = ?", params)
                conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def toggle_test_status(test_id: int, teacher_id: int, target_status: str = None):
        """Testni faol (active) yoki nofaol (draft) qilish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.status FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                WHERE t.id = ? AND ta.teacher_id = ?
            """, (test_id, teacher_id))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Test topilmadi yoki sizga tegishli emas")

            current_status = row["status"]
            if target_status:
                new_status = TeacherService._normalize_status(target_status)
            else:
                new_status = "draft" if current_status == "active" else "active"

            cursor.execute("UPDATE tests SET status = ? WHERE id = ?", (new_status, test_id))
            conn.commit()
            return new_status
        finally:
            conn.close()

    @staticmethod
    def append_question_to_test(test_id: int, teacher_id: int, question_data: dict):
        """Yaratilgan testga keyinchalik yangi savol (21-, 22-savol...) qo'shish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, ta.subject_id FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                WHERE t.id = ? AND ta.teacher_id = ?
            """, (test_id, teacher_id))
            t_row = cursor.fetchone()
            if not t_row:
                raise ValueError("Test topilmadi yoki sizga tegishli emas")

            subject_id = t_row["subject_id"]
            top_name = (question_data.get("topic_name") or "Umumiy mavzu").strip()
            cursor.execute("SELECT id FROM topics WHERE subject_id = ? AND LOWER(name) = LOWER(?)", (subject_id, top_name))
            top_row = cursor.fetchone()
            if top_row:
                top_id = top_row["id"]
            else:
                cursor.execute("INSERT INTO topics (subject_id, name, description) VALUES (?, ?, '')", (subject_id, top_name))
                top_id = cursor.lastrowid

            diff = question_data.get("difficulty", "medium")
            if diff not in ("easy", "medium", "hard"):
                diff = "medium"
            pts = max(1, int(question_data.get("points", 1)))
            exp = (question_data.get("explanation") or "").strip()
            q_text = (question_data.get("question_text") or "").strip()

            cursor.execute("""
                INSERT INTO question_bank (subject_id, topic_id, teacher_id, question_text, difficulty, points, explanation)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (subject_id, top_id, teacher_id, q_text, diff, pts, exp))
            qid = cursor.lastrowid

            opts = question_data.get("options", [])
            for opt in opts:
                opt_text = (opt.get("option_text") or "").strip()
                is_corr = 1 if opt.get("is_correct") else 0
                cursor.execute("""
                    INSERT INTO question_options (question_id, option_text, is_correct)
                    VALUES (?, ?, ?)
                """, (qid, opt_text, is_corr))

            cursor.execute("INSERT OR IGNORE INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, qid))
            conn.commit()
            return qid
        finally:
            conn.close()

    @staticmethod
    def update_test_question(test_id: int, question_id: int, question_data: dict):
        """Test ichidagi savolni tahrirlash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            q_text = question_data.get("question_text")
            diff = question_data.get("difficulty", "medium")
            pts = question_data.get("points", 1)
            exp = question_data.get("explanation", "")

            cursor.execute("""
                UPDATE question_bank
                SET question_text = COALESCE(?, question_text),
                    difficulty = COALESCE(?, difficulty),
                    points = COALESCE(?, points),
                    explanation = COALESCE(?, explanation)
                WHERE id = ?
            """, (q_text, diff, pts, exp, question_id))

            # Variantlar yangilanishi
            opts = question_data.get("options")
            if opts and isinstance(opts, list):
                cursor.execute("DELETE FROM question_options WHERE question_id = ?", (question_id,))
                for opt in opts:
                    opt_text = (opt.get("option_text") or "").strip()
                    is_corr = 1 if opt.get("is_correct") else 0
                    cursor.execute("""
                        INSERT INTO question_options (question_id, option_text, is_correct)
                        VALUES (?, ?, ?)
                    """, (question_id, opt_text, is_corr))

            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def remove_question_from_test(test_id: int, question_id: int):
        """Savolni testdan chiqarib tashlash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM test_questions WHERE test_id = ? AND question_id = ?", (test_id, question_id))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def clone_test(test_id: int, teacher_id: int):
        """Mavjud testni barcha savollari bilan birga nusxalash (Clone)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.title, t.assignment_id, t.exam_type, t.duration_minutes,
                       t.passing_score, t.randomize_questions, t.max_attempts, t.enable_camera
                FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                WHERE t.id = ? AND ta.teacher_id = ?
            """, (test_id, teacher_id))
            row = cursor.fetchone()
            if not row:
                raise ValueError("Nusxalanadigan test topilmadi yoki sizga tegishli emas")

            new_title = f"{row['title']} (Nusxa)"
            cursor.execute("""
                INSERT INTO tests (title, assignment_id, exam_type, duration_minutes, passing_score,
                                  randomize_questions, max_attempts, enable_camera, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'draft')
            """, (new_title, row['assignment_id'], row['exam_type'], row['duration_minutes'],
                  row['passing_score'], row['randomize_questions'], row['max_attempts'], row['enable_camera']))
            new_test_id = cursor.lastrowid

            # Savollarni nusxalash
            cursor.execute("SELECT question_id FROM test_questions WHERE test_id = ?", (test_id,))
            for q_row in cursor.fetchall():
                cursor.execute("INSERT INTO test_questions (test_id, question_id) VALUES (?, ?)", (new_test_id, q_row["question_id"]))

            conn.commit()
            return new_test_id
        finally:
            conn.close()

    @staticmethod
    def delete_or_archive_test(test_id: int, teacher_id: int):
        """
        Testni o'chirish yoki arxivlash.
        Agar o'quvchilar tomonidan topshirilgan bo'lsa -> arxivlaydi (status = 'finished').
        Agar hali topshirilmagan bo'lsa -> butunlay o'chiradi.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.title FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                WHERE t.id = ? AND ta.teacher_id = ?
            """, (test_id, teacher_id))
            if not cursor.fetchone():
                raise ValueError("Test topilmadi yoki sizga tegishli emas")

            cursor.execute("SELECT COUNT(*) as cnt FROM exam_sessions WHERE test_id = ?", (test_id,))
            attempts_count = cursor.fetchone()["cnt"]

            if attempts_count > 0:
                cursor.execute("UPDATE tests SET status = 'finished' WHERE id = ?", (test_id,))
                conn.commit()
                return {
                    "action": "archived",
                    "message": f"Ushbu test bo'yicha {attempts_count} ta o'quvchi natijasi mavjudligi sababli, tarixiy natijalar saqlangan holda test arxivlandi."
                }
            else:
                cursor.execute("DELETE FROM test_questions WHERE test_id = ?", (test_id,))
                cursor.execute("DELETE FROM tests WHERE id = ?", (test_id,))
                conn.commit()
                return {
                    "action": "deleted",
                    "message": "Test va uning bog'lanishlari muvaffaqiyatli o'chirildi."
                }
        finally:
            conn.close()

    @staticmethod
    def search_my_test_bank(teacher_id: int, search: str = None, subject_id: int = None, status: str = None):
        """O'qituvchining barcha testlarini qidirish va filtrlash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT t.id, t.title, t.exam_type, t.duration_minutes, t.passing_score,
                       t.status, t.created_at,
                       sub.id as subject_id, sub.name as subject_name, sub.code as subject_code,
                       g.id as group_id, g.name as group_name, ta.id as assignment_id,
                       (SELECT COUNT(*) FROM test_questions WHERE test_id = t.id) as question_count,
                       (SELECT COUNT(*) FROM exam_sessions WHERE test_id = t.id AND status = 'completed') as attempts_count,
                       (SELECT ROUND(AVG(score_percent), 1) FROM exam_sessions WHERE test_id = t.id AND status = 'completed') as avg_score
                FROM tests t
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN groups g ON g.id = ta.group_id
                WHERE ta.teacher_id = ?
            """
            params = [teacher_id]

            if search:
                query += " AND t.title LIKE ?"
                params.append(f"%{search.strip()}%")
            if subject_id:
                query += " AND sub.id = ?"
                params.append(int(subject_id))
            if status:
                normalized = TeacherService._normalize_status(status)
                query += " AND t.status = ?"
                params.append(normalized)

            query += " ORDER BY t.id DESC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

