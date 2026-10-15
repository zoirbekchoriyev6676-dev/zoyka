import logging
from typing import List, Dict, Any, Optional
from services.ai.schemas import (
    GenerateTestRequest, GenerateTestResponse,
    GeneratedQuestion, QualityScoreDetail
)
from services.ai.question_generator import QuestionGenerator
from services.ai.question_validator import QuestionValidator
from services.ai.question_reviewer import QuestionReviewer
from services.ai.quality_scorer import QualityScorer
from services.ai.student_analyzer import StudentAnalyzer
from services.ai.teacher_analyzer import TeacherAnalyzer
from services.ai.admin_analyzer import AdminAnalyzer

logger = logging.getLogger(__name__)

class AIOrchestrator:
    """
    AI qatlamining boshqaruvchisi (AI Orchestrator).
    Vazifani to'g'ri modulga yo'naltiradi:
    Generator -> Validator -> Duplicate Filter -> Reviewer -> Quality Scorer -> Preview.
    """
    @classmethod
    def generate_test_pipeline(
        cls,
        req: GenerateTestRequest,
        user_id: Optional[int] = None
    ) -> GenerateTestResponse:
        target_count = req.count
        accumulated_questions: List[GeneratedQuestion] = []
        max_attempts = 3
        attempt = 0
        total_requested = 0
        total_rejected = 0

        while len(accumulated_questions) < target_count and attempt < max_attempts:
            attempt += 1
            needed = target_count - len(accumulated_questions)
            total_requested += needed

            # 1. Generator
            raw_batch = QuestionGenerator.generate_raw_questions(
                subject=req.subject_name,
                topic=req.topic_name,
                count=needed,
                difficulty=req.difficulty,
                grade=req.grade_level,
                extra_prompt=req.extra_prompt or "",
                source_based=req.source_based,
                material_text=req.material_text,
                user_id=user_id
            )

            # 2. Python Validation & Duplicate Filter (barcha oldingi batchlar bilan birga)
            existing_texts = [q.question_text for q in accumulated_questions]
            valid_questions, rejected_batch, val_reasons = QuestionValidator.validate_and_filter(
                raw_questions=raw_batch,
                topic_name=req.topic_name,
                existing_questions=existing_texts
            )
            total_rejected += len(rejected_batch)

            if not valid_questions:
                logger.warning(f"Generatsiya batchida barcha savollar tekshiruvdan o'tmadi: {val_reasons}")
                continue

            # 3. Independent AI Reviewer
            reviewed_accepted, reviewed_rejected, rev_reasons = QuestionReviewer.review_questions(
                questions=valid_questions,
                subject=req.subject_name,
                topic=req.topic_name,
                user_id=user_id
            )
            total_rejected += len(reviewed_rejected)

            # Qo'shish
            accumulated_questions.extend(reviewed_accepted)

        if not accumulated_questions:
            raise RuntimeError("Savollar generatsiyasi muvaffaqiyatsiz bo'ldi. Iltimos, qayta urinib ko'ring.")

        final_questions = accumulated_questions[:target_count]

        # 4. Quality Scorer
        score_detail: QualityScoreDetail = QualityScorer.score_set(
            questions=final_questions,
            subject=req.subject_name,
            topic=req.topic_name
        )

        for q in final_questions:
            q.quality_score = score_detail.overall

        return GenerateTestResponse(
            subject=req.subject_name,
            topic=req.topic_name,
            count=len(final_questions),
            questions=final_questions,
            quality_score=score_detail.overall,
            status="accepted" if score_detail.overall >= 0.90 else "review_needed",
            pipeline_stats={
                "requested": total_requested,
                "accepted": len(final_questions),
                "rejected": total_rejected,
                "attempts": attempt,
                "score_details": score_detail.model_dump()
            }
        )

    @classmethod
    def analyze_student(cls, result_data: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        return StudentAnalyzer.analyze(result_data, user_id=user_id)

    @classmethod
    def analyze_group(cls, group_stats: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        return TeacherAnalyzer.analyze_group(group_stats, user_id=user_id)

    @classmethod
    def analyze_school(cls, school_stats: Dict[str, Any], user_id: Optional[int] = None) -> Dict[str, Any]:
        return AdminAnalyzer.analyze_overview(school_stats, user_id=user_id)
