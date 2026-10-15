import sys
sys.stdout.reconfigure(encoding='utf-8')
from fastapi.testclient import TestClient
from main import app
from database.db import init_db, seed_enterprise_data
from services.result_service import ResultService

client = TestClient(app)

def test_result_service():
    print("=====================================================================")
    print("  RESULT SERVICE & API/RESULTS MODERNIZATION TEKSHIRUVI              ")
    print("=====================================================================")

    # Login
    teacher_login = client.post("/api/auth/login", json={"identifier": "wolking", "secret": "wolking"})
    assert teacher_login.status_code == 200
    teacher_token = teacher_login.json()["token"]
    teacher_headers = {"Authorization": f"Bearer {teacher_token}"}

    admin_login = client.post("/api/auth/login", json={"identifier": "zoir", "secret": "zoir"})
    assert admin_login.status_code == 200
    admin_token = admin_login.json()["token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 1. Dashboard stats
    stats = ResultService.get_dashboard_stats()
    assert "total_students" in stats
    assert "total_tests" in stats
    print(f"[OK] ResultService.get_dashboard_stats() muvaffaqiyatli: {stats['total_students']} o'quvchi, {stats['total_tests']} test.")

    # 2. API /api/results/dashboard/stats
    resp = client.get("/api/results/dashboard/stats", headers=admin_headers)
    assert resp.status_code == 200
    assert "total_students" in resp.json()
    print("[OK] GET /api/results/dashboard/stats 200 OK qaytardi.")

    # 3. GET /api/results (barcha natijalar)
    resp = client.get("/api/results", headers=teacher_headers)
    assert resp.status_code == 200
    print(f"[OK] GET /api/results 200 OK qaytardi: {len(resp.json())} ta natija.")

    # 4. Group test stats
    group_stats = ResultService.get_group_test_stats(group_id=1, test_id=1)
    assert group_stats is not None
    assert group_stats["group_name"] == "10-A"
    print(f"[OK] ResultService.get_group_test_stats() muvaffaqiyatli: Guruh = {group_stats['group_name']}.")

    # 5. GET /api/results/group/stats?group_id=1&test_id=1
    resp = client.get("/api/results/group/stats?group_id=1&test_id=1", headers=teacher_headers)
    assert resp.status_code == 200
    assert resp.json()["group_name"] == "10-A"
    print("[OK] GET /api/results/group/stats 200 OK qaytardi.")

    print("\n=====================================================================")
    print("  RESULT SERVICE TEKSHIRUVI 100% MUVAFFAQIYATLI O'TDI!               ")
    print("=====================================================================")

if __name__ == "__main__":
    test_result_service()
