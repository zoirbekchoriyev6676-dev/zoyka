from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Optional, List
from services.test_service import TestService
from services.auth_service import get_current_user, require_teacher, require_admin

router = APIRouter(prefix="/api/tests", tags=["tests"])

class GroupAccessRequest(BaseModel):
    test_id: int
    group_ids: List[int]

class TestCreate(BaseModel):
    title: str
    description: Optional[str] = ""
    duration_minutes: Optional[int] = 30
    passing_score: Optional[int] = 60
    is_active: Optional[int] = 1
    randomize_questions: Optional[int] = 1

class TestUpdate(BaseModel):
    title: str
    description: Optional[str] = ""
    duration_minutes: Optional[int] = 30
    passing_score: Optional[int] = 60
    is_active: Optional[int] = 1
    randomize_questions: Optional[int] = 1

# --- GURUHLAR BO'YICHA TESTGA RUXSAT VA YAKUNLASH ---
@router.post("/grant-access")
def grant_group_access_api(data: GroupAccessRequest, user: dict = Depends(require_teacher)):
    """Admin yoki O'qituvchi tanlangan guruhlar uchun testni boshlaydi."""
    try:
        res = TestService.grant_test_access_to_groups(data.test_id, data.group_ids, user_id=user["id"])
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/stop-access")
def stop_group_access_api(data: GroupAccessRequest, user: dict = Depends(require_teacher)):
    """Admin yoki O'qituvchi testni yakunlaydi va natijalarni e'lon qiladi."""
    try:
        res = TestService.stop_test_access_for_groups(data.test_id, data.group_ids, user_id=user["id"])
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{test_id}/groups-access")
def get_test_groups_access_api(test_id: int, user: dict = Depends(require_teacher)):
    """Test bo'yicha barcha guruhlar va ularning ruxsat holatlari."""
    return TestService.get_test_groups_access(test_id)


@router.get("")
def get_tests(active_only: bool = Query(False), user: dict = Depends(get_current_user)):
    return TestService.get_all_tests(active_only=active_only)

@router.get("/{test_id}")
def get_test(test_id: int, user: dict = Depends(get_current_user)):
    test = TestService.get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    return test

@router.post("")
def create_test(data: TestCreate, user: dict = Depends(require_teacher)):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Test sarlavhasi kiritilishi shart")
    try:
        test_id = TestService.create_test(
            title=data.title,
            description=data.description or "",
            duration_minutes=data.duration_minutes or 30,
            passing_score=data.passing_score or 60,
            is_active=1 if data.is_active is None or data.is_active else 0,
            randomize_questions=1 if data.randomize_questions is None or data.randomize_questions else 0
        )
        return {"id": test_id, "message": "Test muvaffaqiyatli yaratildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Test yaratishda xatolik: {e}")

def _verify_test_ownership(test_id: int, user: dict) -> bool:
    if user.get("role") == "admin":
        return True
    teacher_id = user.get("teacher_id")
    if not teacher_id:
        return False
    from database.db import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT t.id FROM tests t
            JOIN teacher_assignments ta ON ta.id = t.assignment_id
            WHERE t.id = ? AND ta.teacher_id = ?
        """, (test_id, teacher_id))
        return cursor.fetchone() is not None
    finally:
        conn.close()

def _verify_student_test_access(student_id: int, test_id: int) -> bool:
    from database.db import get_db_connection
    conn = get_db_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT 1 FROM students st
            JOIN teacher_assignments ta ON ta.group_id = st.group_id
            JOIN tests t ON t.assignment_id = ta.id
            WHERE st.id = ? AND t.id = ?
        """, (student_id, test_id))
        if cursor.fetchone():
            return True
        cursor.execute("""
            SELECT 1 FROM students st
            JOIN test_groups_access tga ON tga.group_id = st.group_id
            WHERE st.id = ? AND tga.test_id = ?
        """, (student_id, test_id))
        return cursor.fetchone() is not None
    finally:
        conn.close()

@router.put("/{test_id}")
def update_test(test_id: int, data: TestUpdate, user: dict = Depends(require_teacher)):
    if not data.title.strip():
        raise HTTPException(status_code=400, detail="Test sarlavhasi bo'sh bo'lishi mumkin emas")
    if not _verify_test_ownership(test_id, user):
        raise HTTPException(status_code=403, detail="Sizda ushbu testni tahrirlash huquqi yo'q (faqat o'z testlaringizni tahrirlashingiz mumkin)")
    try:
        TestService.update_test(
            test_id=test_id,
            title=data.title,
            description=data.description or "",
            duration_minutes=data.duration_minutes or 30,
            passing_score=data.passing_score or 60,
            is_active=1 if data.is_active else 0,
            randomize_questions=1 if data.randomize_questions else 0
        )
        return {"id": test_id, "message": "Test muvaffaqiyatli yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Testni yangilashda xatolik: {e}")

@router.delete("/{test_id}")
def delete_test(test_id: int, user: dict = Depends(require_teacher)):
    if not _verify_test_ownership(test_id, user):
        raise HTTPException(status_code=403, detail="Sizda ushbu testni o'chirish huquqi yo'q (faqat o'z testlaringizni o'chirishingiz mumkin)")
    try:
        TestService.delete_test(test_id)
        return {"message": "Test va unga tegishli savollar o'chirildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Testni o'chirishda xatolik: {e}")

@router.get("/{test_id}/student-questions")
def get_student_questions(test_id: int, user: dict = Depends(get_current_user)):
    """O'quvchi test ishlashi uchun savollar (to'g'ri javoblar ko'rsatilmaydi)."""
    test = TestService.get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    if not test["is_active"]:
        raise HTTPException(status_code=403, detail="Ushbu test hozirda faol emas")

    # Agar so'rov yuboruvchi o'quvchi bo'lsa: guruh va holat tekshiruvi
    if user.get("role") == "student":
        student_id = user.get("student_id")
        if not student_id or not _verify_student_test_access(student_id, test_id):
            raise HTTPException(status_code=403, detail="Siz ushbu test biriktirilgan guruhga kirmaysiz")

        from database.db import get_db_connection
        conn = get_db_connection()
        try:
            cursor = conn.cursor()
            cursor.execute("SELECT status, block_reason FROM student_test_state WHERE student_id = ? AND test_id = ?", (student_id, test_id))
            st_state = cursor.fetchone()
            if st_state and st_state["status"] == "BLOCKED":
                raise HTTPException(status_code=403, detail=f"Sizning testingiz bloklangan ({st_state['block_reason'] or 'Qoidabuzarlik'}). Administrator qarorini kuting.")
        finally:
            conn.close()

    questions = TestService.get_test_questions_for_student(test_id)
    return {
        "test": {
            "id": test["id"],
            "title": test["title"],
            "description": test.get("description", ""),
            "duration_minutes": test["duration_minutes"],
            "passing_score": test["passing_score"],
            "question_count": len(questions)
        },
        "questions": questions
    }

@router.get("/{test_id}/admin-questions")
def get_admin_questions(test_id: int, user: dict = Depends(require_teacher)):
    """Admin/o'qituvchi uchun savollar (barcha to'g'ri javoblari va izohlari bilan)."""
    test = TestService.get_test_by_id(test_id)
    if not test:
        raise HTTPException(status_code=404, detail="Test topilmadi")
    questions = TestService.get_test_questions_for_admin(test_id)
    return {
        "test": test,
        "questions": questions
    }

