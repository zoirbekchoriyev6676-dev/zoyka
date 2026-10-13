import sys
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from main import app
from database.db import init_db, seed_enterprise_data

client = TestClient(app)

def test_system():
    print("\n--- 1. Baza va foydalanuvchilar autentifikatsiyasi ---")
    # Login qilish
    admin_login = client.post("/api/auth/login", json={"identifier": "zoir", "secret": "zoir"})
    assert admin_login.status_code == 200, f"Admin login xatosi: {admin_login.text}"
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}
    print("[OK] Admin autentifikatsiyadan o'tdi.")

    teacher_login = client.post("/api/auth/login", json={"identifier": "wolking", "secret": "wolking"})
    assert teacher_login.status_code == 200, f"Teacher login xatosi: {teacher_login.text}"
    teacher_token = teacher_login.json()["token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}
    print("[OK] O'qituvchi autentifikatsiyadan o'tdi.")

    student_login = client.post("/api/auth/login", json={"identifier": "Ali_7309", "secret": "7309"})
    assert student_login.status_code == 200, f"Student login xatosi: {student_login.text}"
    student_token = student_login.json()["token"]
    student_headers = {"Authorization": f"Bearer {student_token}"}
    print("[OK] O'quvchi autentifikatsiyadan o'tdi.")

    print("\n--- 2. Guruhlarni tekshirish ---")
    res = client.get("/api/groups", headers=admin_headers)
    assert res.status_code == 200
    groups = res.json()
    assert len(groups) > 0
    print(f"[OK] Guruhlar soni: {len(groups)}")

    print("\n--- 3. Testlar ro'yxatini tekshirish (/api/tests) ---")
    res = client.get("/api/tests", headers=admin_headers)
    assert res.status_code == 200
    tests = res.json()
    test_id = next((t["id"] for t in tests if t["id"] == 1), tests[0]["id"])
    print(f"[OK] Testlar mavjud: {len(tests)} ta. Tanlangan test ID: {test_id}")

    print("\n--- 4. Test savollarini olish va xavfsizlik tekshiruvi ---")
    # Student savollari: is_correct bo'lmasligi kerak
    res = client.get(f"/api/tests/{test_id}/student-questions", headers=student_headers)
    assert res.status_code == 200
    st_data = res.json()
    questions = st_data["questions"]
    assert len(questions) > 0
    assert "is_correct" not in questions[0]["options"][0]
    print(f"[OK] O'quvchi uchun {len(questions)} ta savol yuklandi (to'g'ri javoblar yashirilgan).")

    # Admin/Teacher savollari: is_correct bo'lishi kerak
    res_adm = client.get(f"/api/tests/{test_id}/admin-questions", headers=teacher_headers)
    assert res_adm.status_code == 200
    adm_questions = res_adm.json()["questions"]
    assert "is_correct" in adm_questions[0]["options"][0]
    print("[OK] O'qituvchi/Admin uchun barcha variantlar to'g'ri javoblari bilan ko'rinmoqda.")

    # Anonim foydalanuvchi admin-questions ga kira olmasligi shart (401)
    anon_res = client.get(f"/api/tests/{test_id}/admin-questions")
    assert anon_res.status_code == 401
    print("[OK] Himoyalangan yo'llar anonim kirishni 401 bilan rad etdi.")

    print("\n--- 5. Test holati (State Machine) tekshiruvi ---")
    group_id = groups[0]["id"]
    st_res = client.get(f"/api/groups/{group_id}/tests/{test_id}/stats", headers=admin_headers)
    assert st_res.status_code == 200
    print(f"[OK] Test guruhi statistikasi muvaffaqiyatli olindi: Holat = {st_res.json().get('status')}")

    print("\n=====================================================================")
    print("  TEST VERIFICATION: BARCHA TEKSHIRUVLAR MUVAFFAQIYATLI YAKUNLANDI!  ")
    print("=====================================================================")

if __name__ == "__main__":
    test_system()
