import sys
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from main import app
from database.db import init_db, seed_enterprise_data, get_db_connection

client = TestClient(app)

def run_security_audit_tests():
    print("=====================================================================")
    print("  TEST TIZIMI — XAVFSIZLIK VA AUDIT TEKSHIRUVLARI (SECURITY SUITE)   ")
    print("=====================================================================")

    # Baza va boshlang'ich ma'lumotlar
    init_db(force_recreate=False)
    seed_enterprise_data()

    # Logindan o'tish
    admin_login = client.post("/api/auth/login", json={"identifier": "zoir", "secret": "zoir"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    teacher_login = client.post("/api/auth/login", json={"identifier": "wolking", "secret": "wolking"})
    assert teacher_login.status_code == 200
    teacher_token = teacher_login.json()["token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    student_login = client.post("/api/auth/login", json={"identifier": "Ali_7309", "secret": "7309"})
    assert student_login.status_code == 200
    student_token = student_login.json()["token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}

    print("\n--- 1. XAVFSIZLIK SARLAVHALARI (SECURITY HEADERS) TEKSHIRUVI ---")
    resp = client.get("/")
    assert resp.status_code == 200
    assert resp.headers.get("X-Frame-Options") == "SAMEORIGIN", "Clickjacking himoyasi mavjud emas"
    assert resp.headers.get("X-Content-Type-Options") == "nosniff", "MIME sniffing himoyasi mavjud emas"
    assert resp.headers.get("X-XSS-Protection") == "1; mode=block", "XSS sarlavhasi mavjud emas"
    assert resp.headers.get("Referrer-Policy") == "strict-origin-when-cross-origin"
    print("[OK] Barcha OWASP xavfsizlik sarlavhalari (Frame, Sniff, XSS, Referrer) muvaffaqiyatli tekshirildi.")

    print("\n--- 2. SO'ROV HAJMI CHEKLOVI (DOS / OOM HIMOYASI) TEKSHIRUVI ---")
    # 16 MB soxta content-length bilan kelgan so'rov
    big_headers = {"content-length": str(16 * 1024 * 1024)}
    big_req = client.post("/api/auth/login", headers=big_headers, json={"identifier": "a", "secret": "b"})
    assert big_req.status_code == 413, f"Katta so'rov 413 qaytarmadi: {big_req.status_code}"
    print("[OK] 15 MB dan katta so'rovlar server tomonidan nazoratli rad etildi (413 Payload Too Large).")

    print("\n--- 3. BROKEN ACCESS CONTROL & IDOR HIMOYASI TEKSHIRUVI ---")
    # 3.1 Anonim foydalanuvchi questions routeriga kira olmasligi
    anon_q = client.post("/api/questions", json={"test_id": 1, "topic_id": 1, "question_text": "Hacked?", "options": []})
    assert anon_q.status_code in (401, 403), f"Anonim savol yaratish rad etilmadi: {anon_q.status_code}"
    print("[OK] Anonim foydalanuvchining savol yaratish urinishi 401/403 bilan to'xtatildi.")

    # 3.2 O'quvchi o'qituvchi endpointiga (/api/questions) kira olmasligi
    st_q = client.post("/api/questions", headers=student_headers, json={"test_id": 1, "topic_id": 1, "question_text": "Hacked?", "options": []})
    assert st_q.status_code == 403, f"O'quvchi savol yarata oldi: {st_q.status_code}"
    print("[OK] O'quvchining o'qituvchi huquqlarini egallash urinishi 403 bilan rad etildi.")

    # 3.3 Anonim foydalanuvchi natijalarni ko'ra olmasligi
    anon_res = client.get("/api/results")
    assert anon_res.status_code in (401, 403)
    print("[OK] Himoyalanmagan natijalar ro'yxati anonim shaxslar uchun yopildi (401/403).")

    # 3.4 O'quvchi boshqa guruh test savollarini tortib ololmasligi (Cross-tenant IDOR)
    # Yangi guruh va boshqa test yaratamiz
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM test_groups_access WHERE test_id IN (888, 999)")
        c.execute("DELETE FROM tests WHERE id IN (888, 999)")
        c.execute("DELETE FROM teacher_assignments WHERE id IN (888, 999)")
        c.execute("DELETE FROM groups WHERE id = 999")
        conn.commit()

        c.execute("INSERT INTO groups (id, name) VALUES (999, '11-B')")
        c.execute("""
            INSERT INTO teacher_assignments (id, teacher_id, subject_id, group_id)
            VALUES (999, 1, 1, 999)
        """)
        c.execute("""
            INSERT INTO tests (id, title, assignment_id, status)
            VALUES (999, 'Begona Guruh Testi', 999, 'ready')
        """)
        c.execute("""
            INSERT INTO test_groups_access (test_id, group_id, status)
            VALUES (999, 999, 'active')
        """)
        conn.commit()

    cross_group_res = client.get("/api/tests/999/student-questions", headers=student_headers)
    assert cross_group_res.status_code == 403, f"Begona guruh savollari ochilib qoldi: {cross_group_res.status_code}"
    print("[OK] O'quvchi boshqa guruhning test savollarini o'g'irlay olmadi (403 - Guruh tekshiruvi).")

    # 3.5 Begona o'qituvchining testini o'chirish/tahrirlash IDOR himoyasi
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute("DELETE FROM tests WHERE id = 888")
        c.execute("DELETE FROM teacher_assignments WHERE id = 888")
        c.execute("DELETE FROM teachers WHERE id = 888")
        c.execute("DELETE FROM users WHERE id = 888")
        conn.commit()

        c.execute("""
            INSERT INTO users (id, username, password_hash, role, full_name)
            VALUES (888, 'teacher_other', 'hash', 'teacher', 'Teacher Other')
        """)
        c.execute("""
            INSERT INTO teachers (id, user_id, specialty)
            VALUES (888, 888, 'Matematika')
        """)
        c.execute("""
            INSERT INTO teacher_assignments (id, teacher_id, subject_id, group_id)
            VALUES (888, 888, 1, 1)
        """)
        c.execute("""
            INSERT INTO tests (id, title, assignment_id, status)
            VALUES (888, 'Boshqa Oqituvchi Testi', 888, 'ready')
        """)
        conn.commit()

    idor_del = client.delete("/api/tests/888", headers=teacher_headers)
    assert idor_del.status_code == 403, f"Boshqa o'qituvchi testini o'chirishga yo'l qo'yildi: {idor_del.status_code}"
    print("[OK] O'qituvchi boshqa o'qituvchining testini o'chira olmadi (403 - Egalik tekshiruvi).")

    print("\n--- 4. BRUTE FORCE VA RATE LIMITING TEKSHIRUVI ---")
    blocked_triggered = False
    for i in range(7):
        fail_res = client.post("/api/auth/login", json={"identifier": "fake_user_test", "secret": "wrong_pass"})
        if fail_res.status_code == 429:
            blocked_triggered = True
            break
    assert blocked_triggered, "5 ta xato urunishdan keyin 429 bloklanishi kerak edi"
    print("[OK] 5 ta xato login urinishidan so'ng tizim 429 Too Many Requests bilan blokladi.")

    print("\n--- 5. WORD FAYL YUKLASH HAJMI CHEKLOVI (OOM HIMOYASI) ---")
    huge_fake_docx = b"PK\x03\x04" + (b"0" * (11 * 1024 * 1024))
    upload_res = client.post(
        "/api/teacher/word/import-preview",
        files={"file": ("huge_exam.docx", huge_fake_docx, "application/vnd.openxmlformats-officedocument.wordprocessingml.document")},
        headers=teacher_headers
    )
    assert upload_res.status_code == 413, f"10 MB dan katta fayl 413 qaytarmadi: {upload_res.status_code}"
    print("[OK] 10 MB dan katta Word fayl yuklanganda server 413 Payload Too Large bilan xavfsiz to'xtatildi.")

    print("\n--- 6. PARALLEL TOPSHIRISH VA NATIJA SIR SAQLANISHI TEKSHIRUVI ---")
    # Guruh 10-A testi (test_id=1) uchun topshirish
    sub_res = client.post("/api/student/test/submit", json={
        "test_id": 1,
        "answers": {"1": 1},
        "tab_switch_count": 0,
        "time_spent_seconds": 60
    }, headers=student_headers)
    # Agar allaqachon topshirilgan bo'lsa 403 yoki muvaffaqiyatli bo'lsa 200
    if sub_res.status_code == 200:
        data = sub_res.json()
        assert "session_id" in data
        assert data.get("score_percent") is None, "Natija e'lon qilinmasdan oldin ball ko'rinmasligi kerak"
        print("[OK] Test topshirilganda e'londan oldin ball oshkor qilinmadi.")
    else:
        assert sub_res.status_code == 403
        print("[OK] Allaqachon topshirilgan test qayta qabul qilinmadi (403 - Idempotent).")

    print("\n=====================================================================")
    print("  BARCHA XAVFSIZLIK AUDIT SINOVLARI 100% MUVAFFAQIYATLI O'TDI!       ")
    print("=====================================================================")

if __name__ == "__main__":
    run_security_audit_tests()
