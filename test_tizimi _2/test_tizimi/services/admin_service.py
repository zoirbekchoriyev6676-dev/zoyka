from database.db import get_db_connection
from core.security import hash_password

class AdminService:
    @staticmethod
    def get_dashboard_stats():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) as count FROM students")
            total_students = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM teachers")
            total_teachers = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM subjects WHERE is_active = 1")
            total_subjects = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM groups WHERE is_active = 1")
            total_groups = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count FROM tests WHERE status = 'active'")
            active_tests = cursor.fetchone()["count"]

            cursor.execute("SELECT COUNT(*) as count, ROUND(AVG(score_percent), 1) as avg_score FROM exam_sessions WHERE status = 'completed'")
            session_stats = cursor.fetchone()
            total_attempts = session_stats["count"]
            avg_score = session_stats["avg_score"] or 0.0

            # So'nggi 8 ta topshirilgan imtihon
            cursor.execute("""
                SELECT s.id, u.full_name as student_name, g.name as group_name,
                       sub.name as subject_name, t.title as test_title,
                       s.score_percent, s.finished_at
                FROM exam_sessions s
                JOIN students st ON st.id = s.student_id
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                JOIN tests t ON t.id = s.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                WHERE s.status = 'completed'
                ORDER BY s.id DESC LIMIT 8
            """)
            recent_attempts = [dict(row) for row in cursor.fetchall()]

            # Fanlar bo'yicha o'rtacha ballar
            cursor.execute("""
                SELECT sub.name as subject_name, 
                       COUNT(s.id) as attempts_count,
                       ROUND(AVG(s.score_percent), 1) as avg_score
                FROM exam_sessions s
                JOIN tests t ON t.id = s.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                WHERE s.status = 'completed'
                GROUP BY sub.id
                ORDER BY avg_score DESC
            """)
            subject_analytics = [dict(row) for row in cursor.fetchall()]

            return {
                "total_students": total_students,
                "total_teachers": total_teachers,
                "total_subjects": total_subjects,
                "total_groups": total_groups,
                "active_tests": active_tests,
                "total_attempts": total_attempts,
                "avg_score": avg_score,
                "recent_attempts": recent_attempts,
                "subject_analytics": subject_analytics
            }
        finally:
            conn.close()

    # ------------------ O'QITUVCHILAR (TEACHERS) ------------------
    @staticmethod
    def get_teachers():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id, u.id as user_id, u.username, u.full_name, u.phone, u.is_active, 
                       t.specialty, u.created_at,
                       (SELECT COUNT(*) FROM teacher_assignments WHERE teacher_id = t.id) as assignment_count
                FROM teachers t
                JOIN users u ON u.id = t.user_id
                ORDER BY u.full_name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_teacher(full_name: str, username: str, password: str, specialty: str = "", phone: str = ""):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            pw_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone)
                VALUES (?, ?, 'teacher', ?, ?)
            """, (username.strip(), pw_hash, full_name.strip(), phone.strip()))
            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO teachers (user_id, specialty)
                VALUES (?, ?)
            """, (user_id, specialty.strip()))
            teacher_id = cursor.lastrowid

            AdminService.log_audit(user_id=1, action="CREATE_TEACHER", target_type="TEACHER", target_id=teacher_id, details=f"Yangi o'qituvchi: {full_name}", cursor=cursor)
            conn.commit()
            return teacher_id
        finally:
            conn.close()

    @staticmethod
    def toggle_user_active(user_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("UPDATE users SET is_active = CASE WHEN is_active = 1 THEN 0 ELSE 1 END WHERE id = ?", (user_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ O'QUVCHILAR (STUDENTS) ------------------
    @staticmethod
    def get_students(group_id: int = None, search: str = None):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            query = """
                SELECT st.id, u.id as user_id, u.username, u.full_name, u.phone, u.is_active,
                       st.student_code, st.pin, st.group_id, g.name as group_name,
                       (SELECT COUNT(*) FROM exam_sessions WHERE student_id = st.id AND status = 'completed') as exam_count
                FROM students st
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                WHERE 1=1
            """
            params = []
            if group_id:
                query += " AND st.group_id = ?"
                params.append(group_id)
            if search:
                query += " AND (u.full_name LIKE ? OR st.student_code LIKE ?)"
                params.extend([f"%{search}%", f"%{search}%"])
            query += " ORDER BY g.name ASC, u.full_name ASC"
            cursor.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_student(full_name: str, username: str, password: str, group_id: int, student_code: str, pin: str, phone: str = ""):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            pw_hash = hash_password(password)
            cursor.execute("""
                INSERT INTO users (username, password_hash, role, full_name, phone)
                VALUES (?, ?, 'student', ?, ?)
            """, (username.strip(), pw_hash, full_name.strip(), phone.strip()))
            user_id = cursor.lastrowid

            cursor.execute("""
                INSERT INTO students (user_id, group_id, student_code, pin)
                VALUES (?, ?, ?, ?)
            """, (user_id, group_id, student_code.strip(), pin.strip()))
            student_id = cursor.lastrowid

            AdminService.log_audit(user_id=1, action="CREATE_STUDENT", target_type="STUDENT", target_id=student_id, details=f"Yangi o'quvchi: {full_name} ({student_code})", cursor=cursor)
            conn.commit()
            return student_id
        finally:
            conn.close()

    # ------------------ FANLAR (SUBJECTS) ------------------
    @staticmethod
    def get_subjects():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT s.id, s.name, s.code, s.description, s.is_active,
                       (SELECT COUNT(*) FROM topics WHERE subject_id = s.id) as topic_count,
                       (SELECT COUNT(*) FROM question_bank WHERE subject_id = s.id) as question_count
                FROM subjects s
                ORDER BY s.name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_subject(name: str, code: str, description: str = ""):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO subjects (name, code, description)
                VALUES (?, ?, ?)
            """, (name.strip(), code.strip().upper(), description.strip()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    # ------------------ GURUHLAR (GROUPS) ------------------
    @staticmethod
    def get_groups():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id, g.name, g.academic_year, g.is_active,
                       (SELECT COUNT(*) FROM students WHERE group_id = g.id) as student_count
                FROM groups g
                ORDER BY g.name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_group(name: str, academic_year: str = "2026/2027"):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO groups (name, academic_year)
                VALUES (?, ?)
            """, (name.strip(), academic_year.strip()))
            conn.commit()
            return cursor.lastrowid
        finally:
            conn.close()

    # ------------------ BIRIKTIRISHLAR (TEACHER ASSIGNMENTS) ------------------
    @staticmethod
    def get_assignments():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT ta.id, ta.teacher_id, ta.subject_id, ta.group_id, ta.academic_year, ta.semester, ta.is_active,
                       u.full_name as teacher_name, sub.name as subject_name, sub.code as subject_code,
                       g.name as group_name,
                       (SELECT COUNT(*) FROM tests WHERE assignment_id = ta.id) as test_count
                FROM teacher_assignments ta
                JOIN teachers t ON t.id = ta.teacher_id
                JOIN users u ON u.id = t.user_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN groups g ON g.id = ta.group_id
                ORDER BY u.full_name ASC, sub.name ASC, g.name ASC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def create_assignment(teacher_id: int, subject_id: int, group_id: int, academic_year: str = "2026/2027", semester: int = 1):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO teacher_assignments (teacher_id, subject_id, group_id, academic_year, semester)
                VALUES (?, ?, ?, ?, ?)
            """, (teacher_id, subject_id, group_id, academic_year.strip(), semester))
            assign_id = cursor.lastrowid
            AdminService.log_audit(user_id=1, action="CREATE_ASSIGNMENT", target_type="ASSIGNMENT", target_id=assign_id, details=f"O'qituvchi ID {teacher_id} -> Fan ID {subject_id} -> Guruh ID {group_id}", cursor=cursor)
            conn.commit()
            return assign_id
        finally:
            conn.close()

    @staticmethod
    def delete_assignment(assignment_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("DELETE FROM teacher_assignments WHERE id = ?", (assignment_id,))
            conn.commit()
            return True
        finally:
            conn.close()

    # ------------------ AUDIT LOGS ------------------
    @staticmethod
    def log_audit(user_id: int, action: str, target_type: str = "", target_id: int = None, details: str = "", cursor = None):
        if cursor is not None:
            cursor.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, target_type, target_id, details))
            return

        conn = get_db_connection()
        try:
            cur = conn.cursor()
            cur.execute("""
                INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
                VALUES (?, ?, ?, ?, ?)
            """, (user_id, action, target_type, target_id, details))
            conn.commit()
        finally:
            conn.close()

    @staticmethod
    def get_audit_logs(limit: int = 50):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT al.id, al.user_id, al.action, al.target_type, al.target_id, al.details, al.created_at,
                       u.full_name as user_name, u.role as user_role
                FROM audit_logs al
                LEFT JOIN users u ON u.id = al.user_id
                ORDER BY al.id DESC LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    # ------------------ KENGAYTIRILGAN O'QUVCHILAR BOSHQARUVI ------------------
    @staticmethod
    def get_groups_with_stats():
        """Barcha guruhlar va ularning batafsil statistikasi."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT g.id, g.name, g.academic_year, g.is_active,
                       (SELECT COUNT(*) FROM students WHERE group_id = g.id) as student_count,
                       (SELECT COUNT(*) FROM students st JOIN users u ON u.id = st.user_id WHERE st.group_id = g.id AND u.is_active = 1) as active_students,
                       (SELECT COUNT(DISTINCT es.student_id) FROM exam_sessions es JOIN students st ON st.id = es.student_id WHERE st.group_id = g.id AND es.status = 'completed') as tested_students,
                       (SELECT ROUND(AVG(es.score_percent), 1) FROM exam_sessions es JOIN students st ON st.id = es.student_id WHERE st.group_id = g.id AND es.status = 'completed') as avg_score,
                       (SELECT ROUND(MAX(es.score_percent), 1) FROM exam_sessions es JOIN students st ON st.id = es.student_id WHERE st.group_id = g.id AND es.status = 'completed') as max_score,
                       (SELECT ROUND(MIN(es.score_percent), 1) FROM exam_sessions es JOIN students st ON st.id = es.student_id WHERE st.group_id = g.id AND es.status = 'completed') as min_score
                FROM groups g
                ORDER BY g.name ASC
            """)
            groups = [dict(row) for row in cursor.fetchall()]
            for g in groups:
                if g["avg_score"] is None:
                    g["avg_score"] = 0.0
                if g["max_score"] is None:
                    g["max_score"] = 0.0
                if g["min_score"] is None:
                    g["min_score"] = 0.0
            return groups
        finally:
            conn.close()

    @staticmethod
    def get_group_detail(group_id: int):
        """Bitta guruh ichidagi o'quvchilar ro'yxati va umumiy statistika."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, academic_year, is_active FROM groups WHERE id = ?", (group_id,))
            group_row = cursor.fetchone()
            if not group_row:
                return None

            group_data = dict(group_row)

            # Guruh o'quvchilari
            cursor.execute("""
                SELECT st.id, st.user_id, u.full_name, u.username, u.phone, u.is_active,
                       st.student_code, st.pin, st.group_id, g.name as group_name,
                       (SELECT COUNT(*) FROM exam_sessions WHERE student_id = st.id AND status = 'completed') as exam_count,
                       (SELECT ROUND(AVG(score_percent), 1) FROM exam_sessions WHERE student_id = st.id AND status = 'completed') as avg_score
                FROM students st
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                WHERE st.group_id = ?
                ORDER BY u.full_name ASC
            """, (group_id,))
            students = [dict(row) for row in cursor.fetchall()]

            student_count = len(students)
            active_count = sum(1 for s in students if s["is_active"] == 1)
            tested_count = sum(1 for s in students if (s.get("exam_count") or 0) > 0)
            avg_scores = [s["avg_score"] for s in students if s["avg_score"] is not None]
            group_avg = round(sum(avg_scores) / len(avg_scores), 1) if avg_scores else 0.0
            group_max = max(avg_scores) if avg_scores else 0.0
            group_min = min(avg_scores) if avg_scores else 0.0

            group_data["students"] = students
            group_data["student_count"] = student_count
            group_data["active_students"] = active_count
            group_data["tested_students"] = tested_count
            group_data["avg_score"] = group_avg
            group_data["max_score"] = group_max
            group_data["min_score"] = group_min

            return group_data
        finally:
            conn.close()

    @staticmethod
    def update_student(student_id: int, full_name: str = None, username: str = None,
                       group_id: int = None, student_code: str = None, pin: str = None,
                       phone: str = None, password: str = None, is_active: int = None):
        """O'quvchi ma'lumotlarini tahrirlash (ism, guruh, login, PIN, parol, holat)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT user_id, group_id, student_code, pin FROM students WHERE id = ?", (student_id,))
            st_row = cursor.fetchone()
            if not st_row:
                raise ValueError("O'quvchi topilmadi")

            user_id = st_row["user_id"]

            user_updates = []
            user_params = []
            if full_name is not None:
                user_updates.append("full_name = ?")
                user_params.append(full_name.strip())
            if username is not None:
                user_updates.append("username = ?")
                user_params.append(username.strip())
            if phone is not None:
                user_updates.append("phone = ?")
                user_params.append(phone.strip())
            if is_active is not None:
                user_updates.append("is_active = ?")
                user_params.append(1 if is_active else 0)
            if password is not None and password.strip():
                user_updates.append("password_hash = ?")
                user_params.append(hash_password(password.strip()))

            if user_updates:
                user_params.append(user_id)
                cursor.execute(f"UPDATE users SET {', '.join(user_updates)} WHERE id = ?", user_params)

            st_updates = []
            st_params = []
            if group_id is not None:
                st_updates.append("group_id = ?")
                st_params.append(int(group_id))
            if student_code is not None:
                st_updates.append("student_code = ?")
                st_params.append(student_code.strip())
            if pin is not None:
                st_updates.append("pin = ?")
                st_params.append(pin.strip())

            if st_updates:
                st_params.append(student_id)
                cursor.execute(f"UPDATE students SET {', '.join(st_updates)} WHERE id = ?", st_params)

            AdminService.log_audit(user_id=1, action="UPDATE_STUDENT", target_type="STUDENT", target_id=student_id, details=f"O'quvchi ID {student_id} ma'lumotlari yangilandi", cursor=cursor)
            conn.commit()
            return True
        finally:
            conn.close()

    @staticmethod
    def search_students_global(search_query: str, limit: int = 25):
        """Admin uchun umumiy o'quvchi qidiruv (ism, familiya, login, student ID)."""
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            q = f"%{search_query.strip()}%"
            cursor.execute("""
                SELECT st.id as student_id, st.user_id, u.full_name, u.username, u.phone, u.is_active,
                       st.student_code, st.pin, st.group_id, g.name as group_name,
                       (SELECT COUNT(*) FROM exam_sessions WHERE student_id = st.id AND status = 'completed') as exam_count,
                       (SELECT ROUND(score_percent, 1) FROM exam_sessions WHERE student_id = st.id AND status = 'completed' ORDER BY id DESC LIMIT 1) as last_exam_score,
                       (SELECT t.title FROM exam_sessions es JOIN tests t ON t.id = es.test_id WHERE es.student_id = st.id AND es.status = 'completed' ORDER BY es.id DESC LIMIT 1) as last_exam_title
                FROM students st
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                WHERE u.full_name LIKE ? OR u.username LIKE ? OR st.student_code LIKE ?
                ORDER BY u.full_name ASC
                LIMIT ?
            """, (q, q, q, limit))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_student_profile(student_id: int):
        """
        O'quvchi profili: Shaxsiy ma'lumotlar, fanlar bo'yicha o'zlashtirish,
        so'nggi natijalar, to'liq test tarixi, trend nuqtalari va AI xulosa.
        """
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT st.id, st.user_id, u.full_name, u.username, u.phone, u.is_active, u.created_at as registered_at,
                       st.student_code, st.pin, st.group_id, g.name as group_name
                FROM students st
                JOIN users u ON u.id = st.user_id
                JOIN groups g ON g.id = st.group_id
                WHERE st.id = ?
            """, (student_id,))
            student_row = cursor.fetchone()
            if not student_row:
                return None

            profile = dict(student_row)

            # Barcha topshirilgan imtihonlar tarixi
            cursor.execute("""
                SELECT es.id as session_id, es.test_id, t.title as test_title, t.exam_type,
                       sub.id as subject_id, sub.name as subject_name, sub.code as subject_code,
                       teach_u.full_name as teacher_name,
                       es.score_percent, es.correct_answers, es.total_questions, es.tab_switch_count,
                       es.time_spent_seconds, es.ai_analysis, es.finished_at, es.started_at
                FROM exam_sessions es
                JOIN tests t ON t.id = es.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                JOIN teachers teach ON teach.id = ta.teacher_id
                JOIN users teach_u ON teach_u.id = teach.user_id
                WHERE es.student_id = ? AND es.status = 'completed'
                ORDER BY es.id DESC
            """, (student_id,))
            sessions = [dict(row) for row in cursor.fetchall()]

            # Umumiy statistika
            total_exams = len(sessions)
            scores = [s["score_percent"] for s in sessions]
            overall_avg = round(sum(scores) / total_exams, 1) if total_exams > 0 else 0.0
            highest_score = round(max(scores), 1) if total_exams > 0 else 0.0
            lowest_score = round(min(scores), 1) if total_exams > 0 else 0.0
            passed_exams = sum(1 for s in scores if s >= 60.0)

            # Fanlar bo'yicha o'zlashtirish (Matematika 84%, Fizika 72%...)
            cursor.execute("""
                SELECT sub.id as subject_id, sub.name as subject_name, sub.code as subject_code,
                       COUNT(es.id) as exam_count,
                       ROUND(AVG(es.score_percent), 1) as avg_score,
                       ROUND(MAX(es.score_percent), 1) as max_score
                FROM exam_sessions es
                JOIN tests t ON t.id = es.test_id
                JOIN teacher_assignments ta ON ta.id = t.assignment_id
                JOIN subjects sub ON sub.id = ta.subject_id
                WHERE es.student_id = ? AND es.status = 'completed'
                GROUP BY sub.id
                ORDER BY avg_score DESC
            """, (student_id,))
            subject_stats = [dict(row) for row in cursor.fetchall()]

            # O'quvchi natijasi trendi (Ketma-ketlik bo'yicha)
            # Eng eskisidan yangisiga qarab tartiblaymiz
            trend_list = []
            for idx, s in enumerate(reversed(sessions), 1):
                trend_list.append({
                    "step": idx,
                    "test_title": s["test_title"],
                    "subject_name": s["subject_name"],
                    "score": s["score_percent"],
                    "date": str(s["finished_at"])[:10] if s["finished_at"] else ""
                })

            # AI xulosa (eng so'nggi sessiyadan yoki mavjud bo'lganidan)
            latest_ai = None
            for s in sessions:
                if s.get("ai_analysis"):
                    latest_ai = s["ai_analysis"]
                    break

            profile["stats"] = {
                "total_exams": total_exams,
                "overall_avg": overall_avg,
                "highest_score": highest_score,
                "lowest_score": lowest_score,
                "passed_exams": passed_exams
            }
            profile["subject_stats"] = subject_stats
            profile["history"] = sessions
            profile["trend"] = trend_list
            profile["latest_ai_analysis"] = latest_ai

            return profile
        finally:
            conn.close()

    # ------------------ TEST NAZORATI VA STATE MACHINE ------------------
    @staticmethod
    def get_admin_tests_for_control():
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.id as test_id, t.title as test_title, t.duration_minutes, t.passing_score,
                       COALESCE(ts.status, t.status, 'draft') as current_status,
                       g.id as group_id, g.name as group_name,
                       sub.id as subject_id, sub.name as subject_name,
                       u.full_name as teacher_name,
                       (SELECT COUNT(*) FROM students WHERE group_id = g.id) as student_count
                FROM tests t
                LEFT JOIN teacher_assignments ta ON ta.id = t.assignment_id
                LEFT JOIN groups g ON g.id = ta.group_id
                LEFT JOIN subjects sub ON sub.id = ta.subject_id
                LEFT JOIN teachers teach ON teach.id = ta.teacher_id
                LEFT JOIN users u ON u.id = teach.user_id
                LEFT JOIN test_sessions ts ON ts.test_id = t.id AND ts.group_id = g.id
                ORDER BY t.id DESC
            """)
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()

    @staticmethod
    def get_test_group_results(test_id: int):
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT es.id as session_id, es.student_id, u.full_name as student_name, st.student_code,
                       es.score_percent, es.correct_answers, es.total_questions, es.tab_switch_count,
                       es.finished_at,
                       COALESCE(sts.status, 'FINISHED') as student_state,
                       (SELECT COUNT(*) FROM proctoring_events WHERE test_id = ? AND student_id = es.student_id) as violations_count
                FROM exam_sessions es
                JOIN students st ON st.id = es.student_id
                JOIN users u ON u.id = st.user_id
                LEFT JOIN student_test_state sts ON sts.student_id = es.student_id AND sts.test_id = ?
                WHERE es.test_id = ?
                ORDER BY es.score_percent DESC
            """, (test_id, test_id, test_id))
            return [dict(row) for row in cursor.fetchall()]
        finally:
            conn.close()


