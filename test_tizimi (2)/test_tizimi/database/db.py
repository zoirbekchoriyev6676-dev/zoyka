import sqlite3
import os
import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from core.security import hash_password
from dotenv import load_dotenv

ENV_PATH = BASE_DIR / ".env"
load_dotenv(dotenv_path=ENV_PATH)

_env_db = os.getenv("DATABASE_PATH", "").strip()
if _env_db:
    _p = Path(_env_db)
    DB_PATH = _p if _p.is_absolute() else BASE_DIR / _p
else:
    DB_PATH = BASE_DIR / "database" / "database.db"

SCHEMA_PATH = BASE_DIR / "database" / "schema.sql"

def get_db_connection():
    """SQLite ma'lumotlar bazasiga ulanish va sozlamalarni o'rnatish."""
    conn = sqlite3.connect(str(DB_PATH), timeout=30.0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.execute("PRAGMA journal_mode = WAL;")
    conn.execute("PRAGMA busy_timeout = 30000;")
    conn.execute("PRAGMA synchronous = NORMAL;")
    return conn

get_db = get_db_connection

def init_db(force_recreate=False):
    """Baza sxemasini ishga tushirish."""
    os.makedirs(DB_PATH.parent, exist_ok=True)
    if force_recreate and os.path.exists(DB_PATH):
        try:
            os.remove(DB_PATH)
            print("Eski baza o'chirildi, yangi Enterprise sxema yaratilmoqda...")
        except Exception as e:
            print(f"Baza faylini tozalashda xatolik: {e}")

    conn = get_db_connection()
    try:
        with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
            conn.executescript(f.read())
        
        # Mavjud bazaga yangi ustunlarni tekshirib qo'shish (migratsiya)
        cursor = conn.cursor()
        cols = [r["name"] for r in cursor.execute("PRAGMA table_info(question_bank)").fetchall()]
        if "quality_score" not in cols:
            cursor.execute("ALTER TABLE question_bank ADD COLUMN quality_score REAL")
        if "status" not in cols:
            cursor.execute("ALTER TABLE question_bank ADD COLUMN status TEXT DEFAULT 'accepted'")
        if "source_based" not in cols:
            cursor.execute("ALTER TABLE question_bank ADD COLUMN source_based INTEGER DEFAULT 0")
        if "source_id" not in cols:
            cursor.execute("ALTER TABLE question_bank ADD COLUMN source_id INTEGER")

        test_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(tests)").fetchall()]
        if "is_results_announced" not in test_cols:
            try:
                cursor.execute("ALTER TABLE tests ADD COLUMN is_results_announced INTEGER DEFAULT 0")
            except Exception:
                pass

        # test_groups_access jadvalini yaratish
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS test_groups_access (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                test_id INTEGER NOT NULL,
                group_id INTEGER NOT NULL,
                status TEXT DEFAULT 'pending' CHECK(status IN ('pending', 'active', 'completed')),
                start_time TIMESTAMP,
                end_time TIMESTAMP,
                is_results_announced INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
                UNIQUE(test_id, group_id)
            )
        """)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_test_groups_access_test_group ON test_groups_access(test_id, group_id)")

        # Mavjud testlarni test_groups_access bilan sinxronlash
        cursor.execute("""
            INSERT OR IGNORE INTO test_groups_access (test_id, group_id, status, start_time, is_results_announced)
            SELECT t.id, ta.group_id, 
                   CASE WHEN LOWER(COALESCE(t.status, '')) IN ('active', 'started') THEN 'active' 
                        WHEN LOWER(COALESCE(t.status, '')) IN ('finished', 'results_published') THEN 'completed' 
                        ELSE 'pending' END,
                   CASE WHEN LOWER(COALESCE(t.status, '')) IN ('active', 'started') THEN CURRENT_TIMESTAMP ELSE NULL END,
                   CASE WHEN LOWER(COALESCE(t.status, '')) = 'results_published' THEN 1 ELSE 0 END
            FROM tests t
            JOIN teacher_assignments ta ON ta.id = t.assignment_id
        """)

        # 1. schools jadvali (AI Exam Report Bot uchun)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS schools (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                ai_school_analysis TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Boshlang'ich maktab kiritish (agar bo'lmasa)
        cursor.execute("SELECT COUNT(*) as cnt FROM schools")
        if cursor.fetchone()["cnt"] == 0:
            cursor.execute("""
                INSERT INTO schools (id, name, ai_school_analysis)
                VALUES (1, '1-sonli ixtisoslashtirilgan umumta''lim maktabi', 
                        'Maktab o''quvchilarining umumiy o''zlashtirish ko''rsatkichi yuqori darajada. Aniq fanlar, xususan Informatika va Matematika yo''nalishlarida nazariy tushunchalar mustahkam. O''quvchilarning faolligi va test yechish tezligi barqaror. Tavsiya: Amaliy mashg''ulotlar va murakkab algoritmlar ustida ishlashni kuchaytirish.')
            """)

        # 2. groups jadvaliga school_id, status, ai_group_analysis ustunlarini qo'shish
        group_cols = [r["name"] for r in cursor.execute("PRAGMA table_info(groups)").fetchall()]
        if "school_id" not in group_cols:
            cursor.execute("ALTER TABLE groups ADD COLUMN school_id INTEGER DEFAULT 1")
        if "status" not in group_cols:
            cursor.execute("ALTER TABLE groups ADD COLUMN status TEXT DEFAULT 'published'")
        if "ai_group_analysis" not in group_cols:
            cursor.execute("ALTER TABLE groups ADD COLUMN ai_group_analysis TEXT")

        # 3. results jadvali - bot uchun to'g'ridan-to'g'ri natijalar jadvali
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                group_id INTEGER NOT NULL,
                student_name TEXT NOT NULL,
                score REAL DEFAULT 0.0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
            )
        """)

        # 4. Kamera va nazorat jadvallari (camera_monitor migratsiyasi)
        try:
            from services.camera_monitor import migrate as camera_migrate
            camera_migrate(conn)
        except Exception as _ce:
            print(f"Kamera migratsiyasi ogohlantirish: {_ce}")

        # 5. Yuqori tezlikli qidiruv indekslari (Performance & Scale Indexes)
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_teacher_assignments_group_active ON teacher_assignments(group_id, is_active)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_tests_assignment_status ON tests(assignment_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_exam_sessions_student_status ON exam_sessions(student_id, status)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_question_bank_subject_topic ON question_bank(subject_id, topic_id)")

        conn.commit()
    finally:
        conn.close()

def seed_enterprise_data():
    """
    Arxitektura talablariga mos yagona 3 ta hisob:
    - O'quvchi: Alisher Choriyev (Login: Ali_7309, Parol/PIN: 7309)
    - O'qituvchi: Zoirbek Choriyev (Fani: IT, Login: wolking, Parol: wolking)
    - Admin: Zoir (Login: zoir, Parol: zoir)
    """
    conn = get_db_connection()
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT COUNT(*) as cnt FROM users")
        if cursor.fetchone()["cnt"] > 0:
            return  # Ma'lumotlar allaqachon mavjud

        print("Boshlang'ich arxitektura ma'lumotlari yuklanmoqda...")

        # 1. Foydalanuvchilar (Admin, O'qituvchi, O'quvchi)
        admin_pass = hash_password("zoir")
        teacher_pass = hash_password("wolking")
        student_pass = hash_password("7309")

        # Admin: Zoir
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, phone)
            VALUES (?, ?, 'admin', 'Zoir', '+998901234567')
        """, ("zoir", admin_pass))
        admin_uid = cursor.lastrowid

        # O'qituvchi: Zoirbek Choriyev (IT)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, phone)
            VALUES (?, ?, 'teacher', 'Zoirbek Choriyev', '+998902345678')
        """, ("wolking", teacher_pass))
        t_uid = cursor.lastrowid
        cursor.execute("""
            INSERT INTO teachers (user_id, specialty)
            VALUES (?, 'Oliy toifali IT va dasturlash o''qituvchisi')
        """, (t_uid,))
        teacher_zoirbek_id = cursor.lastrowid

        # 2. Guruh
        cursor.execute("INSERT INTO groups (name, academic_year) VALUES (?, ?)", ("10-A", "2026/2027"))
        group_10a_id = cursor.lastrowid

        # 3. O'quvchi: Alisher Choriyev (10-A, Login/Kodi: Ali_7309, PIN/Parol: 7309)
        cursor.execute("""
            INSERT INTO users (username, password_hash, role, full_name, phone)
            VALUES (?, ?, 'student', 'Alisher Choriyev', '+998931112233')
        """, ("Ali_7309", student_pass))
        s_uid = cursor.lastrowid
        cursor.execute("""
            INSERT INTO students (user_id, group_id, student_code, pin)
            VALUES (?, ?, 'Ali_7309', '7309')
        """, (s_uid, group_10a_id))
        student_alisher_id = cursor.lastrowid

        # 4. Fan (IT)
        cursor.execute("""
            INSERT INTO subjects (name, code, description)
            VALUES ('IT', 'IT-01', 'Axborot texnologiyalari, Dasturlash va Algoritmlar')
        """)
        subject_it_id = cursor.lastrowid

        # 5. O'qituvchi - Fan - Guruh Biriktirish (Teacher Assignment)
        cursor.execute("""
            INSERT INTO teacher_assignments (teacher_id, subject_id, group_id, academic_year, semester)
            VALUES (?, ?, ?, '2026/2027', 1)
        """, (teacher_zoirbek_id, subject_it_id, group_10a_id))
        assignment_id = cursor.lastrowid

        # 6. Mavzular (Topics)
        topics_data = [
            ("Python asoslari va o'zgaruvchilar", "O'zgaruvchilar, ma'lumot turlari va kiritish-chiqarish"),
            ("Shart operatorlari (if/elif/else)", "Taqqoslash, mantiqiy amallar va tarmoqlanuvchi algoritmlar"),
            ("Sikllar (for va while)", "Takrorlanuvchi jarayonlar, range funksiyasi va sikl boshqaruvi"),
            ("Ro'yxatlar va ma'lumotlar tuzilmasi", "List elementlari bilan ishlash, slicing va indekslash")
        ]
        topic_ids = []
        for tname, tdesc in topics_data:
            cursor.execute("INSERT INTO topics (subject_id, name, description) VALUES (?, ?, ?)",
                           (subject_it_id, tname, tdesc))
            topic_ids.append(cursor.lastrowid)

        # 7. Savollar banki (IT bo'yicha 12 ta sifatli savol)
        q_bank_data = [
            # Topic 1: Python asoslari
            {
                "topic_id": topic_ids[0],
                "text": "Python dasturlash tilida qaysi funksiya foydalanuvchidan ma'lumot kiritish uchun ishlatiladi?",
                "diff": "easy",
                "exp": "Python'da input() funksiyasi klaviaturadan satr ko'rinishidagi ma'lumotlarni qabul qiladi.",
                "opts": [("input()", 1), ("print()", 0), ("scan()", 0), ("read()", 0)]
            },
            {
                "topic_id": topic_ids[0],
                "text": "type(3.14) ifodasi qanday ma'lumot turini qaytaradi?",
                "diff": "easy",
                "exp": "3.14 o'nlik kasr son bo'lgani sababli u <class 'float'> turiga tegishli.",
                "opts": [("<class 'float'>", 1), ("<class 'int'>", 0), ("<class 'str'>", 0), ("<class 'bool'>", 0)]
            },
            {
                "topic_id": topic_ids[0],
                "text": "Python'da bir satrli izoh qaysi belgi bilan boshlanadi?",
                "diff": "easy",
                "exp": "Python'da # belgisi bir satrli izohlarni belgilash uchun ishlatiladi.",
                "opts": [("#", 1), ("//", 0), ("/*", 0), ("--", 0)]
            },
            # Topic 2: Shart operatorlari
            {
                "topic_id": topic_ids[1],
                "text": "Python'da ko'p shartli tarmoqlanishda oraliq shartni tekshirish uchun qaysi kalit so'z ishlatiladi?",
                "diff": "easy",
                "exp": "Python'da 'else if' o'rniga qisqartirilgan 'elif' kalit so'zi qo'llaniladi.",
                "opts": [("elif", 1), ("else if", 0), ("elseif", 0), ("when", 0)]
            },
            {
                "topic_id": topic_ids[1],
                "text": "Agar a = 10 va b = 20 bo'lsa, 'a > 5 and b < 15' ifodasining natijasi nima bo'ladi?",
                "diff": "medium",
                "exp": "a > 5 (True) bo'lsa-da, b < 15 (False) bo'lgani uchun 'and' operatori False qaytaradi.",
                "opts": [("False", 1), ("True", 0), ("None", 0), ("SyntaxError", 0)]
            },
            {
                "topic_id": topic_ids[1],
                "text": "Tenglikni tekshirish uchun qaysi taqqoslash operatori ishlatiladi?",
                "diff": "easy",
                "exp": "== operatori qiymatlarning tengligini tekshiradi, = esa o'zlashtirish operatoridir.",
                "opts": [("==", 1), ("=", 0), ("===", 0), ("is not", 0)]
            },
            # Topic 3: Sikllar
            {
                "topic_id": topic_ids[2],
                "text": "range(1, 6) ketma-ketligi qaysi sonlarni o'z ichiga oladi?",
                "diff": "easy",
                "exp": "range(start, stop) da stop qiymat kirmaydi, ya'ni 1, 2, 3, 4, 5 hosil bo'ladi.",
                "opts": [("1, 2, 3, 4, 5", 1), ("1, 2, 3, 4, 5, 6", 0), ("0, 1, 2, 3, 4, 5", 0), ("2, 3, 4, 5, 6", 0)]
            },
            {
                "topic_id": topic_ids[2],
                "text": "Siklni muddatidan oldin to'xtatish uchun qaysi operator qo'llaniladi?",
                "diff": "easy",
                "exp": "break operatori bajarilayotgan sikldan darhol chiqib ketishni ta'minlaydi.",
                "opts": [("break", 1), ("continue", 0), ("pass", 0), ("stop", 0)]
            },
            {
                "topic_id": topic_ids[2],
                "text": "Siklning keyingi iteratsiyasiga o'tish uchun qaysi operator ishlatiladi?",
                "diff": "easy",
                "exp": "continue operatori joriy iteratsiyaning qolgan qismini tashlab ketib, keyingisiga o'tadi.",
                "opts": [("continue", 1), ("break", 0), ("return", 0), ("skip", 0)]
            },
            # Topic 4: Ro'yxatlar
            {
                "topic_id": topic_ids[3],
                "text": "Ro'yxat oxiriga yangi element qo'shish uchun qaysi metod ishlatiladi?",
                "diff": "easy",
                "exp": "append() metodi ro'yxatning oxiriga berilgan elementni qo'shadi.",
                "opts": [("append()", 1), ("add()", 0), ("insert()", 0), ("extend()", 0)]
            },
            {
                "topic_id": topic_ids[3],
                "text": "numbers = [10, 20, 30, 40] ro'yxatida numbers[2] qaysi elementga teng?",
                "diff": "easy",
                "exp": "Indekslash 0 dan boshlanadi: 0->10, 1->20, 2->30.",
                "opts": [("30", 1), ("20", 0), ("40", 0), ("10", 0)]
            },
            {
                "topic_id": topic_ids[3],
                "text": "len([1, 2, 3, 4, 5]) ifodasi qanday natija qaytaradi?",
                "diff": "easy",
                "exp": "len() funksiyasi to'plamdagi elementlar sonini (uzunligini) qaytaradi, bu yerda 5.",
                "opts": [("5", 1), ("4", 0), ("6", 0), ("0", 0)]
            }
        ]

        inserted_q_ids = []
        for q in q_bank_data:
            cursor.execute("""
                INSERT INTO question_bank (subject_id, topic_id, teacher_id, question_text, difficulty, points, explanation, quality_score, status)
                VALUES (?, ?, ?, ?, ?, 1, ?, 0.95, 'accepted')
            """, (subject_it_id, q["topic_id"], teacher_zoirbek_id, q["text"], q["diff"], q["exp"]))
            qid = cursor.lastrowid
            inserted_q_ids.append(qid)

            for opt_text, is_c in q["opts"]:
                cursor.execute("""
                    INSERT INTO question_options (question_id, option_text, is_correct)
                    VALUES (?, ?, ?)
                """, (qid, opt_text, is_c))

        # 8. Test yaratish: "1-oraliq nazorat: IT va Dasturlash" (10-A guruhi uchun)
        cursor.execute("""
            INSERT INTO tests (
                title, assignment_id, exam_type, duration_minutes, 
                passing_score, randomize_questions, max_attempts, enable_camera, status
            ) VALUES (?, ?, 'midterm', 30, 60, 1, 1, 0, 'ready')
        """, ("1-oraliq nazorat: IT va Dasturlash", assignment_id))
        test_id = cursor.lastrowid

        # Savollarni testga biriktirish
        for qid in inserted_q_ids:
            cursor.execute("INSERT INTO test_questions (test_id, question_id) VALUES (?, ?)", (test_id, qid))

        # 9. Test Sessiyasi (State Machine: READY)
        cursor.execute("""
            INSERT INTO test_sessions (group_id, test_id, status)
            VALUES (?, ?, 'READY')
        """, (group_10a_id, test_id))
        test_session_id = cursor.lastrowid

        # 9.1 Guruh kirish ruxsati (test_groups_access)
        cursor.execute("""
            INSERT OR IGNORE INTO test_groups_access (test_id, group_id, status, start_time, is_results_announced)
            VALUES (?, ?, 'active', CURRENT_TIMESTAMP, 0)
        """, (test_id, group_10a_id))

        # 10. Proctoring Sozlamalari (Default limitlar: 3 marta)
        cursor.execute("""
            INSERT INTO proctoring_settings (
                test_id, tab_switch_limit, fullscreen_limit, reload_limit,
                face_lost_limit, multiple_faces_limit, enable_camera, camera_policy
            ) VALUES (?, 3, 3, 3, 5, 2, 0, 'allow_without_camera')
        """, (test_id,))

        # 11. O'quvchining test holati (Boshlang'ich holati: ACTIVE)
        cursor.execute("""
            INSERT INTO student_test_state (session_id, student_id, test_id, status)
            VALUES (?, ?, ?, 'ACTIVE')
        """, (test_session_id, student_alisher_id, test_id))

        # 12. Audit log
        cursor.execute("""
            INSERT INTO audit_logs (user_id, action, target_type, target_id, details)
            VALUES (?, 'SYSTEM_INIT', 'SYSTEM', 1, 'Ideal Test Tizimi arxitekturasi bo''yicha boshlang''ich ma''lumotlar yuklandi.')
        """, (admin_uid,))

        conn.commit()
        print("Ideal Test Tizimi bazasi muvaffaqiyatli ishga tushirildi!")
    finally:
        conn.close()

if __name__ == "__main__":
    init_db(force_recreate=True)
    seed_enterprise_data()
