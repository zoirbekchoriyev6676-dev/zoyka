import random
from database.db import get_db_connection

class TestService:
    # ------------------ GURUHLAR ------------------
    @staticmethod
    def get_all_groups():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id, g.name, g.created_at, COUNT(s.id) as student_count
                FROM groups g
                LEFT JOIN students s ON s.group_id = g.id
                GROUP BY g.id
                ORDER BY g.name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_group(name: str):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO groups (name) VALUES (?)", (name.strip(),))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update_group(group_id: int, name: str):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE groups SET name = ? WHERE id = ?", (name.strip(), group_id))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete_group(group_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM groups WHERE id = ?", (group_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ MAVZULAR ------------------
    @staticmethod
    def get_all_topics():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, t.name, t.description, t.created_at, COUNT(q.id) as question_count
                FROM topics t
                LEFT JOIN questions q ON q.topic_id = t.id
                GROUP BY t.id
                ORDER BY t.name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_topic(name: str, description: str = ""):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("INSERT INTO topics (name, description) VALUES (?, ?)", (name.strip(), description.strip()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    @staticmethod
    def update_topic(topic_id: int, name: str, description: str = ""):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE topics SET name = ?, description = ? WHERE id = ?", (name.strip(), description.strip(), topic_id))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete_topic(topic_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM topics WHERE id = ?", (topic_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ TESTLAR (ENTERPRISE SXEMA MOSLASHUVI) ------------------
    @staticmethod
    def get_all_tests(active_only: bool = False):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT t.id, t.title, t.exam_type, t.duration_minutes, t.passing_score, 
                       t.randomize_questions, t.enable_camera, t.status, t.created_at,
                       t.assignment_id,
                       sub.name as subject_name,
                       g.name as group_name,
                       COUNT(tq.question_id) as question_count
                FROM tests t
                LEFT JOIN teacher_assignments ta ON ta.id = t.assignment_id
                LEFT JOIN subjects sub ON sub.id = ta.subject_id
                LEFT JOIN groups g ON g.id = ta.group_id
                LEFT JOIN test_questions tq ON tq.test_id = t.id
            """
            params = []
            if active_only:
                query += " WHERE LOWER(t.status) IN ('ready', 'started', 'active')"
            query += " GROUP BY t.id ORDER BY t.id DESC"
            cursor.execute(query, params)
            results = []
            for row in cursor.fetchall():
                d = dict(row)
                d["is_active"] = 1 if (d.get("status") or "").lower() not in ("draft", "archived") else 0
                d["description"] = f"{d.get('subject_name') or 'Fan'} - {d.get('group_name') or 'Guruh'}"
                results.append(d)
            return results
        finally:
            conn.close()

    @staticmethod
    def get_test_by_id(test_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.*, sub.name as subject_name, g.name as group_name,
                       COUNT(tq.question_id) as question_count
                FROM tests t
                LEFT JOIN teacher_assignments ta ON ta.id = t.assignment_id
                LEFT JOIN subjects sub ON sub.id = ta.subject_id
                LEFT JOIN groups g ON g.id = ta.group_id
                LEFT JOIN test_questions tq ON tq.test_id = t.id
                WHERE t.id = ?
                GROUP BY t.id
            """, (test_id,))
            row = cursor.fetchone()
            if not row:
                return None
            d = dict(row)
            d["is_active"] = 1 if (d.get("status") or "").lower() not in ("draft", "archived") else 0
            d["description"] = f"{d.get('subject_name') or 'Fan'} - {d.get('group_name') or 'Guruh'}"
            return d
        finally:
            conn.close()

    @staticmethod
    def create_test(title: str, description: str, duration_minutes: int, passing_score: int, is_active: int, randomize_questions: int, assignment_id: int = None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if not assignment_id:
                cursor.execute("SELECT id, group_id FROM teacher_assignments ORDER BY id ASC LIMIT 1")
                assign = cursor.fetchone()
                if assign:
                    assignment_id = assign["id"]
                    group_id = assign["group_id"]
                else:
                    assignment_id = 1
                    group_id = 1
            else:
                cursor.execute("SELECT group_id FROM teacher_assignments WHERE id = ?", (assignment_id,))
                a_row = cursor.fetchone()
                group_id = a_row["group_id"] if a_row else 1

            status_val = "ready" if is_active else "draft"
            cursor.execute("""
                INSERT INTO tests (title, assignment_id, duration_minutes, passing_score, randomize_questions, status)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (title.strip(), assignment_id, duration_minutes, passing_score, randomize_questions, status_val))
            test_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO test_sessions (group_id, test_id, status)
                VALUES (?, ?, ?)
            """, (group_id, test_id, status_val.upper()))

            conn.commit()
            return test_id
        finally:
            conn.close()

    @staticmethod
    def update_test(test_id: int, title: str, description: str, duration_minutes: int, passing_score: int, is_active: int, randomize_questions: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            status_val = "ready" if is_active else "draft"
            cursor.execute("""
                UPDATE tests 
                SET title = ?, duration_minutes = ?, passing_score = ?, randomize_questions = ?, status = ?
                WHERE id = ?
            """, (title.strip(), duration_minutes, passing_score, randomize_questions, status_val, test_id))
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete_test(test_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM tests WHERE id = ?", (test_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ SAVOLLAR VA VARIANTLAR (ENTERPRISE QUESTION_BANK) ------------------
    @staticmethod
    def get_test_questions_for_student(test_id: int):
        """O'quvchi uchun savollar ro'yxati. To'g'ri javob yashiriladi, variantlar va savollar aralashtiriladi."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT randomize_questions FROM tests WHERE id = ?", (test_id,))
            test_row = cursor.fetchone()
            randomize = bool(test_row["randomize_questions"]) if test_row else True

            cursor.execute("""
                SELECT qb.id, qb.question_text, qb.difficulty, qb.points, qb.topic_id, top.name as topic_name
                FROM test_questions tq
                JOIN question_bank qb ON qb.id = tq.question_id
                LEFT JOIN topics top ON top.id = qb.topic_id
                WHERE tq.test_id = ? AND qb.is_active = 1
                ORDER BY qb.id ASC
            """, (test_id,))
            questions = [dict(row) for row in cursor.fetchall()]

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

            return questions
        finally:
            conn.close()

    @staticmethod
    def get_test_questions_for_admin(test_id: int):
        """O'qituvchi/Admin uchun barcha savollar to'g'ri javoblari va izohlari bilan."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT qb.id, qb.question_text, qb.difficulty, qb.points, qb.explanation, qb.created_at,
                       qb.topic_id, top.name as topic_name
                FROM test_questions tq
                JOIN question_bank qb ON qb.id = tq.question_id
                LEFT JOIN topics top ON top.id = qb.topic_id
                WHERE tq.test_id = ?
                ORDER BY qb.id ASC
            """, (test_id,))
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
    def create_question(test_id: int, topic_id: int, question_text: str, difficulty: str, explanation: str, options: list):
        """
        options: [{'option_text': '...', 'is_correct': 1 or 0}, ...]
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT assignment_id FROM tests WHERE id = ?", (test_id,))
            t_row = cursor.fetchone()
            subject_id = 1
            if t_row and t_row["assignment_id"]:
                cursor.execute("SELECT subject_id FROM teacher_assignments WHERE id = ?", (t_row["assignment_id"],))
                s_row = cursor.fetchone()
                if s_row:
                    subject_id = s_row["subject_id"]

            cursor.execute("""
                INSERT INTO question_bank (subject_id, topic_id, question_text, difficulty, points, explanation)
                VALUES (?, ?, ?, ?, 1, ?)
            """, (subject_id, topic_id, question_text.strip(), difficulty, explanation.strip()))
            q_id = cursor.lastrowid

            for opt in options:
                cursor.execute("""
                    INSERT INTO question_options (question_id, option_text, is_correct)
                    VALUES (?, ?, ?)
                """, (q_id, opt["option_text"].strip(), 1 if opt.get("is_correct") else 0))

            cursor.execute("INSERT OR IGNORE INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, q_id))
            conn.commit()
            return q_id
        finally:
            conn.close()

    @staticmethod
    def update_question(question_id: int, topic_id: int, question_text: str, difficulty: str, explanation: str, options: list):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE question_bank
                SET topic_id = ?, question_text = ?, difficulty = ?, explanation = ?
                WHERE id = ?
            """, (topic_id, question_text.strip(), difficulty, explanation.strip(), question_id))

            cursor.execute("DELETE FROM question_options WHERE question_id = ?", (question_id,))
            for opt in options:
                cursor.execute("""
                    INSERT INTO question_options (question_id, option_text, is_correct)
                    VALUES (?, ?, ?)
                """, (question_id, opt["option_text"].strip(), 1 if opt.get("is_correct") else 0))

            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def delete_question(question_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM question_bank WHERE id = ?", (question_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ==================== STATE MACHINE (TEST HAYOT SIKLI) ====================
    VALID_TRANSITIONS = {
        "DRAFT": ["READY"],
        "READY": ["STARTED", "DRAFT"],
        "ACTIVE": ["READY", "STARTED", "FINISHED"],
        "STARTED": ["FINISHED"],
        "FINISHED": ["RESULTS_APPROVED"],
        "RESULTS_APPROVED": ["RESULTS_PUBLISHED"],
        "RESULTS_PUBLISHED": []
    }


    @classmethod
    def get_test_state(cls, test_id: int, group_id: int = None) -> str:
        """Testning joriy holatini olish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            if group_id:
                cursor.execute("""
                    SELECT status FROM test_sessions WHERE test_id = ? AND group_id = ?
                    ORDER BY id DESC LIMIT 1
                """, (test_id, group_id))
                row = cursor.fetchone()
                if row:
                    return row["status"].upper()

            cursor.execute("SELECT status FROM tests WHERE id = ?", (test_id,))
            row = cursor.fetchone()
            if row:
                st = row["status"]
                return st.upper() if st else "DRAFT"
            return "DRAFT"
        finally:
            conn.close()

    @classmethod
    def transition_test_state(
        cls,
        test_id: int,
        target_state: str,
        group_id: int = None,
        user_role: str = "admin",
        user_id: int = None
    ) -> dict:
        """
        Test holatini ruxsat etilgan o'tishlar asosida o'zgartirish.
        DRAFT -> READY -> STARTED -> FINISHED -> RESULTS_APPROVED -> RESULTS_PUBLISHED
        """
        target = target_state.upper()
        current = cls.get_test_state(test_id, group_id)

        # Ruxsat tekshiruvi: faqat Admin START, FINISH, APPROVE, PUBLISH qila oladi
        if target in ("STARTED", "FINISHED", "RESULTS_APPROVED", "RESULTS_PUBLISHED") and user_role != "admin":
            raise PermissionError("Ushbu bosqichga o'tkazish faqat Administratorga ruxsat etilgan")

        # Holat o'tishi ruxsat etilganligini tekshirish
        allowed = cls.VALID_TRANSITIONS.get(current, [])
        if target not in allowed and target != current:
            # Audit logga yozish
            conn = get_db_connection()
            try:
                c = conn.cursor()
                c.execute("""
                    INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                    VALUES (?, 'INVALID_STATE_TRANSITION', 'TEST', ?, ?)
                """, (user_id, test_id, f"Taqiqlangan o'tish urinishi: {current} -> {target}"))
                conn.commit()
            finally:
                conn.close()

            raise ValueError(f"Noto'g'ri holat o'tishi: {current} -> {target}. Ruxsat etilgan: {', '.join(allowed) if allowed else 'Yo`q'}")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # Agar group_id berilmagan bo'lsa, test biriktirilgan guruhni topish
            if not group_id:
                cursor.execute("""
                    SELECT ta.group_id FROM tests t
                    JOIN teacher_assignments ta ON ta.id = t.assignment_id
                    WHERE t.id = ?
                """, (test_id,))
                row = cursor.fetchone()
                if row:
                    group_id = row["group_id"]

            # 1. tests jadvalidagi statusni yangilash
            cursor.execute("UPDATE tests SET status = ? WHERE id = ?", (target.lower(), test_id))

            # 2. test_sessions jadvalini tekshirish va yangilash
            if group_id:
                cursor.execute("""
                    SELECT id FROM test_sessions WHERE test_id = ? AND group_id = ?
                """, (test_id, group_id))
                sess_row = cursor.fetchone()

                now_time = "datetime('now')"
                if not sess_row:
                    cursor.execute(f"""
                        INSERT INTO test_sessions (group_id, test_id, status, started_at, finished_at)
                        VALUES (?, ?, ?, {'datetime("now")' if target == 'STARTED' else 'NULL'}, {'datetime("now")' if target == 'FINISHED' else 'NULL'})
                    """, (group_id, test_id, target))
                else:
                    upd_query = "UPDATE test_sessions SET status = ?"
                    params = [target]
                    if target == "STARTED":
                        upd_query += ", started_at = datetime('now')"
                    elif target == "FINISHED":
                        upd_query += ", finished_at = datetime('now')"
                    upd_query += " WHERE test_id = ? AND group_id = ?"
                    params.extend([test_id, group_id])
                    cursor.execute(upd_query, params)

                # 3. STARTED bo'lganda guruhdagi barcha o'quvchilarni ACTIVE qilish
                if target == "STARTED":
                    cursor.execute("SELECT id FROM students WHERE group_id = ?", (group_id,))
                    st_ids = [r["id"] for r in cursor.fetchall()]
                    for sid in st_ids:
                        cursor.execute("""
                            INSERT INTO student_test_state (student_id, test_id, status)
                            VALUES (?, ?, 'ACTIVE')
                            ON CONFLICT(student_id, test_id) DO UPDATE SET status = 'ACTIVE', block_reason = NULL
                        """, (sid, test_id))

                # 4. FINISHED bo'lganda hali topshirmagan o'quvchilar testini ham yopish
                elif target == "FINISHED":
                    cursor.execute("""
                        UPDATE student_test_state
                        SET status = 'FINISHED'
                        WHERE test_id = ? AND status = 'ACTIVE'
                    """, (test_id,))

            # 5. Audit log
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, 'TEST_STATE_TRANSITION', 'TEST', ?, ?)
            """, (user_id, test_id, f"Test holati o'zgartirildi: {current} -> {target}"))

            conn.commit()
            return {"success": True, "previous_status": current, "current_status": target}
        finally:
            conn.close()

    @classmethod
    def get_group_test_stats(cls, test_id: int, group_id: int = None) -> dict:
        """Admin paneli uchun guruh ko'rsatkichlari (holat, faol soni, yakunlagan soni, bloklanganlar soni)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            status = cls.get_test_state(test_id, group_id)

            if not group_id:
                cursor.execute("""
                    SELECT ta.group_id FROM tests t
                    JOIN teacher_assignments ta ON ta.id = t.assignment_id
                    WHERE t.id = ?
                """, (test_id,))
                r = cursor.fetchone()
                group_id = r["group_id"] if r else None

            total_students = 0
            active_count = 0
            finished_count = 0
            blocked_count = 0

            if group_id:
                cursor.execute("SELECT COUNT(*) as cnt FROM students WHERE group_id = ?", (group_id,))
                total_students = cursor.fetchone()["cnt"]

                cursor.execute("""
                    SELECT status, COUNT(*) as cnt FROM student_test_state
                    WHERE test_id = ?
                    GROUP BY status
                """, (test_id,))
                for row in cursor.fetchall():
                    st = row["status"]
                    if st == "ACTIVE":
                        active_count = row["cnt"]
                    elif st == "FINISHED":
                        finished_count = row["cnt"]
                    elif st == "BLOCKED":
                        blocked_count = row["cnt"]

            return {
                "test_id": test_id,
                "group_id": group_id,
                "status": status,
                "total_students": total_students,
                "active_count": active_count,
                "finished_count": finished_count,
                "blocked_count": blocked_count
            }
        finally:
            conn.close()

    # ==================== TEST NAZORATI (PROCTORING) ====================
    @classmethod
    def get_proctoring_settings(cls, test_id: int) -> dict:
        """Test bo'yicha proctoring sozlamalarini olish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM proctoring_settings WHERE test_id = ?", (test_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            # Standart sozlamalar
            return {
                "test_id": test_id,
                "tab_switch_limit": 3,
                "fullscreen_limit": 3,
                "reload_limit": 3,
                "face_lost_limit": 5,
                "multiple_faces_limit": 2,
                "enable_camera": 0,
                "camera_policy": "allow_without_camera",
                "track_exit": 1,
                "track_suspicious": 1
            }
        finally:
            conn.close()

    @classmethod
    def update_proctoring_settings(cls, test_id: int, settings: dict):
        """Admin tomonidan nazorat sozlamalarini yangilash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO proctoring_settings (
                    test_id, tab_switch_limit, fullscreen_limit, reload_limit,
                    face_lost_limit, multiple_faces_limit, enable_camera, camera_policy,
                    track_exit, track_suspicious
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(test_id) DO UPDATE SET
                    tab_switch_limit = excluded.tab_switch_limit,
                    fullscreen_limit = excluded.fullscreen_limit,
                    reload_limit = excluded.reload_limit,
                    face_lost_limit = excluded.face_lost_limit,
                    multiple_faces_limit = excluded.multiple_faces_limit,
                    enable_camera = excluded.enable_camera,
                    camera_policy = excluded.camera_policy,
                    track_exit = excluded.track_exit,
                    track_suspicious = excluded.track_suspicious
            """, (
                test_id,
                settings.get("tab_switch_limit", 3),
                settings.get("fullscreen_limit", 3),
                settings.get("reload_limit", 3),
                settings.get("face_lost_limit", 5),
                settings.get("multiple_faces_limit", 2),
                1 if settings.get("enable_camera") else 0,
                settings.get("camera_policy", "allow_without_camera"),
                1 if settings.get("track_exit", 1) else 0,
                1 if settings.get("track_suspicious", 1) else 0
            ))
            conn.commit()
            return True
        finally:
            conn.close()

    @classmethod
    def record_proctoring_event(
        cls,
        test_id: int,
        student_id: int,
        event_type: str,
        details: str = "",
        session_id: int = None
    ) -> dict:
        """
        Nazorat hodisasini serverda qayd qilish va limitni tekshirish.
        Limitga yetganda student_test_state holati BLOCKED bo'ladi.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()

            # 1. Hodisalar sonini hisoblash
            cursor.execute("""
                SELECT COUNT(*) as cnt FROM proctoring_events
                WHERE test_id = ? AND student_id = ? AND event_type = ?
            """, (test_id, student_id, event_type))
            current_count = cursor.fetchone()["cnt"] + 1

            # 2. Hodisani yozish
            cursor.execute("""
                INSERT INTO proctoring_events (session_id, student_id, test_id, event_type, details, counter)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (session_id, student_id, test_id, event_type, details, current_count))

            # 3. Sozlamalar va limitni tekshirish
            settings = cls.get_proctoring_settings(test_id)
            limit = 3
            if event_type == "tab_switch":
                limit = settings.get("tab_switch_limit", 3)
            elif event_type == "fullscreen_exit":
                limit = settings.get("fullscreen_limit", 3)
            elif event_type == "reload":
                limit = settings.get("reload_limit", 3)
            elif event_type == "face_lost":
                limit = settings.get("face_lost_limit", 5)
            elif event_type == "multiple_faces":
                limit = settings.get("multiple_faces_limit", 2)

            is_blocked = (current_count >= limit)
            status = "BLOCKED" if is_blocked else "ACTIVE"

            message = ""
            if is_blocked:
                message = f"🔒 TEST BLOKLANDI: test oynasidan ruxsatsiz chiqish belgilangan chegaraga yetdi ({current_count}/{limit}). Administrator qarorini kuting."
                # Bazada o'quvchi holatini BLOCKED ga o'tkazish
                cursor.execute("""
                    INSERT INTO student_test_state (student_id, test_id, status, block_reason, blocked_at)
                    VALUES (?, ?, 'BLOCKED', ?, datetime('now'))
                    ON CONFLICT(student_id, test_id) DO UPDATE SET
                        status = 'BLOCKED',
                        block_reason = excluded.block_reason,
                        blocked_at = datetime('now')
                """, (student_id, test_id, f"{event_type}: {current_count}"))
            else:
                if current_count == 1:
                    message = "⚠️ Ogohlantirish: siz test oynasidan chiqdingiz. Bu holat qayd qilindi."
                elif current_count == 2:
                    message = "⚠️ DIQQAT: test oynasidan yana chiqdingiz. Keyingi holatda test bloklanishi mumkin."
                else:
                    message = f"⚠️ Ogohlantirish qayd etildi ({current_count}/{limit})."

            conn.commit()
            return {
                "status": status,
                "student_state": status,
                "event_type": event_type,
                "counter": current_count,
                "current_count": current_count,
                "limit": limit,
                "message": message,
                "is_blocked": is_blocked
            }
        finally:
            conn.close()

    @classmethod
    def resume_student(cls, student_id: int, test_id: int, admin_user_id: int = None) -> bool:
        """Admin qarori: Bloklangan o'quvchini davom ettirish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE student_test_state
                SET status = 'ACTIVE', block_reason = NULL, updated_at = datetime('now')
                WHERE student_id = ? AND test_id = ?
            """, (student_id, test_id))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, 'RESUME_STUDENT', 'STUDENT', ?, ?)
            """, (admin_user_id, student_id, f"O'quvchi {test_id}-test bo'yicha blokdan chiqarildi"))

            conn.commit()
            return True
        finally:
            conn.close()

    @classmethod
    def terminate_student(cls, student_id: int, test_id: int, admin_user_id: int = None) -> bool:
        """Admin qarori: Bloklangan o'quvchining testini yakunlash."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE student_test_state
                SET status = 'FINISHED', updated_at = datetime('now')
                WHERE student_id = ? AND test_id = ?
            """, (student_id, test_id))

            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, 'TERMINATE_STUDENT', 'STUDENT', ?, ?)
            """, (admin_user_id, student_id, f"O'quvchining {test_id}-testi admin tomonidan yakunlandi"))

            conn.commit()
            return True
        finally:
            conn.close()

    @classmethod
    def get_proctoring_dashboard(cls, test_id: int) -> list:
        """
        Admin paneli uchun testda qatnashayotgan o'quvchilar va ularning nazorat hodisalari.
        Barcha o'quvchilarni emas, aynan ushbu test biriktirilgan guruhlar yoki test holati mavjud
        o'quvchilarni filtrlaydi va hodisalarni bitta so'rovda hisoblaydi (performance boost).
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                WITH test_students AS (
                    -- Testga ruxsat berilgan yoki test topshirayotgan o'quvchilar
                    SELECT DISTINCT s.id as student_id, u.full_name as student_name, s.student_code,
                           COALESCE(sts.status, 'ACTIVE') as test_state,
                           sts.block_reason
                    FROM students s
                    JOIN users u ON u.id = s.user_id
                    LEFT JOIN student_test_state sts ON sts.student_id = s.id AND sts.test_id = ?
                    WHERE s.group_id IN (
                        SELECT group_id FROM test_groups_access WHERE test_id = ?
                        UNION
                        SELECT ta.group_id FROM tests t 
                        JOIN teacher_assignments ta ON ta.id = t.assignment_id 
                        WHERE t.id = ?
                    ) OR sts.id IS NOT NULL
                ),
                events_agg AS (
                    SELECT student_id,
                           SUM(CASE WHEN event_type = 'tab_switch' THEN 1 ELSE 0 END) as tab_switches,
                           SUM(CASE WHEN event_type = 'fullscreen_exit' THEN 1 ELSE 0 END) as fullscreen_exits,
                           SUM(CASE WHEN event_type = 'reload' THEN 1 ELSE 0 END) as reloads,
                           SUM(CASE WHEN event_type = 'face_lost' THEN 1 ELSE 0 END) as face_losts,
                           SUM(CASE WHEN event_type = 'multiple_faces' THEN 1 ELSE 0 END) as multiple_faces
                    FROM proctoring_events
                    WHERE test_id = ?
                    GROUP BY student_id
                )
                SELECT ts.student_id, ts.student_name, ts.student_code,
                       ts.test_state, ts.block_reason,
                       COALESCE(ea.tab_switches, 0) as tab_switches,
                       COALESCE(ea.fullscreen_exits, 0) as fullscreen_exits,
                       COALESCE(ea.reloads, 0) as reloads,
                       COALESCE(ea.face_losts, 0) as face_losts,
                       COALESCE(ea.multiple_faces, 0) as multiple_faces
                FROM test_students ts
                LEFT JOIN events_agg ea ON ea.student_id = ts.student_id
                ORDER BY ts.student_name ASC
            """, (test_id, test_id, test_id, test_id))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    # ==================== GURUHLAR KESIMIDA TESTGA RUXSAT VA YAKUNLASH ====================
    @classmethod
    def grant_test_access_to_groups(cls, test_id: int, group_ids: list, user_id: int = None) -> dict:
        """
        Admin/O'qituvchi tanlangan guruhlar uchun testni boshlaydi (status='active').
        """
        if not group_ids:
            raise ValueError("Kamida bitta guruh tanlanishi kerak")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM tests WHERE id = ?", (test_id,))
            t_row = cursor.fetchone()
            if not t_row:
                raise ValueError("Test topilmadi")

            # tests jadvalini 'active' qilish
            cursor.execute("UPDATE tests SET status = 'active' WHERE id = ?", (test_id,))

            activated_groups = []
            for gid in group_ids:
                gid = int(gid)
                # test_groups_access ni yangilash yoki kiritish
                cursor.execute("SELECT id FROM test_groups_access WHERE test_id = ? AND group_id = ?", (test_id, gid))
                tga_row = cursor.fetchone()
                if tga_row:
                    cursor.execute("""
                        UPDATE test_groups_access
                        SET status = 'active', start_time = datetime('now'), end_time = NULL, is_results_announced = 0
                        WHERE id = ?
                    """, (tga_row["id"],))
                else:
                    cursor.execute("""
                        INSERT INTO test_groups_access (test_id, group_id, status, start_time, end_time, is_results_announced)
                        VALUES (?, ?, 'active', datetime('now'), NULL, 0)
                    """, (test_id, gid))

                # test_sessions moslash
                cursor.execute("SELECT id FROM test_sessions WHERE test_id = ? AND group_id = ?", (test_id, gid))
                ts_row = cursor.fetchone()
                if ts_row:
                    cursor.execute("""
                        UPDATE test_sessions
                        SET status = 'STARTED', started_at = datetime('now')
                        WHERE id = ?
                    """, (ts_row["id"],))
                else:
                    cursor.execute("""
                        INSERT INTO test_sessions (group_id, test_id, status, started_at)
                        VALUES (?, ?, 'STARTED', datetime('now'))
                    """, (gid, test_id))

                # groups jadvalidagi statusni ham moslash (Bot uchun 'ongoing')
                cursor.execute("UPDATE groups SET status = 'ongoing' WHERE id = ?", (gid,))

                # Guruhdagi barcha o'quvchilarni ACTIVE qilish
                cursor.execute("SELECT id FROM students WHERE group_id = ?", (gid,))
                st_ids = [r["id"] for r in cursor.fetchall()]
                for sid in st_ids:
                    cursor.execute("SELECT id FROM student_test_state WHERE student_id = ? AND test_id = ?", (sid, test_id))
                    state_row = cursor.fetchone()
                    if state_row:
                        cursor.execute("""
                            UPDATE student_test_state
                            SET status = 'ACTIVE', block_reason = NULL
                            WHERE id = ?
                        """, (state_row["id"],))
                    else:
                        cursor.execute("""
                            INSERT INTO student_test_state (student_id, test_id, status)
                            VALUES (?, ?, 'ACTIVE')
                        """, (sid, test_id))

                activated_groups.append(gid)

            # Audit log
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, 'GRANT_GROUP_ACCESS', 'TEST', ?, ?)
            """, (user_id, test_id, f"Test {test_id} guruhlar uchun boshlandi: {activated_groups}"))

            conn.commit()
            return {
                "success": True,
                "test_id": test_id,
                "message": f"Test {len(activated_groups)} ta guruh uchun muvaffaqiyatli boshlandi",
                "activated_groups": activated_groups
            }
        finally:
            conn.close()

    grant_group_access = grant_test_access_to_groups

    @classmethod
    def stop_test_access_for_groups(cls, test_id: int, group_ids: list, user_id: int = None) -> dict:
        """
        Admin/O'qituvchi testni to'xtatadi (status='completed'), end_time belgilaydi
        va natijalarni e'lon qiladi (is_results_announced=1).
        """
        if not group_ids:
            raise ValueError("Kamida bitta guruh tanlanishi kerak")

        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, title FROM tests WHERE id = ?", (test_id,))
            t_row = cursor.fetchone()
            if not t_row:
                raise ValueError("Test topilmadi")

            stopped_groups = []
            for gid in group_ids:
                gid = int(gid)
                cursor.execute("SELECT id FROM test_groups_access WHERE test_id = ? AND group_id = ?", (test_id, gid))
                tga_row = cursor.fetchone()
                if tga_row:
                    cursor.execute("""
                        UPDATE test_groups_access
                        SET status = 'completed', end_time = datetime('now'), is_results_announced = 1
                        WHERE id = ?
                    """, (tga_row["id"],))
                else:
                    cursor.execute("""
                        INSERT INTO test_groups_access (test_id, group_id, status, end_time, is_results_announced)
                        VALUES (?, ?, 'completed', datetime('now'), 1)
                    """, (test_id, gid))

                # test_sessions moslash
                cursor.execute("""
                    UPDATE test_sessions
                    SET status = 'RESULTS_PUBLISHED', finished_at = datetime('now')
                    WHERE test_id = ? AND group_id = ?
                """, (test_id, gid))

                # Guruhdagi hali topshirmagan o'quvchilar testini yopish
                cursor.execute("SELECT id FROM students WHERE group_id = ?", (gid,))
                st_ids = [r["id"] for r in cursor.fetchall()]
                for sid in st_ids:
                    cursor.execute("""
                        UPDATE student_test_state
                        SET status = 'FINISHED'
                        WHERE student_id = ? AND test_id = ? AND status = 'ACTIVE'
                    """, (sid, test_id))

                # groups jadvalidagi statusni 'published' qilish (Bot talabi bo'yicha)
                cursor.execute("UPDATE groups SET status = 'published' WHERE id = ?", (gid,))

                # Bot uchun 'results' jadvalini avtomatik sinxronlash (SELECT student_name, score FROM results WHERE group_id = gid)
                cursor.execute("""
                    DELETE FROM results WHERE group_id = ?
                """, (gid,))
                cursor.execute("""
                    INSERT INTO results (group_id, student_name, score)
                    SELECT st.group_id, u.full_name, MAX(es.score_percent)
                    FROM exam_sessions es
                    JOIN students st ON st.id = es.student_id
                    JOIN users u ON u.id = st.user_id
                    WHERE st.group_id = ? AND es.test_id = ? AND es.status = 'completed'
                    GROUP BY st.id
                """, (gid, test_id))

                stopped_groups.append(gid)

            # Agar bu testning barcha guruhlari completed bo'lsa, tests jadvalini ham 'finished' va 'is_results_announced'=1 qilish
            cursor.execute("""
                SELECT COUNT(*) as active_cnt FROM test_groups_access
                WHERE test_id = ? AND status = 'active'
            """, (test_id,))
            if cursor.fetchone()["active_cnt"] == 0:
                cursor.execute("UPDATE tests SET status = 'finished', is_results_announced = 1 WHERE id = ?", (test_id,))

            # Audit log
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, 'STOP_GROUP_ACCESS', 'TEST', ?, ?)
            """, (user_id, test_id, f"Test {test_id} guruhlar uchun yakunlandi va natijalar e'lon qilindi: {stopped_groups}"))

            conn.commit()
            return {
                "success": True,
                "test_id": test_id,
                "message": f"Test {len(stopped_groups)} ta guruh uchun yakunlandi va natijalar e'lon qilindi",
                "stopped_groups": stopped_groups,
                "is_results_announced": True
            }
        finally:
            conn.close()

    stop_group_access = stop_test_access_for_groups

    @classmethod
    def get_test_groups_access(cls, test_id: int) -> list:
        """Test bo'yicha barcha guruhlar va ularning joriy ruxsat holatlari."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id as group_id, g.name as group_name, g.academic_year,
                       tga.id as access_id,
                       COALESCE(tga.status, 'pending') as status,
                       tga.start_time, tga.end_time,
                       COALESCE(tga.is_results_announced, 0) as is_results_announced,
                       (SELECT COUNT(*) FROM students WHERE group_id = g.id) as student_count,
                       (SELECT COUNT(*) FROM exam_sessions es 
                        JOIN students s ON s.id = es.student_id 
                        WHERE es.test_id = ? AND s.group_id = g.id AND es.status = 'completed') as completed_count
                FROM groups g
                LEFT JOIN test_groups_access tga ON tga.group_id = g.id AND tga.test_id = ?
                ORDER BY g.name ASC
            """, (test_id, test_id))
            return [dict(r) for r in cursor.fetchall()]
        finally:
            conn.close()

    @classmethod
    def check_student_access(cls, student_id: int, test_id: int) -> dict:
        """Talaba uchun test ochiq yoki yo'qligini tekshirish."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT group_id FROM students WHERE id = ?", (student_id,))
            st = cursor.fetchone()
            if not st:
                return {"allowed": False, "reason": "O'quvchi ma'lumotlari topilmadi", "status": "unknown"}

            group_id = st["group_id"]

            # 1. State Machine (test_sessions) tekshiruvi
            cursor.execute("""
                SELECT status FROM test_sessions
                WHERE test_id = ? AND group_id = ?
            """, (test_id, group_id))
            ts = cursor.fetchone()
            if ts:
                sm_status = (ts["status"] or "DRAFT").upper()
                if sm_status in ("DRAFT", "READY"):
                    return {"allowed": False, "reason": "Test hali boshlanmagan (Kutish rejimida). Administrator yoki o'qituvchi ruxsatini kuting.", "status": sm_status}
                elif sm_status in ("FINISHED", "RESULTS_PUBLISHED"):
                    return {"allowed": False, "reason": "Test yakunlangan.", "status": sm_status}

            cursor.execute("""
                SELECT status, is_results_announced FROM test_groups_access
                WHERE test_id = ? AND group_id = ?
            """, (test_id, group_id))
            acc = cursor.fetchone()

            if acc:
                status = acc["status"]
                is_announced = bool(acc["is_results_announced"])
                if status == "active":
                    return {"allowed": True, "status": "active", "group_id": group_id, "is_results_announced": is_announced}
                elif status == "completed":
                    return {"allowed": False, "reason": "Test guruhingiz uchun yakunlangan.", "status": "completed", "group_id": group_id, "is_results_announced": is_announced}
                else:
                    return {"allowed": False, "reason": "Ushbu test guruhingiz uchun hali boshlanmadi. Administrator yoki o'qituvchi ruxsatini kuting.", "status": "pending", "group_id": group_id, "is_results_announced": is_announced}

            # test_groups_access da yozuv bo'lmasa: umumiy test holati
            cursor.execute("SELECT status FROM tests WHERE id = ?", (test_id,))
            t_row = cursor.fetchone()
            t_status = (t_row["status"] or "draft").lower() if t_row else "draft"
            if t_status in ("active", "started"):
                return {"allowed": True, "status": "active", "group_id": group_id, "is_results_announced": False}
            elif t_status in ("finished", "results_published"):
                return {"allowed": False, "reason": "Test yakunlangan.", "status": "completed", "group_id": group_id, "is_results_announced": True}
            else:
                return {"allowed": False, "reason": "Ushbu test guruhingiz uchun hali boshlanmadi. Administrator yoki o'qituvchi ruxsatini kuting.", "status": "pending", "group_id": group_id, "is_results_announced": False}
        finally:
            conn.close()

