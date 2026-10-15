"""
gemini_service.py — Yangi services/ai/ arxitekturasi ustidan yupqa adapter.
Mavjud interfeys va metod nomlari to'liq saqlanadi, barcha so'rovlar yangi
AI Gateway va AI Orchestrator orqali o'tadi.
"""

import logging
from typing import Optional, List, Dict, Any

from services.ai.ai_gateway import AIGateway
from services.ai.orchestrator import AIOrchestrator
from services.ai.report_generator import ReportGenerator
from services.ai.schemas import GenerateTestRequest

logger = logging.getLogger(__name__)

class GeminiService:
    @staticmethod
    def get_api_key() -> str:
        return AIGateway.get_api_key()

    @staticmethod
    def set_api_key(key: str):
        AIGateway.set_api_key(key)

    @staticmethod
    def analyze_student_result(result_detail: dict) -> str:
        """
        O'quvchi natijasini tahlil qilish (Fact + Interpretation).
        Backend faktlari asosida pedagogik xulosa qaytaradi.
        """
        analysis_dict = AIOrchestrator.analyze_student(result_detail)
        return ReportGenerator.format_student_report(analysis_dict)

    @staticmethod
    def analyze_student_structured(result_detail: dict) -> dict:
        """Strukturalashgan Fact + Interpretation tahlili."""
        return AIOrchestrator.analyze_student(result_detail)

    @staticmethod
    def analyze_group_results(group_stats: dict) -> str:
        """Guruh natijalari bo'yicha tahliliy hisobot."""
        analysis_dict = AIOrchestrator.analyze_group(group_stats)
        return ReportGenerator.format_group_report(analysis_dict)

    @staticmethod
    def analyze_school_overview(school_stats: dict) -> str:
        """Maktab / Institut darajasidagi umumiy tahlil."""
        analysis_dict = AIOrchestrator.analyze_school(school_stats)
        return ReportGenerator.format_school_report(analysis_dict)

    @staticmethod
    def generate_test_questions(
        subject_name: str,
        topic_name: str,
        count: int = 10,
        difficulty: str = "medium",
        extra_prompt: str = "",
        grade_level: int = 10,
        points: int = 1,
        include_explanation: bool = True,
        source_based: bool = False,
        material_text: Optional[str] = None
    ) -> list:
        """
        Yangi ko'p bosqichli pipeline (Generator -> Validator -> Duplicate -> Reviewer -> Quality Scorer).
        Natija o'qituvchiga preview uchun ro'yxat ko'rinishida qaytariladi.
        """
        req = GenerateTestRequest(
            subject_name=subject_name or "IT",
            topic_name=topic_name,
            count=count,
            difficulty=difficulty,
            grade_level=grade_level,
            points=points,
            include_explanation=include_explanation,
            extra_prompt=extra_prompt,
            source_based=source_based,
            material_text=material_text
        )

        pipeline_resp = AIOrchestrator.generate_test_pipeline(req)

        # Eski formatga to'liq mos konvertatsiya
        result = []
        for q in pipeline_resp.questions:
            result.append({
                "question_text": q.question_text,
                "difficulty": q.difficulty,
                "points": q.points,
                "explanation": q.explanation,
                "quality_score": q.quality_score,
                "options": [
                    {"option_text": opt.option_text, "is_correct": opt.is_correct}
                    for opt in q.options
                ]
            })

        return result
