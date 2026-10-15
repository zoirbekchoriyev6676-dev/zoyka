import sys
import os
from pathlib import Path
from fastapi.testclient import TestClient

# Ensure UTF-8 output on Windows console
if sys.platform == "win32":
    try:
        sys.stdout.reconfigure(encoding="utf-8")
        sys.stderr.reconfigure(encoding="utf-8")
    except Exception:
        pass

BASE_DIR = Path(__file__).resolve().parent
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))

from main import app
from database.db import init_db, seed_enterprise_data, get_db

def test_enterprise_blueprint():
    print("=====================================================================")
    print("  IDEAL TEST TIZIMI - ARXITEKTURA VA TALABLAR TEKSHIRUVI (14 BAND)   ")
    print("=====================================================================")

    print("\n--- 1. BAZA VA SOZLAMALARNI TOZA QAYTA TIKLASH ---")
    init_db(force_recreate=True)
    seed_enterprise_data()
    client = TestClient(app)
    print("[OK] Baza toza qayta tiklandi va faqat talab qilingan ma'lumotlar yuklandi.")

    print("\n--- 2. FOYDALANUVCHILAR VA LOGIN (3 TA HISOB, DEMO YO'Q) ---")
    # 2.1 Ali_7309 / 7309 -> O'quvchi
    res = client.post("/api/auth/login", json={"identifier": "Ali_7309", "secret": "7309"})
    assert res.status_code == 200, f"O'quvchi login xatosi: {res.text}"
    student_data = res.json()
    assert student_data["user"]["role"] == "student"
    assert student_data["user"]["full_name"] == "Alisher Choriyev"
    student_token = student_data["token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("[OK] O'quvchi Alisher Choriyev (Ali_7309 / 7309) muvaffaqiyatli kirdi.")

    # 2.2 wolking / wolking -> O'qituvchi (IT)
    res = client.post("/api/auth/login", json={"identifier": "wolking", "secret": "wolking"})
    assert res.status_code == 200, f"O'qituvchi login xatosi: {res.text}"
    teacher_data = res.json()
    assert teacher_data["user"]["role"] == "teacher"
    assert teacher_data["user"]["full_name"] == "Zoirbek Choriyev"
    teacher_token = teacher_data["token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    print("[OK] O'qituvchi Zoirbek Choriyev (wolking / wolking, IT) muvaffaqiyatli kirdi.")

    # 2.3 zoir / zoir -> Admin
    res = client.post("/api/auth/login", json={"identifier": "zoir", "secret": "zoir"})
    assert res.status_code == 200, f"Admin login xatosi: {res.text}"
    admin_data = res.json()
    assert admin_data["user"]["role"] == "admin"
    assert admin_data["user"]["full_name"] == "Zoir"
    admin_token = admin_data["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[OK] Admin Zoir (zoir / zoir) muvaffaqiyatli kirdi.")

    # 2.4 Noto'g'ri yoki eski loginlar kirishi taqiqlangan
    for bad_id, bad_pw in [
        ("admin", "admin123"),
        ("karimov.a", "teacher123"),
        ("javohir.aliyev", "student123"),
        ("Ali_7309", "noto'g'ri_parol"),
    ]:
        res = client.post("/api/auth/login", json={"identifier": bad_id, "secret": bad_pw})
        assert res.status_code == 401, f"Kutilgan 401 bo'lmadi ({bad_id}): {res.status_code}"
    print("[OK] Eski va noto'g'ri loginlar qat'iy rad etildi (401).")

    # 2.5 Bazada faqat 3 ta foydalanuvchi borligini tekshirish
    with get_db() as conn:
        users = conn.execute("SELECT id, username, full_name, role FROM users").fetchall()
        assert len(users) == 3, f"Bazada 3 ta user bo'lishi kerak, mavjud: {len(users)}"
        print(f"[OK] Bazada aynan 3 ta foydalanuvchi mavjud: {[u['username'] for u in users]}")

    print("\n--- 3. TEST HAYOT SIKLI (STATE MACHINE) NAZORATI ---")
    test_id = 1
    group_id = 1

    # 3.1 DRAFT holatida o'quvchi testni ko'ra olmaydi
    with get_db() as conn:
        conn.execute("UPDATE test_sessions SET status = 'DRAFT' WHERE test_id = ? AND group_id = ?", (test_id, group_id))
        conn.execute("UPDATE tests SET status = 'draft' WHERE id = ?", (test_id,))
        conn.commit()
    
    res = client.get(f"/api/student/test/{test_id}", headers=student_headers)
    assert res.status_code == 403, f"DRAFT holatida o'quvchi kira olmasligi kerak: {res.status_code}"
    print("[OK] DRAFT holatida o'quvchiga test ochilmadi (403 - Test hali boshlanmagan).")

    # 3.2 Taqiqlangan holat o'tishi: DRAFT -> STARTED to'g'ridan-to'g'ri o'ta olmaydi (READY bo'lishi shart)
    res = client.post(f"/api/groups/{group_id}/tests/{test_id}/start", headers=admin_headers)
    assert res.status_code == 400, "DRAFT -> STARTED to'g'ridan-to'g'ri o'tishi rad etilishi kerak edi"
    print("[OK] Ruxsat etilmagan DRAFT -> STARTED holat o'tishi server tomonidan bloklandi.")

    # 3.3 To'g'ri o'tish: DRAFT -> READY
    from services.test_service import TestService
    t_res = TestService.transition_test_state(test_id=test_id, target_state="READY", group_id=group_id, user_role="teacher", user_id=2)
    assert t_res.get("success"), f"READY ga o'tish xatosi: {t_res}"
    print("[OK] Test READY (Kutmoqda) holatiga o'tkazildi.")

    # 3.4 READY holatida ham o'quvchi boshlay olmaydi
    res = client.get(f"/api/student/test/{test_id}", headers=student_headers)
    assert res.status_code == 403, "READY holatida ham o'quvchi kira olmasligi kerak"
    print("[OK] READY holatida ham o'quvchi kira olmaydi (Faqat admin boshlaganda).")

    # 3.5 Admin: [ TESTNI BOSHLASH ] -> STARTED
    res = client.post(f"/api/groups/{group_id}/tests/{test_id}/start", headers=admin_headers)
    assert res.status_code == 200, f"Admin testni boshlay olmadi: {res.text}"
    print("[OK] Admin [ TESTNI BOSHLASH ] tugmasini bosdi -> Holat: STARTED.")

    # 3.6 Endi o'quvchi testga kiradi
    res = client.get(f"/api/student/test/{test_id}", headers=student_headers)
    assert res.status_code == 200, f"O'quvchi testni ocholmadi: {res.text}"
    test_data = res.json()
    questions = test_data["questions"]
    assert len(questions) > 0, "Savollar topilmadi"
    print(f"[OK] O'quvchi testga kirdi: {len(questions)} ta savol yuklandi.")

    print("\n--- 4. PROCTORING (NAZORAT) VA LIMITGA YETGANDA BLOKLASH ---")
    # 4.1 Proctoring sozlamalarini tekshirish (tab_switch limiti = 3)
    res = client.get(f"/api/proctoring/status/{test_id}", headers=student_headers)
    assert res.status_code == 200
    p_status = res.json()
    print(f"[OK] O'quvchi proctoring holati: {p_status}")

    # 4.2 O'quvchi 1-marta oynadan chiqdi (ogohlantirish)
    res = client.post("/api/proctoring/event", json={"test_id": test_id, "event_type": "tab_switch"}, headers=student_headers)
    assert res.status_code == 200
    ev1 = res.json()
    assert ev1["student_state"] == "ACTIVE" and not ev1["is_blocked"]
    print(f"[OK] 1-chi tab_switch: Ogohlantirish (Sanog'i: {ev1['current_count']})")

    # 4.3 O'quvchi 2-marta chiqdi (ogohlantirish)
    res = client.post("/api/proctoring/event", json={"test_id": test_id, "event_type": "tab_switch"}, headers=student_headers)
    assert res.status_code == 200
    ev2 = res.json()
    assert ev2["student_state"] == "ACTIVE" and not ev2["is_blocked"]
    print(f"[OK] 2-chi tab_switch: Ikkinchi ogohlantirish (Sanog'i: {ev2['current_count']})")

    # 4.4 O'quvchi 3-marta chiqdi -> LIMITGA YETDI -> BLOKLANDI!
    res = client.post("/api/proctoring/event", json={"test_id": test_id, "event_type": "tab_switch"}, headers=student_headers)
    assert res.status_code == 200
    ev3 = res.json()
    assert ev3["is_blocked"] is True and ev3["student_state"] == "BLOCKED"
    print(f"[OK] 3-chi tab_switch: Limitga yetdi! O'quvchi BLOKLANDI: {ev3['message']}")

    # 4.5 Bloklangan o'quvchi yangi javob yubora olmaydi
    submit_attempt = client.post("/api/student/test/submit", json={
        "test_id": test_id,
        "answers": {str(questions[0]["id"]): questions[0]["options"][0]["id"]},
        "tab_switch_count": 3,
        "time_spent_seconds": 30
    }, headers=student_headers)
    assert submit_attempt.status_code == 403, "Bloklangan o'quvchi javob yubora olmasligi kerak edi"
    print("[OK] Bloklangan o'quvchidan javob qabul qilinmadi (403 Bloklangan).")

    # 4.6 Admin boshqaruv paneli bloklangan o'quvchini ko'radi
    dash_res = client.get(f"/api/proctoring/dashboard/{test_id}", headers=admin_headers)
    assert dash_res.status_code == 200
    dash_data = dash_res.json()
    assert isinstance(dash_data, list) and len(dash_data) >= 1
    assert dash_data[0]["test_state"] == "BLOCKED"
    print(f"[OK] Admin dashboardi bloklangan o'quvchini ko'rsatdi: {dash_data[0]['student_name']} - BLOCKED")

    # 4.7 Admin [ DAVOM ETTIRISH ] (Resume) bosadi
    student_id = student_data["user"]["student_id"]
    resume_res = client.post(f"/api/proctoring/{student_id}/resume?test_id={test_id}", headers=admin_headers)
    assert resume_res.status_code == 200
    print("[OK] Admin [ DAVOM ETTIRISH ] tugmasini bosdi -> O'quvchi yana ACTIVE bo'ldi.")

    print("\n--- 5. JAVOBLARNI TOPSHIRISH VA NATIJANI YASHIRISH (E'LON QILISHDAN OLDIN) ---")
    # 5.1 O'quvchi javoblarni topshiradi
    answers_dict = {}
    for q in questions:
        opt_id = q["options"][0]["id"]
        answers_dict[str(q["id"])] = opt_id

    submit_res = client.post("/api/student/test/submit", json={
        "test_id": test_id,
        "answers": answers_dict,
        "tab_switch_count": 0,
        "time_spent_seconds": 150
    }, headers=student_headers)
    assert submit_res.status_code == 200
    session_result = submit_res.json()
    session_id = session_result["session_id"]
    print(f"[OK] O'quvchi testni topshirdi. Sessiya ID: {session_id}")

    # 5.2 O'quvchi darhol natija so'raganda: BALL VA SAVOLLAR KO'RINMAYDI!
    res_before_publish = client.get(f"/api/student/result/{session_id}", headers=student_headers)
    assert res_before_publish.status_code == 200
    hide_view = res_before_publish.json()
    assert hide_view.get("is_published") is False
    assert "administrator tomonidan tasdiqlangandan keyin" in hide_view.get("message", "")
    assert hide_view.get("score_percent") is None
    assert hide_view.get("correct_answers") is None
    assert hide_view.get("questions") is None
    print(f"[OK] E'londan oldin o'quvchiga ball ko'rinmadi: '{hide_view['message']}'")

    # 5.3 O'quvchi AI tahlilini ham e'londan oldin ololmaydi
    ai_attempt = client.post(f"/api/student/ai-analysis/{session_id}", headers=student_headers)
    assert ai_attempt.status_code == 403
    print("[OK] E'londan oldin AI xulosasi ham berilmaydi (403 - e'lon qilinmagan).")

    print("\n--- 6. ADMIN: YAKUNLASH, TEKSHIRISH, TASDIQLASH VA E'LON QILISH ---")
    # 6.1 Admin: [ TESTNI YAKUNLASH ] -> FINISHED
    fin_res = client.post(f"/api/groups/{group_id}/tests/{test_id}/finish", headers=admin_headers)
    assert fin_res.status_code == 200
    print("[OK] Admin [ TESTNI YAKUNLASH ] bosdi -> Holat: FINISHED.")

    # 6.2 Admin: [ NATIJALARNI KO'RISH ] (Guruh bo'yicha nazorat hodisalari va ballar)
    results_view = client.get(f"/api/admin/tests/{test_id}/group-results", headers=admin_headers)
    assert results_view.status_code == 200
    grp_res = results_view.json()
    assert isinstance(grp_res, list) and len(grp_res) >= 1
    print(f"[OK] Admin guruh natijalarini ko'rdi: {len(grp_res)} ta o'quvchi natijasi: {grp_res[0]['student_name']} ({grp_res[0]['score_percent']}%)")

    # 6.3 Admin: [ NATIJALARNI TASDIQLASH ] -> RESULTS_APPROVED
    appr_res = client.post(f"/api/groups/{group_id}/tests/{test_id}/approve", headers=admin_headers)
    assert appr_res.status_code == 200
    print("[OK] Admin natijalarni tekshirib tasdiqladi -> RESULTS_APPROVED.")

    # 6.4 Admin: [ NATIJALARNI E'LON QILISH ] -> RESULTS_PUBLISHED
    pub_res = client.post(f"/api/groups/{group_id}/tests/{test_id}/publish", headers=admin_headers)
    assert pub_res.status_code == 200
    print("[OK] Admin [ NATIJALARNI E'LON QILISH ] bosdi -> RESULTS_PUBLISHED.")

    # 6.5 Endi o'quvchi o'z natijasini to'liq ko'radi (Backend haqiqat manbai!)
    res_after_publish = client.get(f"/api/student/result/{session_id}", headers=student_headers)
    assert res_after_publish.status_code == 200
    open_view = res_after_publish.json()
    assert open_view.get("is_published") is True
    assert open_view.get("score_percent") is not None
    assert open_view.get("correct_answers") is not None
    assert len(open_view.get("questions", [])) > 0
    print(f"[OK] E'londan keyin o'quvchi natijani ko'rdi: Ball: {open_view['score_percent']}%, To'g'ri: {open_view['correct_answers']}")

    print("\n--- 7. AI QATLAMI (GEMINI): FACT + INTERPRETATION AJRATISH ---")
    ai_res = client.post(f"/api/student/ai-analysis/{session_id}", headers=student_headers)
    assert ai_res.status_code == 200
    ai_data = ai_res.json()
    assert "ai_analysis" in ai_data
    # AI tahlili backend faktlarini o'zgartirmaydi
    print(f"[OK] Gemini AI tahlili qabul qilindi: {ai_data['ai_analysis'][:80]}...")

    print("\n--- 8. TEACHER & ADMIN ROLLI ANALYZERLAR ---")
    # 8.1 Teacher analyzer
    t_an = client.post("/api/ai/analyze/teacher", json={
        "group_stats": {
            "subject": "IT",
            "total_students": 1,
            "total_questions_solved": 12,
            "topics_stats": {"Python sintaksisi": 90.0, "Algoritmlar": 50.0}
        }
    }, headers=teacher_headers)
    assert t_an.status_code == 200
    t_out = t_an.json()
    assert "analysis" in t_out and len(t_out.get("facts", [])) > 0
    print(f"[OK] O'qituvchi tahlili (Teacher Analyzer): Facts={len(t_out.get('facts', []))}, Analysis bor.")

    # 8.2 Admin analyzer
    a_an = client.post("/api/ai/analyze/admin", json={
        "school_stats": {
            "total_groups": 1,
            "total_students": 1,
            "subjects_stats": {"IT": 85.0}
        }
    }, headers=admin_headers)
    assert a_an.status_code == 200
    a_out = a_an.json()
    assert "summary" in a_out
    print(f"[OK] Admin tahlili (Admin Analyzer): Umumiy xulosa muvaffaqiyatli.")

    print("\n--- 9. AUDIT LOG VA KESH (AI AUDIT) ---")
    with get_db() as conn:
        logs = conn.execute("SELECT id, task, model, status FROM ai_audit_log ORDER BY id DESC LIMIT 5").fetchall()
        assert len(logs) > 0, "AI so'rovlari audit logga yozilishi shart"
        print(f"[OK] AI Audit log yozuvlari mavjud: {len(logs)} ta qayd tekshirildi.")

    print("\n--- 10. AI SAVOL GENERATSIYASI VA REVIEWER (QUALITY SCORE >= 0.90) ---")
    gen_res = client.post("/api/ai/generate-questions", json={
        "subject_name": "IT",
        "topic_name": "Python asoslari",
        "count": 2,
        "difficulty": "medium",
        "grade_level": 10
    }, headers=teacher_headers)
    assert gen_res.status_code == 200, f"Savol generatsiyasi xatosi: {gen_res.text}"
    gen_data = gen_res.json()
    assert len(gen_data["questions"]) >= 2
    assert gen_data["quality_score"] >= 0.90
    for q in gen_data["questions"]:
        assert len(q["options"]) == 4, "Har bir savolda aynan 4 ta variant bo'lishi shart"
        correct_opts = [o for o in q["options"] if o.get("is_correct") == 1]
        assert len(correct_opts) == 1, "Aynan 1 ta to'g'ri javob bo'lishi shart"
    print(f"[OK] AI Savol generatsiyasi: {len(gen_data['questions'])} ta savol, Quality Score: {gen_data['quality_score']}, 4 variant, 1 to'g'ri javob.")

    print("\n=====================================================================")
    print("  BARCHA ENTERPRISE ARXITEKTURA VA TALABLAR 100% MUVAFFAQIYATLI O'TDI! ")
    print("=====================================================================")

if __name__ == "__main__":
    test_enterprise_blueprint()
