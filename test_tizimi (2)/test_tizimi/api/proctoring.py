from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional, Dict, Any
from services.test_service import TestService
from services.auth_service import get_current_user, require_admin, require_student

router = APIRouter(prefix="/api/proctoring", tags=["proctoring"])

class ProctoringEventRequest(BaseModel):
    test_id: int
    event_type: str
    details: Optional[str] = ""
    session_id: Optional[int] = None

class ProctoringSettingsRequest(BaseModel):
    tab_switch_limit: Optional[int] = 3
    fullscreen_limit: Optional[int] = 3
    reload_limit: Optional[int] = 3
    face_lost_limit: Optional[int] = 5
    multiple_faces_limit: Optional[int] = 2
    enable_camera: Optional[int] = 0
    camera_policy: Optional[str] = "allow_without_camera"
    track_exit: Optional[int] = 1
    track_suspicious: Optional[int] = 1

@router.post("/event")
def report_proctoring_event(data: ProctoringEventRequest, user: dict = Depends(get_current_user)):
    """
    O'quvchi tomonidan yuz bergan nazorat hodisasini (oyna almashishi, fullscreen chiqishi,
    sahifa yangilanishi, yuz yo'qolishi) serverga yuborish.
    Barcha limitlar va hisoblagichlar serverda boshqariladi.
    """
    student_id = user.get("student_id")
    if not student_id:
        raise HTTPException(status_code=400, detail="Faqat o'quvchi hisobidan hodisa yuborish mumkin")

    try:
        res = TestService.record_proctoring_event(
            test_id=data.test_id,
            student_id=student_id,
            event_type=data.event_type,
            details=data.details or "",
            session_id=data.session_id
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Hodisani qayd qilishda xatolik: {e}")

@router.get("/status/{test_id}")
def get_student_test_status(test_id: int, user: dict = Depends(require_student)):
    """O'quvchining joriy test holati (ACTIVE / BLOCKED / FINISHED)."""
    student_id = user.get("student_id")
    from database.db import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("SELECT status, block_reason FROM student_test_state WHERE student_id = ? AND test_id = ?", (student_id, test_id))
        row = cursor.fetchone()
        return {
            "status": row["status"] if row else "ACTIVE",
            "block_reason": row["block_reason"] if row else None
        }
    finally:
        conn.close()

class ActionStudentRequest(BaseModel):
    test_id: Optional[int] = None

@router.post("/{student}/resume")
def resume_student(student: int, test_id: Optional[int] = Query(None), data: Optional[ActionStudentRequest] = None, admin: dict = Depends(require_admin)):
    """Admin qarori: Bloklangan o'quvchini testga qaytarish (DAVOM ETTIRISH)."""
    tid = test_id or (data.test_id if data else None)
    if not tid:
        raise HTTPException(status_code=400, detail="test_id ko'rsatilishi shart")
    try:
        TestService.resume_student(student_id=student, test_id=tid, admin_user_id=admin["id"])
        return {"success": True, "message": "O'quvchi testga muvaffaqiyatli qaytarildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{student}/terminate")
def terminate_student(student: int, test_id: Optional[int] = Query(None), data: Optional[ActionStudentRequest] = None, admin: dict = Depends(require_admin)):
    """Admin qarori: Bloklangan o'quvchining testini to'xtatish (TESTNI YAKUNLASH)."""
    tid = test_id or (data.test_id if data else None)
    if not tid:
        raise HTTPException(status_code=400, detail="test_id ko'rsatilishi shart")
    try:
        TestService.terminate_student(student_id=student, test_id=tid, admin_user_id=admin["id"])
        return {"success": True, "message": "O'quvchi testi admin tomonidan yakunlandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/dashboard/{test_id}")
def get_proctoring_dashboard(test_id: int, admin: dict = Depends(require_admin)):
    """Admin paneli uchun testdagi barcha o'quvchilar va ularning nazorat hodisalari."""
    return TestService.get_proctoring_dashboard(test_id)

@router.get("/settings/{test_id}")
def get_proctoring_settings(test_id: int, admin: dict = Depends(require_admin)):
    """Test bo'yicha nazorat sozlamalarini olish."""
    return TestService.get_proctoring_settings(test_id)

@router.post("/settings/{test_id}")
def update_proctoring_settings(test_id: int, data: ProctoringSettingsRequest, admin: dict = Depends(require_admin)):
    """Test bo'yicha nazorat sozlamalarini saqlash."""
    TestService.update_proctoring_settings(test_id, data.model_dump())
    return {"success": True, "message": "Nazorat sozlamalari saqlandi"}
