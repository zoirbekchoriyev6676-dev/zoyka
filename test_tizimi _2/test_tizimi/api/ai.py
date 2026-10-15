from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from services.gemini_service import GeminiService
from services.ai.orchestrator import AIOrchestrator
from services.ai.schemas import GenerateTestRequest, ReviewQuestionRequest
from services.auth_service import get_current_user, require_teacher, require_admin

router = APIRouter(prefix="/api/ai", tags=["ai"])

class SetApiKeyRequest(BaseModel):
    api_key: str

class GenerateQuestionsRequest(BaseModel):
    subject_name: Optional[str] = "IT"
    topic_name: str
    count: Optional[int] = 10
    difficulty: Optional[str] = "medium"
    extra_prompt: Optional[str] = ""
    grade_level: Optional[int] = 10
    points: Optional[int] = 1
    include_explanation: Optional[bool] = True
    source_based: Optional[bool] = False
    material_text: Optional[str] = None

class StudentAnalysisApiRequest(BaseModel):
    result_data: Dict[str, Any]

class TeacherAnalysisApiRequest(BaseModel):
    group_stats: Dict[str, Any]

class AdminAnalysisApiRequest(BaseModel):
    school_stats: Dict[str, Any]

@router.get("/key-status")
def get_key_status(user: dict = Depends(require_teacher)):
    key = GeminiService.get_api_key()
    if not key:
        return {"has_key": False, "masked_key": ""}
    masked = key[:6] + "..." + key[-4:] if len(key) > 10 else "***"
    return {"has_key": True, "masked_key": masked}

@router.post("/set-key")
def set_api_key(data: SetApiKeyRequest, admin: dict = Depends(require_admin)):
    if not data.api_key.strip():
        raise HTTPException(status_code=400, detail="API kaliti bo'sh bo'lishi mumkin emas")
    GeminiService.set_api_key(data.api_key.strip())
    return {"message": "Gemini API kaliti muvaffaqiyatli saqlandi va faollashtirildi!"}

@router.post("/generate-questions")
def generate_questions(data: GenerateQuestionsRequest, user: dict = Depends(require_teacher)):
    if not data.topic_name.strip():
        raise HTTPException(status_code=400, detail="Mavzu nomi kiritilishi shart")

    try:
        req = GenerateTestRequest(
            subject_name=data.subject_name or "IT",
            topic_name=data.topic_name,
            count=data.count or 10,
            difficulty=data.difficulty or "medium",
            grade_level=data.grade_level or 10,
            points=data.points or 1,
            include_explanation=data.include_explanation if data.include_explanation is not None else True,
            extra_prompt=data.extra_prompt or "",
            source_based=bool(data.source_based),
            material_text=data.material_text
        )
        resp = AIOrchestrator.generate_test_pipeline(req)

        # Eski formatni to'liq saqlagan holda yangi maydonlarni ham qaytarish
        return {
            "subject": resp.subject,
            "topic": resp.topic,
            "count": resp.count,
            "quality_score": resp.quality_score,
            "status": resp.status,
            "pipeline_stats": resp.pipeline_stats,
            "questions": [q.model_dump() for q in resp.questions]
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/review-questions")
def review_questions(data: Dict[str, Any], user: dict = Depends(require_teacher)):
    """O'qituvchi tomonidan kiritilgan yoki yuklangan savollarni AI orqali tekshirish."""
    questions = data.get("questions", [])
    subject = data.get("subject", "IT")
    topic = data.get("topic", "Umumiy")
    from services.ai.question_reviewer import QuestionReviewer
    from services.ai.schemas import GeneratedQuestion, QuestionOption
    parsed = []
    for q in questions:
        opts = [QuestionOption(option_text=o.get("option_text", ""), is_correct=o.get("is_correct", 0)) for o in q.get("options", [])]
        parsed.append(GeneratedQuestion(
            question_text=q.get("question_text", ""),
            options=opts,
            explanation=q.get("explanation", "")
        ))
    accepted, rejected, reasons = QuestionReviewer.review_questions(parsed, subject, topic, user_id=user.get("id"))
    return {
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
        "reasons": reasons,
        "accepted": [q.model_dump() for q in accepted]
    }

@router.post("/analyze/student")
def analyze_student(data: StudentAnalysisApiRequest, user: dict = Depends(get_current_user)):
    if user.get("role") == "student":
        req_student_id = data.result_data.get("student_id")
        if req_student_id and req_student_id != user.get("student_id"):
            raise HTTPException(status_code=403, detail="Boshqa o'quvchi natijasini tahlil qilish huquqi yo'q")
    return AIOrchestrator.analyze_student(data.result_data, user_id=user.get("id"))

@router.post("/analyze/teacher")
def analyze_teacher(data: TeacherAnalysisApiRequest, user: dict = Depends(require_teacher)):
    return AIOrchestrator.analyze_group(data.group_stats, user_id=user.get("id"))

@router.post("/analyze/admin")
def analyze_admin(data: AdminAnalysisApiRequest, user: dict = Depends(require_admin)):
    return AIOrchestrator.analyze_school(data.school_stats, user_id=user.get("id"))
