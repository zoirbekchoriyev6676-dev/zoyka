from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import List, Optional
from services.test_service import TestService
from services.auth_service import require_teacher

router = APIRouter(prefix="/api/questions", tags=["questions"])

class OptionModel(BaseModel):
    option_text: str
    is_correct: int = 0

class QuestionCreate(BaseModel):
    test_id: int
    topic_id: int
    question_text: str
    difficulty: Optional[str] = "medium"
    explanation: Optional[str] = ""
    options: List[OptionModel]

class QuestionUpdate(BaseModel):
    topic_id: int
    question_text: str
    difficulty: Optional[str] = "medium"
    explanation: Optional[str] = ""
    options: List[OptionModel]

class BatchQuestionItem(BaseModel):
    topic_id: Optional[int] = None
    question_text: str
    difficulty: Optional[str] = "medium"
    explanation: Optional[str] = ""
    options: List[OptionModel]

class BatchQuestionCreate(BaseModel):
    test_id: int
    default_topic_id: int
    questions: List[BatchQuestionItem]

@router.post("")
def create_question(data: QuestionCreate, user: dict = Depends(require_teacher)):
    if not data.question_text.strip():
        raise HTTPException(status_code=400, detail="Savol matni kiritilishi shart")
    if len(data.options) < 2:
        raise HTTPException(status_code=400, detail="Kamida 2 ta javob varianti bo'lishi kerak")
    
    # Hech bo'lmaganda bitta to'g'ri javob bormi?
    has_correct = any(opt.is_correct == 1 for opt in data.options)
    if not has_correct:
        raise HTTPException(status_code=400, detail="Kamida bitta to'g'ri javob belgilanmagan")

    try:
        q_id = TestService.create_question(
            test_id=data.test_id,
            topic_id=data.topic_id,
            question_text=data.question_text,
            difficulty=data.difficulty or "medium",
            explanation=data.explanation or "",
            options=[opt.dict() for opt in data.options]
        )
        return {"id": q_id, "message": "Savol muvaffaqiyatli saqlandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Savol qo'shishda xatolik: {e}")

@router.put("/{question_id}")
def update_question(question_id: int, data: QuestionUpdate, user: dict = Depends(require_teacher)):
    if not data.question_text.strip():
        raise HTTPException(status_code=400, detail="Savol matni bo'sh bo'lishi mumkin emas")
    if len(data.options) < 2:
        raise HTTPException(status_code=400, detail="Kamida 2 ta javob varianti bo'lishi kerak")

    has_correct = any(opt.is_correct == 1 for opt in data.options)
    if not has_correct:
        raise HTTPException(status_code=400, detail="Kamida bitta to'g'ri javob tanlanishi kerak")

    try:
        TestService.update_question(
            question_id=question_id,
            topic_id=data.topic_id,
            question_text=data.question_text,
            difficulty=data.difficulty or "medium",
            explanation=data.explanation or "",
            options=[opt.dict() for opt in data.options]
        )
        return {"id": question_id, "message": "Savol muvaffaqiyatli yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Savolni tahrirlashda xatolik: {e}")

@router.delete("/{question_id}")
def delete_question(question_id: int, user: dict = Depends(require_teacher)):
    try:
        TestService.delete_question(question_id)
        return {"message": "Savol o'chirildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Savolni o'chirishda xatolik: {e}")

@router.post("/batch")
def create_batch_questions(data: BatchQuestionCreate, user: dict = Depends(require_teacher)):
    """AI orqali yaratilgan yoki import qilingan bir nechta savollarni birdaniga testga qo'shish."""
    if not data.questions:
        raise HTTPException(status_code=400, detail="Qo'shish uchun savollar mavjud emas")

    created_ids = []
    try:
        for q in data.questions:
            topic_id = q.topic_id if q.topic_id else data.default_topic_id
            qid = TestService.create_question(
                test_id=data.test_id,
                topic_id=topic_id,
                question_text=q.question_text,
                difficulty=q.difficulty or "medium",
                explanation=q.explanation or "",
                options=[opt.dict() for opt in q.options]
            )
            created_ids.append(qid)

        return {
            "created_count": len(created_ids),
            "message": f"{len(created_ids)} ta savol muvaffaqiyatli saqlandi!"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Savollarni saqlashda xatolik: {e}")

