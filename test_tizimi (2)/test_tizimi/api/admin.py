from fastapi import APIRouter, HTTPException, Depends, Query
from pydantic import BaseModel
from typing import Optional
from services.auth_service import require_admin
from services.admin_service import AdminService
from services.gemini_service import GeminiService

router = APIRouter(prefix="/api/admin", tags=["admin"])

# --- Pydantic Schemas ---
class TeacherCreateRequest(BaseModel):
    full_name: str
    username: str
    password: str
    specialty: Optional[str] = ""
    phone: Optional[str] = ""

class StudentCreateRequest(BaseModel):
    full_name: str
    username: str
    password: str
    group_id: int
    student_code: str
    pin: str
    phone: Optional[str] = ""

class StudentUpdateRequest(BaseModel):
    full_name: Optional[str] = None
    username: Optional[str] = None
    group_id: Optional[int] = None
    student_code: Optional[str] = None
    pin: Optional[str] = None
    phone: Optional[str] = None
    password: Optional[str] = None
    is_active: Optional[int] = None

class SubjectCreateRequest(BaseModel):
    name: str
    code: str
    description: Optional[str] = ""

class GroupCreateRequest(BaseModel):
    name: str
    academic_year: Optional[str] = "2026/2027"

class AssignmentCreateRequest(BaseModel):
    teacher_id: int
    subject_id: int
    group_id: int
    academic_year: Optional[str] = "2026/2027"
    semester: Optional[int] = 1

# --- Routes ---
@router.get("/dashboard")
def get_dashboard(admin: dict = Depends(require_admin)):
    return AdminService.get_dashboard_stats()

# O'qituvchilar
@router.get("/teachers")
def get_teachers(admin: dict = Depends(require_admin)):
    return AdminService.get_teachers()

@router.post("/teachers")
def create_teacher(data: TeacherCreateRequest, admin: dict = Depends(require_admin)):
    try:
        t_id = AdminService.create_teacher(
            full_name=data.full_name,
            username=data.username,
            password=data.password,
            specialty=data.specialty or "",
            phone=data.phone or ""
        )
        return {"id": t_id, "message": "O'qituvchi muvaffaqiyatli qo'shildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"O'qituvchi qo'shishda xatolik (bunday login mavjud bo'lishi mumkin): {e}")

@router.post("/toggle-user/{user_id}")
def toggle_user(user_id: int, admin: dict = Depends(require_admin)):
    AdminService.toggle_user_active(user_id)
    return {"message": "Foydalanuvchi holati o'zgartirildi"}

# O'quvchilar
@router.get("/students")
def get_students(group_id: Optional[int] = Query(None), search: Optional[str] = Query(None), admin: dict = Depends(require_admin)):
    return AdminService.get_students(group_id=group_id, search=search)

@router.post("/students")
def create_student(data: StudentCreateRequest, admin: dict = Depends(require_admin)):
    try:
        s_id = AdminService.create_student(
            full_name=data.full_name,
            username=data.username,
            password=data.password,
            group_id=data.group_id,
            student_code=data.student_code,
            pin=data.pin,
            phone=data.phone or ""
        )
        return {"id": s_id, "message": "O'quvchi muvaffaqiyatli qo'shildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"O'quvchi qo'shishda xatolik: {e}")

@router.put("/students/{student_id}")
def update_student(student_id: int, data: StudentUpdateRequest, admin: dict = Depends(require_admin)):
    try:
        AdminService.update_student(
            student_id=student_id,
            full_name=data.full_name,
            username=data.username,
            group_id=data.group_id,
            student_code=data.student_code,
            pin=data.pin,
            phone=data.phone,
            password=data.password,
            is_active=data.is_active
        )
        return {"success": True, "message": "O'quvchi ma'lumotlari muvaffaqiyatli yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"O'quvchini yangilashda xatolik: {e}")

@router.get("/students/search")
def search_students(q: str = Query(..., min_length=1), admin: dict = Depends(require_admin)):
    return AdminService.search_students_global(q)

@router.get("/students/{student_id}/profile")
def get_student_profile(student_id: int, admin: dict = Depends(require_admin)):
    profile = AdminService.get_student_profile(student_id)
    if not profile:
        raise HTTPException(status_code=404, detail="O'quvchi topilmadi")
    return profile

@router.get("/groups-with-stats")
def get_groups_with_stats(admin: dict = Depends(require_admin)):
    return AdminService.get_groups_with_stats()

@router.get("/groups/{group_id}/detail")
def get_group_detail(group_id: int, admin: dict = Depends(require_admin)):
    detail = AdminService.get_group_detail(group_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Guruh topilmadi")
    return detail

# Fanlar
@router.get("/subjects")
def get_subjects(admin: dict = Depends(require_admin)):
    return AdminService.get_subjects()

@router.post("/subjects")
def create_subject(data: SubjectCreateRequest, admin: dict = Depends(require_admin)):
    try:
        sub_id = AdminService.create_subject(name=data.name, code=data.code, description=data.description or "")
        return {"id": sub_id, "message": "Fan muvaffaqiyatli qo'shildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Fan qo'shishda xatolik: {e}")

# Guruhlar
@router.get("/groups")
def get_groups(admin: dict = Depends(require_admin)):
    return AdminService.get_groups()

@router.post("/groups")
def create_group(data: GroupCreateRequest, admin: dict = Depends(require_admin)):
    try:
        g_id = AdminService.create_group(name=data.name, academic_year=data.academic_year or "2026/2027")
        return {"id": g_id, "message": "Guruh muvaffaqiyatli yaratildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Guruh yaratishda xatolik: {e}")

# Biriktirishlar (Assignments)
@router.get("/assignments")
def get_assignments(admin: dict = Depends(require_admin)):
    return AdminService.get_assignments()

@router.post("/assignments")
def create_assignment(data: AssignmentCreateRequest, admin: dict = Depends(require_admin)):
    try:
        a_id = AdminService.create_assignment(
            teacher_id=data.teacher_id,
            subject_id=data.subject_id,
            group_id=data.group_id,
            academic_year=data.academic_year or "2026/2027",
            semester=data.semester or 1
        )
        return {"id": a_id, "message": "Biriktirish muvaffaqiyatli saqlandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Biriktirishda xatolik: {e}")

@router.delete("/assignments/{assignment_id}")
def delete_assignment(assignment_id: int, admin: dict = Depends(require_admin)):
    AdminService.delete_assignment(assignment_id)
    return {"message": "Biriktirish o'chirildi"}

# Audit Logs
@router.get("/audit-logs")
def get_audit_logs(admin: dict = Depends(require_admin)):
    return AdminService.get_audit_logs(limit=50)

# Maktab bo'yicha Institutsional AI tahlili
@router.post("/ai-school-report")
def get_school_ai_report(admin: dict = Depends(require_admin)):
    stats = AdminService.get_dashboard_stats()
    report_text = GeminiService.analyze_school_overview(stats)
    return {"report": report_text}

# Test Nazorati va State Machine
@router.get("/tests-control")
def get_tests_for_control(admin: dict = Depends(require_admin)):
    return AdminService.get_admin_tests_for_control()

@router.get("/tests/{test_id}/group-results")
def get_test_group_results(test_id: int, admin: dict = Depends(require_admin)):
    return AdminService.get_test_group_results(test_id)

class AdminGroupAccessRequest(BaseModel):
    test_id: int
    group_ids: list

@router.post("/tests/grant-access")
def admin_grant_test_access(data: AdminGroupAccessRequest, admin: dict = Depends(require_admin)):
    from services.test_service import TestService
    try:
        return TestService.grant_test_access_to_groups(data.test_id, data.group_ids, user_id=admin["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tests/stop-access")
def admin_stop_test_access(data: AdminGroupAccessRequest, admin: dict = Depends(require_admin)):
    from services.test_service import TestService
    try:
        return TestService.stop_test_access_for_groups(data.test_id, data.group_ids, user_id=admin["id"])
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/tests/{test_id}/groups-access")
def admin_get_test_groups_access(test_id: int, admin: dict = Depends(require_admin)):
    from services.test_service import TestService
    return TestService.get_test_groups_access(test_id)


