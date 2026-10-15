from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel
from typing import Dict, Any, Optional
from services.result_service import ResultService
from services.gemini_service import GeminiService
from services.auth_service import require_teacher, require_admin, get_current_user

router = APIRouter(prefix="/api/results", tags=["results"])

class SubmitTestRequest(BaseModel):
    first_name: str
    last_name: str
    group_id: int
    test_id: int
    answers: Dict[str, Any]
    tab_switch_count: Optional[int] = 0
    time_spent_seconds: Optional[int] = 0

@router.post("/submit")
def submit_test(data: SubmitTestRequest, user: dict = Depends(get_current_user)):
    if not data.first_name.strip() or not data.last_name.strip():
        raise HTTPException(status_code=400, detail="Ism va familiya kiritilishi shart")

    try:
        res = ResultService.submit_test(
            first_name=data.first_name,
            last_name=data.last_name,
            group_id=data.group_id,
            test_id=data.test_id,
            answers=data.answers,
            tab_switch_count=data.tab_switch_count or 0,
            time_spent_seconds=data.time_spent_seconds or 0
        )
        return {
            "success": True,
            "attempt_id": res["attempt_id"],
            "score_percent": res["score_percent"],
            "correct_answers": res["correct_answers"],
            "total_questions": res["total_questions"],
            "message": "Test muvaffaqiyatli yakunlandi"
        }
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Testni yakunlashda xatolik yuz berdi: {e}")

@router.get("/{attempt_id}")
def get_result(attempt_id: int, user: dict = Depends(require_teacher)):
    result = ResultService.get_result_detail(attempt_id)
    if not result:
        raise HTTPException(status_code=404, detail="Test natijasi topilmadi")
    return result

@router.get("")
def get_all_results(
    group_id: Optional[int] = Query(None),
    test_id: Optional[int] = Query(None),
    search: Optional[str] = Query(None),
    limit: Optional[int] = Query(100),
    user: dict = Depends(require_teacher)
):
    return ResultService.get_all_results(group_id=group_id, test_id=test_id, search=search, limit=limit)

@router.get("/dashboard/stats")
def get_dashboard_stats(user: dict = Depends(require_admin)):
    return ResultService.get_dashboard_stats()

@router.get("/group/stats")
def get_group_stats(group_id: int = Query(...), test_id: int = Query(...), user: dict = Depends(require_teacher)):
    stats = ResultService.get_group_test_stats(group_id, test_id)
    if not stats:
        raise HTTPException(status_code=404, detail="Guruh yoki test ma'lumotlari topilmadi")
    return stats

