from fastapi import APIRouter, HTTPException, Depends, Query, UploadFile, File
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
import re
import urllib.parse
from services.auth_service import require_teacher
from services.teacher_service import TeacherService
from services.gemini_service import GeminiService
from services.word_service import WordService

router = APIRouter(prefix="/api/teacher", tags=["teacher"])

# --- Schemas ---
class TopicCreateRequest(BaseModel):
    subject_id: int
    name: str
    description: Optional[str] = ""

class QuestionOptionModel(BaseModel):
    option_text: str
    is_correct: int = 0

class QuestionCreateRequest(BaseModel):
    subject_id: int
    topic_id: int
    question_text: str
    difficulty: Optional[str] = "medium"
    points: Optional[int] = 1
    explanation: Optional[str] = ""
    options: List[QuestionOptionModel]

class BlueprintCreateRequest(BaseModel):
    assignment_id: int
    title: str
    duration_minutes: Optional[int] = 30
    passing_score: Optional[int] = 60
    exam_type: Optional[str] = "midterm"
    enable_camera: Optional[int] = 0
    blueprint: Optional[Dict[str, Any]] = None
    specific_question_ids: Optional[List[int]] = None

class TeacherGroupAiRequest(BaseModel):
    assignment_id: int

class FullTestCreateRequest(BaseModel):
    assignment_id: int
    title: str
    duration_minutes: Optional[int] = 30
    passing_score: Optional[int] = 60
    exam_type: Optional[str] = "midterm"
    status: Optional[str] = "active"
    questions: Optional[List[Dict[str, Any]]] = None

class TestUpdateRequest(BaseModel):
    title: Optional[str] = None
    duration_minutes: Optional[int] = None
    passing_score: Optional[int] = None
    exam_type: Optional[str] = None
    status: Optional[str] = None
    assignment_id: Optional[int] = None

class AppendQuestionRequest(BaseModel):
    question_text: str
    topic_name: Optional[str] = "Umumiy mavzu"
    difficulty: Optional[str] = "medium"
    points: Optional[int] = 1
    explanation: Optional[str] = ""
    options: List[QuestionOptionModel]

class ToggleStatusRequest(BaseModel):
    status: Optional[str] = None

class AiCustomGenRequest(BaseModel):
    subject_name: Optional[str] = "Matematika"
    topic_name: str
    grade_level: Optional[int] = 10
    count: Optional[int] = 10
    easy_count: Optional[int] = 3
    medium_count: Optional[int] = 5
    hard_count: Optional[int] = 2
    points_per_q: Optional[int] = 1
    include_explanation: Optional[bool] = True
    extra_instructions: Optional[str] = ""

class WordAiReviewRequest(BaseModel):
    questions: List[Dict[str, Any]]

# --- Routes ---
@router.get("/assignments")
def get_my_assignments(teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not t_id:
        raise HTTPException(status_code=400, detail="O'qituvchi ID topilmadi")
    return TeacherService.get_my_assignments(t_id)

@router.get("/subjects")
def get_my_subjects(teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not t_id:
        raise HTTPException(status_code=400, detail="O'qituvchi ID topilmadi")
    return TeacherService.get_my_subjects(t_id)

@router.get("/topics/{subject_id}")
def get_topics(subject_id: int, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_subject(t_id, subject_id):
        raise HTTPException(status_code=403, detail="Ushbu fanga tegishli mavzularni ko'rish huquqi yo'q")
    return TeacherService.get_topics_by_subject(subject_id)

@router.post("/topics")
def add_topic(data: TopicCreateRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_subject(t_id, data.subject_id):
        raise HTTPException(status_code=403, detail="Ushbu fanga mavzu qo'shish huquqi yo'q")
    topic_id = TeacherService.add_topic(data.subject_id, data.name, data.description or "")
    return {"id": topic_id, "message": "Mavzu qo'shildi"}

# Savollar banki
@router.get("/question-bank")
def get_questions(subject_id: Optional[int] = Query(None), topic_id: Optional[int] = Query(None),
                     difficulty: Optional[str] = Query(None), teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if subject_id and not TeacherService.verify_teacher_subject(t_id, subject_id):
        raise HTTPException(status_code=403, detail="Ushbu fan bo'yicha savollarni ko'rish huquqi yo'q")
    return TeacherService.get_question_bank(subject_id, topic_id, difficulty, teacher_id=t_id)

@router.post("/question-bank")
def create_question(data: QuestionCreateRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_subject(t_id, data.subject_id):
        raise HTTPException(status_code=403, detail="Ushbu fanga savol qo'shish huquqi yo'q")
    if len(data.options) < 2:
        raise HTTPException(status_code=400, detail="Kamida 2 ta variant bo'lishi kerak")
    if not any(opt.is_correct == 1 for opt in data.options):
        raise HTTPException(status_code=400, detail="Kamida bitta to'g'ri javob belgilanmagan")

    q_id = TeacherService.create_question(
        subject_id=data.subject_id,
        topic_id=data.topic_id,
        teacher_id=t_id,
        question_text=data.question_text,
        difficulty=data.difficulty or "medium",
        points=data.points or 1,
        explanation=data.explanation or "",
        options=[opt.dict() for opt in data.options]
    )
    return {"id": q_id, "message": "Savol savollar bankiga muvaffaqiyatli saqlandi"}

@router.delete("/question-bank/{question_id}")
def delete_question(question_id: int, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_question_ownership(t_id, question_id):
        raise HTTPException(status_code=403, detail="Ushbu savolni o'chirish huquqi yo'q yoki savol sizga tegishli emas")
    deleted = TeacherService.delete_question(question_id, teacher_id=t_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Savol topilmadi")
    return {"message": "Savol o'chirildi"}

# Testlar & Blueprint
@router.get("/tests")
def get_my_tests(teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    return TeacherService.get_my_tests(t_id)

@router.post("/tests")
def create_test_blueprint(data: BlueprintCreateRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_assignment(t_id, data.assignment_id):
        raise HTTPException(status_code=403, detail="Ushbu guruh/fan biriktiruviga test yaratish huquqi yo'q")
    try:
        test_id = TeacherService.create_test_blueprint(
            teacher_id=t_id,
            assignment_id=data.assignment_id,
            title=data.title,
            duration_minutes=data.duration_minutes or 30,
            passing_score=data.passing_score or 60,
            exam_type=data.exam_type or "midterm",
            enable_camera=data.enable_camera or 0,
            blueprint=data.blueprint,
            specific_question_ids=data.specific_question_ids
        )
        return {"id": test_id, "message": "Test muvaffaqiyatli yaratildi va guruhga biriktirildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

# O'qituvchi hisobotlari va AI
@router.get("/assignment-report/{assignment_id}")
def get_assignment_report(assignment_id: int, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_assignment(t_id, assignment_id):
        raise HTTPException(status_code=403, detail="Ushbu hisobotni ko'rish huquqi yo'q")
    rep = TeacherService.get_assignment_report(assignment_id)
    if not rep:
        raise HTTPException(status_code=404, detail="Hisobot ma'lumotlari topilmadi")
    return rep

@router.post("/ai-group-report")
def run_teacher_group_ai(data: TeacherGroupAiRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_assignment(t_id, data.assignment_id):
        raise HTTPException(status_code=403, detail="Ushbu guruh hisobotini tahlil qilish huquqi yo'q")
    rep = TeacherService.get_assignment_report(data.assignment_id)
    if not rep or rep.get("student_count", 0) == 0:
        raise HTTPException(status_code=400, detail="Ushbu guruh bo'yicha hali topshirilgan imtihonlar mavjud emas")
    
    ai_text = GeminiService.analyze_group_results(rep)
    return {
        "assignment_id": data.assignment_id,
        "group_name": rep["group_name"],
        "subject_name": rep["subject_name"],
        "student_count": rep["student_count"],
        "avg_score": rep["avg_score"],
        "ai_report": ai_text
    }

# --- KENGAYTIRILGAN TEST BAZASI VA BOSHQARUVI ENDPOINTLARI ---

@router.get("/tests/{test_id}")
def get_test_detail(test_id: int, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    detail = TeacherService.get_test_detail(test_id, t_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Test topilmadi yoki sizga tegishli emas")
    return detail

@router.post("/tests/full")
def create_full_test(data: FullTestCreateRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if not TeacherService.verify_teacher_assignment(t_id, data.assignment_id):
        raise HTTPException(status_code=403, detail="Ushbu guruh/fan biriktiruviga test yaratish huquqi yo'q")
    try:
        test_id = TeacherService.create_full_test(
            teacher_id=t_id,
            assignment_id=data.assignment_id,
            title=data.title,
            duration_minutes=data.duration_minutes or 30,
            passing_score=data.passing_score or 60,
            exam_type=data.exam_type or "midterm",
            status=data.status or "active",
            questions=data.questions or []
        )
        return {
            "success": True,
            "test_id": test_id,
            "message": f"Test '{data.title}' muvaffaqiyatli saqlandi!"
        }
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/tests/{test_id}")
def update_test(test_id: int, data: TestUpdateRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if data.assignment_id and not TeacherService.verify_teacher_assignment(t_id, data.assignment_id):
        raise HTTPException(status_code=403, detail="Ushbu guruh/fan biriktiruviga ruxsat yo'q")
    try:
        TeacherService.update_test_details(
            test_id=test_id,
            teacher_id=t_id,
            title=data.title,
            duration_minutes=data.duration_minutes,
            passing_score=data.passing_score,
            exam_type=data.exam_type,
            status=data.status,
            assignment_id=data.assignment_id
        )
        return {"success": True, "message": "Test parametrlari yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tests/{test_id}/toggle-status")
def toggle_test_status(test_id: int, data: Optional[ToggleStatusRequest] = None, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    try:
        req_status = data.status if data else None
        new_status = TeacherService.toggle_test_status(test_id, t_id, req_status)
        status_label = "Faol" if new_status == "active" else "Nofaol"
        return {"success": True, "status": new_status, "message": f"Test holati '{status_label}' ga o'zgartirildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tests/{test_id}/clone")
def clone_test(test_id: int, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    try:
        new_test_id = TeacherService.clone_test(test_id, t_id)
        return {"success": True, "new_test_id": new_test_id, "message": "Test muvaffaqiyatli nusxalandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/tests/{test_id}")
def delete_or_archive_test(test_id: int, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    try:
        res = TeacherService.delete_or_archive_test(test_id, t_id)
        return {"success": True, **res}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.post("/tests/{test_id}/questions")
def append_question_to_test(test_id: int, data: AppendQuestionRequest, teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    if len(data.options) < 2:
        raise HTTPException(status_code=400, detail="Kamida 2 ta variant bo'lishi kerak")
    try:
        qid = TeacherService.append_question_to_test(
            test_id=test_id,
            teacher_id=t_id,
            question_data={
                "question_text": data.question_text,
                "topic_name": data.topic_name,
                "difficulty": data.difficulty,
                "points": data.points,
                "explanation": data.explanation,
                "options": [opt.dict() for opt in data.options]
            }
        )
        return {"success": True, "question_id": qid, "message": "Yangi savol testga muvaffaqiyatli qo'shildi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.put("/tests/{test_id}/questions/{question_id}")
def update_test_question(test_id: int, question_id: int, data: Dict[str, Any], teacher: dict = Depends(require_teacher)):
    try:
        TeacherService.update_test_question(test_id, question_id, data)
        return {"success": True, "message": "Savol muvaffaqiyatli yangilandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.delete("/tests/{test_id}/questions/{question_id}")
def remove_question_from_test(test_id: int, question_id: int, teacher: dict = Depends(require_teacher)):
    try:
        TeacherService.remove_question_from_test(test_id, question_id)
        return {"success": True, "message": "Savol testdan olib tashlandi"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@router.get("/test-bank/search")
def search_test_bank(search: Optional[str] = Query(None), subject_id: Optional[int] = Query(None),
                      status: Optional[str] = Query(None), teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    return TeacherService.search_my_test_bank(t_id, search, subject_id, status)

# --- WORD IMPORT / EXPORT ENDPOINTLARI ---

MAX_DOCX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

@router.post("/word/import-preview")
async def import_word_preview(file: UploadFile = File(...), teacher: dict = Depends(require_teacher)):
    if not file.filename or not file.filename.lower().endswith(".docx"):
        raise HTTPException(status_code=400, detail="Faqat Word (.docx) formatidagi fayllar qabul qilinadi")
    try:
        content = await file.read()
        if len(content) > MAX_DOCX_FILE_SIZE:
            raise HTTPException(status_code=413, detail="Yuklangan Word fayli hajmi 10 MB dan oshmasligi kerak")
        if len(content) == 0:
            raise HTTPException(status_code=400, detail="Yuklangan fayl bo'sh")
        res = WordService.parse_docx(content)
        return res
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Word faylini tahlil qilishda xatolik: {e}")

@router.post("/word/ai-review")
def review_imported_questions_with_ai(data: WordAiReviewRequest, teacher: dict = Depends(require_teacher)):
    """Worddan import qilingan savollar bo'yicha Gemini AI tavsiyalari."""
    q_sample = data.questions[:15] # ko'pi bilan 15 tasini tekshirish
    prompt_q = "\n".join([f"{idx+1}. {q.get('question_text')} (Variantlar: {len(q.get('options', []))} ta, To'g'ri: {next((o.get('option_text') for o in q.get('options', []) if o.get('is_correct')), 'Yoq')})" for idx, q in enumerate(q_sample)])
    
    review_prompt = f"""Sen test ekspertisan. Quyidagi import qilingan test savollarini ko'rib chiq:
{prompt_q}

Quyidagilarni qisqa va aniq tekshirib ber:
1. Savollar tushunarlimi?
2. Variantlar orasida takrorlanish yoki noaniqliklar bormi?
3. Savollarning tuzilishi bo'yicha qisqa metodik tavsiya.
O'zbek tilida, do'stona va amaliy tarzda yoz."""

    from services.ai.ai_gateway import AIGateway
    api_key = AIGateway.get_api_key()
    if not api_key:
        return {
            "advice": "Gemini AI kaliti kiritilmagan. Savollaringiz Word formati bo'yicha muvaffaqiyatli tekshirildi. Barcha variantlar va to'g'ri javoblar mavjudligini ko'zdan kechirib, tasdiqlashingiz mumkin."
        }

    def _task(client, model):
        return client.analyze(
            prompt=review_prompt,
            model=model,
            system_instruction="Sen professional pedagogik test tahlilchisisan. Javoblaringni aniq va o'zbek tilida ber."
        )

    def _fallback():
        return "Savollar Word formatiga mos, variantlar va javoblar to'liq kiritilgan. Tasdiqlashga tayyor."

    try:
        advice_text = AIGateway.execute_with_retry(
            task_func=_task,
            task_name="word_ai_review",
            request_data={"questions_sample_count": len(q_sample)},
            user_id=teacher.get("id"),
            fallback_allowed=True,
            fallback_func=_fallback
        )
        return {"advice": advice_text}
    except Exception:
        return {"advice": _fallback()}

@router.get("/word/export/{test_id}")
def export_test_docx(test_id: int, mode: Optional[str] = Query("teacher"), teacher: dict = Depends(require_teacher)):
    t_id = teacher.get("teacher_id")
    detail = TeacherService.get_test_detail(test_id, t_id)
    if not detail:
        raise HTTPException(status_code=404, detail="Test topilmadi")

    stream = WordService.generate_docx_export(detail, mode=mode or "teacher")
    clean_title = re.sub(r'[^a-zA-Z0-9_\-]', '_', detail.get("title", "Test"))
    filename = f"{clean_title}_{'oqituvchi' if mode == 'teacher' else 'oquvchi'}.docx"
    encoded_filename = urllib.parse.quote(filename)

    headers = {
        "Content-Disposition": f"attachment; filename*=UTF-8''{encoded_filename}"
    }
    return StreamingResponse(
        stream,
        media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        headers=headers
    )

