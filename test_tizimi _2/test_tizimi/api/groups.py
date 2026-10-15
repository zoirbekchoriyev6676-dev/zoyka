# pyrefly: ignore [missing-import]
from fastapi import APIRouter, HTTPException, Depends
# pyrefly: ignore [missing-import]
from pydantic import BaseModel
from services.test_service import TestService
from services.auth_service import require_admin, get_current_user

router = APIRouter(prefix="/api/groups", tags=["groups"])

class GroupCreate(BaseModel):
    name: str

class GroupUpdate(BaseModel):
    name: str

@router.get("")
def get_groups(user: dict = Depends(get_current_user)):
    return TestService.get_all_groups()

@router.post("")
def create_group(data: GroupCreate, admin: dict = Depends(require_admin)):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Guruh nomi bo'sh bo'lishi mumkin emas")
    try:
        group_id = TestService.create_group(data.name)
        return {"id": group_id, "name": data.name, "message": "Guruh muvaffaqiyatli yaratildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Guruh yaratishda xatolik (bunday guruh mavjud bo'lishi mumkin): {e}")

@router.put("/{group_id}")
def update_group(group_id: int, data: GroupUpdate, admin: dict = Depends(require_admin)):
    if not data.name.strip():
        raise HTTPException(status_code=400, detail="Guruh nomi bo'sh bo'lishi mumkin emas")
    try:
        TestService.update_group(group_id, data.name)
        return {"id": group_id, "name": data.name, "message": "Guruh yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Guruhni tahrirlashda xatolik: {e}")

@router.delete("/{group_id}")
def delete_group(group_id: int, admin: dict = Depends(require_admin)):
    try:
        TestService.delete_group(group_id)
        return {"message": "Guruh o'chirildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Guruhni o'chirishda xatolik: {e}")

# ==================== GURUH TESTLARI STATE MACHINE ====================
@router.post("/{id}/tests/{tid}/start")
def start_group_test(id: int, tid: int, admin: dict = Depends(require_admin)):
    """Admin guruh uchun testni boshlaydi (DRAFT/READY -> STARTED)."""
    try:
        res = TestService.transition_test_state(
            test_id=tid,
            target_state="STARTED",
            group_id=id,
            user_role=admin["role"],
            user_id=admin["id"]
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/tests/{tid}/finish")
def finish_group_test(id: int, tid: int, admin: dict = Depends(require_admin)):
    """Admin guruh uchun testni yakunlaydi (STARTED -> FINISHED)."""
    try:
        res = TestService.transition_test_state(
            test_id=tid,
            target_state="FINISHED",
            group_id=id,
            user_role=admin["role"],
            user_id=admin["id"]
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/tests/{tid}/approve")
def approve_group_test_results(id: int, tid: int, admin: dict = Depends(require_admin)):
    """Admin natijalarni tekshirib tasdiqlaydi (FINISHED -> RESULTS_APPROVED)."""
    try:
        res = TestService.transition_test_state(
            test_id=tid,
            target_state="RESULTS_APPROVED",
            group_id=id,
            user_role=admin["role"],
            user_id=admin["id"]
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/{id}/tests/{tid}/publish")
def publish_group_test_results(id: int, tid: int, admin: dict = Depends(require_admin)):
    """Admin natijalarni e'lon qiladi (RESULTS_APPROVED -> RESULTS_PUBLISHED)."""
    try:
        res = TestService.transition_test_state(
            test_id=tid,
            target_state="RESULTS_PUBLISHED",
            group_id=id,
            user_role=admin["role"],
            user_id=admin["id"]
        )
        return res
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/{id}/tests/{tid}/stats")
def get_group_test_stats(id: int, tid: int, admin: dict = Depends(require_admin)):
    """Guruhning test holati, faol, yakunlagan va bloklangan o'quvchilari statistikasi."""
    return TestService.get_group_test_stats(test_id=tid, group_id=id)

