import json
import logging
from typing import List, Dict, Any, Optional
from services.ai.ai_gateway import AIGateway
from services.ai.ai_guard import AIGuard
from services.ai.schemas import GeneratedQuestion, QuestionOption

logger = logging.getLogger(__name__)

class QuestionGenerator:
    """
    Savol generatsiyasi moduli (1-bosqich).
    Strukturalashgan JSON va professional prompt bilan savollar yaratadi.
    """
    @staticmethod
    def generate_raw_questions(
        subject: str,
        topic: str,
        count: int = 10,
        difficulty: str = "medium",
        grade: int = 10,
        extra_prompt: str = "",
        source_based: bool = False,
        material_text: Optional[str] = None,
        user_id: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        count = max(1, min(30, count))
        system_instruction = AIGuard.build_system_instruction(
            subject=subject,
            grade=grade,
            topic=topic,
            level=difficulty,
            source_based=source_based,
            material_text=material_text
        )

        user_prompt = f"""Quyidagi talablar asosida aniq {count} ta test savolini toza JSON formatida massiv ko'rinishida yarat:
- Fan: {subject}
- Mavzu: {topic}
- Savollar soni: {count} ta
- Qiyinlik darajasi: {difficulty}
- Sinf: {grade}-sinf
{f'- Qo‘shimcha talab: {extra_prompt}' if extra_prompt else ''}

Har bir savolda:
1. "question_text": Savol matni (aniq, tushunarli, takrorlanmas).
2. "options": Aynan 4 ta variant. Har bir variant ob'ekt bo'lib: {{"option_text": "...", "is_correct": 1 yoki 0}}. Ulardan faqat bittasida is_correct=1 bo'lsin, qolgan uchtasida is_correct=0.
3. "difficulty": "{difficulty}".
4. "points": 1.
5. "explanation": To'g'ri javobning qisqa va aniq pedagogik izohi.

Javobni FAQAT JSON massiv formatida qaytar: [ {{ ... }} ]"""

        def run_generation(client, model_name):
            raw_text = client.generate(
                prompt=user_prompt,
                model=model_name,
                system_instruction=system_instruction,
                response_mime_type="application/json",
                temperature=0.7
            )
            text = raw_text.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text.rsplit("\n", 1)[0]
            parsed = json.loads(text)
            if not isinstance(parsed, list):
                if isinstance(parsed, dict) and "questions" in parsed:
                    parsed = parsed["questions"]
                else:
                    raise ValueError("JSON natijasi savollar ro'yxati (list) bo'lishi shart")
            return parsed

        return AIGateway.execute_with_retry(
            task_func=run_generation,
            task_name="generate_questions",
            request_data={
                "subject": subject,
                "topic": topic,
                "count": count,
                "difficulty": difficulty
            },
            user_id=user_id,
            max_retries=3,
            fallback_allowed=False  # Hech qanday soxta savol yo'q!
        )
