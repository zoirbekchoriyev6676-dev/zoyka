-- Enterprise LMS & Exam Platform Schema
-- Roles: Admin, Teacher, Student

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    role TEXT NOT NULL CHECK(role IN ('admin', 'teacher', 'student')),
    full_name TEXT NOT NULL,
    phone TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS groups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE NOT NULL,
    academic_year TEXT DEFAULT '2026/2027',
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS subjects (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    code TEXT UNIQUE NOT NULL,
    description TEXT,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS teachers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    specialty TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS students (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER UNIQUE NOT NULL,
    group_id INTEGER NOT NULL,
    student_code TEXT UNIQUE NOT NULL,
    pin TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS teacher_assignments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    teacher_id INTEGER NOT NULL,
    subject_id INTEGER NOT NULL,
    group_id INTEGER NOT NULL,
    academic_year TEXT DEFAULT '2026/2027',
    semester INTEGER DEFAULT 1,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE CASCADE,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    UNIQUE(teacher_id, subject_id, group_id, academic_year, semester)
);

CREATE TABLE IF NOT EXISTS topics (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS question_bank (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    subject_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    teacher_id INTEGER,
    question_text TEXT NOT NULL,
    difficulty TEXT DEFAULT 'medium' CHECK(difficulty IN ('easy', 'medium', 'hard')),
    points INTEGER DEFAULT 1,
    explanation TEXT,
    quality_score REAL,
    status TEXT DEFAULT 'accepted',
    source_based INTEGER DEFAULT 0,
    source_id INTEGER,
    is_active INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE,
    FOREIGN KEY (teacher_id) REFERENCES teachers(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS question_options (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    question_id INTEGER NOT NULL,
    option_text TEXT NOT NULL,
    is_correct INTEGER DEFAULT 0,
    FOREIGN KEY (question_id) REFERENCES question_bank(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tests (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    assignment_id INTEGER NOT NULL,
    exam_type TEXT DEFAULT 'midterm' CHECK(exam_type IN ('diagnostic', 'quiz', 'midterm', 'final')),
    duration_minutes INTEGER DEFAULT 30,
    start_time TIMESTAMP,
    end_time TIMESTAMP,
    passing_score INTEGER DEFAULT 60,
    randomize_questions INTEGER DEFAULT 1,
    max_attempts INTEGER DEFAULT 1,
    enable_camera INTEGER DEFAULT 0,
    status TEXT DEFAULT 'ready' CHECK(status IN ('draft', 'ready', 'started', 'finished', 'results_approved', 'results_published', 'active', 'scheduled')),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (assignment_id) REFERENCES teacher_assignments(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS test_questions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES question_bank(id) ON DELETE CASCADE,
    UNIQUE(test_id, question_id)
);

CREATE TABLE IF NOT EXISTS exam_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER NOT NULL,
    student_id INTEGER NOT NULL,
    score_percent REAL DEFAULT 0.0,
    total_questions INTEGER DEFAULT 0,
    correct_answers INTEGER DEFAULT 0,
    incorrect_answers INTEGER DEFAULT 0,
    tab_switch_count INTEGER DEFAULT 0,
    time_spent_seconds INTEGER DEFAULT 0,
    status TEXT DEFAULT 'completed' CHECK(status IN ('in_progress', 'completed')),
    ai_analysis TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS student_answers (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    question_id INTEGER NOT NULL,
    selected_option_id INTEGER,
    is_correct INTEGER DEFAULT 0,
    FOREIGN KEY (session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (question_id) REFERENCES question_bank(id) ON DELETE CASCADE,
    FOREIGN KEY (selected_option_id) REFERENCES question_options(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS session_topic_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    topic_id INTEGER NOT NULL,
    total_questions INTEGER NOT NULL,
    correct_answers INTEGER NOT NULL,
    percentage REAL NOT NULL,
    FOREIGN KEY (session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE,
    FOREIGN KEY (topic_id) REFERENCES topics(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS monitoring_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT,
    event_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (session_id) REFERENCES exam_sessions(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    action TEXT NOT NULL,
    target_type TEXT,
    target_id INTEGER,
    details TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS ai_reports (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    report_type TEXT NOT NULL CHECK(report_type IN ('student', 'group', 'subject', 'school')),
    target_id INTEGER,
    report_text TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ==================== YANGI QATLAM JADVALLARI (ARXITEKTURA 8-BO'LIM) ====================

-- 1. Test Sessiyalari (Guruh + Test + State Machine holati)
CREATE TABLE IF NOT EXISTS test_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    group_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    status TEXT DEFAULT 'DRAFT' CHECK(status IN ('DRAFT', 'READY', 'STARTED', 'FINISHED', 'RESULTS_APPROVED', 'RESULTS_PUBLISHED')),
    started_at TIMESTAMP,
    finished_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (group_id) REFERENCES groups(id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
);

-- 2. Har bir o'quvchining test holati (ACTIVE / BLOCKED / FINISHED)
CREATE TABLE IF NOT EXISTS student_test_state (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    status TEXT DEFAULT 'ACTIVE' CHECK(status IN ('ACTIVE', 'BLOCKED', 'FINISHED')),
    block_reason TEXT,
    blocked_at TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE,
    UNIQUE(student_id, test_id)
);

-- 3. Proctoring Sozlamalari (Test bo'yicha)
CREATE TABLE IF NOT EXISTS proctoring_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    test_id INTEGER UNIQUE NOT NULL,
    tab_switch_limit INTEGER DEFAULT 3,
    fullscreen_limit INTEGER DEFAULT 3,
    reload_limit INTEGER DEFAULT 3,
    face_lost_limit INTEGER DEFAULT 5,
    multiple_faces_limit INTEGER DEFAULT 2,
    enable_camera INTEGER DEFAULT 0,
    camera_policy TEXT DEFAULT 'allow_without_camera' CHECK(camera_policy IN ('allow_without_camera', 'block')),
    track_exit INTEGER DEFAULT 1,
    track_suspicious INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
);

-- 4. Proctoring Hodisalari
CREATE TABLE IF NOT EXISTS proctoring_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id INTEGER,
    student_id INTEGER NOT NULL,
    test_id INTEGER NOT NULL,
    event_type TEXT NOT NULL,
    details TEXT,
    counter INTEGER DEFAULT 1,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (test_id) REFERENCES tests(id) ON DELETE CASCADE
);

-- 5. AI Audit Log
CREATE TABLE IF NOT EXISTS ai_audit_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    task TEXT NOT NULL,
    model TEXT,
    request_data TEXT,
    response_data TEXT,
    status TEXT DEFAULT 'success',
    latency REAL DEFAULT 0.0,
    tokens INTEGER DEFAULT 0,
    error TEXT,
    requested_count INTEGER DEFAULT 0,
    accepted_count INTEGER DEFAULT 0,
    rejected_count INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE SET NULL
);

-- 6. AI Tahlil Keshi (Cache)
CREATE TABLE IF NOT EXISTS ai_cache (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    cache_key TEXT UNIQUE NOT NULL,
    response_data TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 7. RAG Materiallari
CREATE TABLE IF NOT EXISTS materials (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    file_path TEXT,
    subject_id INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (subject_id) REFERENCES subjects(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS material_chunks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    material_id INTEGER NOT NULL,
    chunk_text TEXT NOT NULL,
    chunk_index INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (material_id) REFERENCES materials(id) ON DELETE CASCADE
);

-- ==================== ENTERPRISE INDEXLAR (PERFORMANCE BOOST) ====================
CREATE INDEX IF NOT EXISTS idx_exam_sessions_test_student ON exam_sessions(test_id, student_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_session ON student_answers(session_id);
CREATE INDEX IF NOT EXISTS idx_student_answers_question ON student_answers(question_id);
CREATE INDEX IF NOT EXISTS idx_proctoring_events_student_test ON proctoring_events(student_id, test_id);
CREATE INDEX IF NOT EXISTS idx_test_questions_test ON test_questions(test_id);
CREATE INDEX IF NOT EXISTS idx_question_options_question ON question_options(question_id);
-- 8. Guruhlar bo'yicha testga kirish va yakunlash holati (Multi-group test access & announcement)
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
);

CREATE INDEX IF NOT EXISTS idx_test_groups_access_test_group ON test_groups_access(test_id, group_id);
CREATE INDEX IF NOT EXISTS idx_teacher_assignments_group_active ON teacher_assignments(group_id, is_active);
CREATE INDEX IF NOT EXISTS idx_tests_assignment_status ON tests(assignment_id, status);
CREATE INDEX IF NOT EXISTS idx_exam_sessions_student_status ON exam_sessions(student_id, status);
CREATE INDEX IF NOT EXISTS idx_question_bank_subject_topic ON question_bank(subject_id, topic_id);


