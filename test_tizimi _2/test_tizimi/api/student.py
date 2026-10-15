from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from services.auth_service import require_student
from services.student_service import StudentService
from services.gemini_service import GeminiService
from database.db import get_db_connection

router = APIRouter(prefix="/api/student", tags=["student"])

class SubmitExamRequest(BaseModel):
    test_id: int
    answers: Dict[str, Any]
    tab_switch_count: Optional[int] = 0
    time_spent_seconds: Optional[int] = 0
    monitoring_events: Optional[List[Dict[str, Any]]] = None

@router.get("/my-subjects")
def get_my_subjects(student: dict = Depends(require_student)):
    s_id = student.get("student_id")
    if not s_id:
        raise HTTPException(status_code=400, detail="O'quvchi profili topilmadi")
    return StudentService.get_my_subjects(s_id)

@router.get("/subjects/{subject_id}/exams")
def get_subject_exams(subject_id: int, student: dict = Depends(require_student)):
    s_id = student.get("student_id")
    return StudentService.get_subject_exams(s_id, subject_id)

@router.get("/test/{test_id}")
def get_test_for_solving(test_id: int, student: dict = Depends(require_student)):
    s_id = student.get("student_id")
    try:
        return StudentService.get_test_for_solving(s_id, test_id)
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Xatolik: {e}")

@router.post("/test/submit")
def submit_exam(data: SubmitExamRequest, student: dict = Depends(require_student)):
    s_id = student.get("student_id")
    try:
        res = StudentService.submit_exam(
            student_id=s_id,
            test_id=data.test_id,
            answers=data.answers,
            tab_switch_count=data.tab_switch_count or 0,
            time_spent_seconds=data.time_spent_seconds or 0,
            monitoring_events=data.monitoring_events
        )
        return res
    except ValueError as ve:
        raise HTTPException(status_code=403, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Testni topshirishda xatolik: {e}")

@router.get("/result/{session_id}")
def get_session_result(session_id: int, student: dict = Depends(require_student)):
    res = StudentService.get_session_result(session_id, is_admin_or_teacher=False)
    if not res:
        raise HTTPException(status_code=404, detail="Natija topilmadi")
    s_id = student.get("student_id")
    if res.get("student_id") != s_id:
        raise HTTPException(status_code=403, detail="Ushbu natijani ko'rish uchun ruxsat yo'q")
    return res

@router.get("/learning-map")
def get_learning_map(student: dict = Depends(require_student)):
    s_id = student.get("student_id")
    lmap = StudentService.get_student_learning_map(s_id)
    if not lmap:
        raise HTTPException(status_code=404, detail="Ta'lim xaritasi ma'lumotlari topilmadi")
    return lmap

@router.post("/ai-analysis/{session_id}")
def get_student_ai_analysis(session_id: int, force_regenerate: bool = Query(False), student: dict = Depends(require_student)):
    res = StudentService.get_session_result(session_id, is_admin_or_teacher=False)
    if not res:
        raise HTTPException(status_code=404, detail="Imtihon natijasi topilmadi")

    s_id = student.get("student_id")
    if res.get("student_id") != s_id:
        raise HTTPException(status_code=403, detail="Ushbu natija AI tahlilini ko'rish uchun ruxsat yo'q")

    if not res.get("is_published", True):
        raise HTTPException(status_code=403, detail="Natija e'lon qilinmaguncha AI xulosasi ko'rsatilmaydi")

    if res.get("ai_analysis") and not force_regenerate:
        return {"ai_analysis": res["ai_analysis"], "cached": True}

    ai_text = GeminiService.analyze_student_result(res)

    # Natijani bazaga saqlash
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("UPDATE exam_sessions SET ai_analysis = ? WHERE id = ?", (ai_text, session_id))
        conn.commit()
    finally:
        conn.close()

    return {"ai_analysis": ai_text, "cached": False}
