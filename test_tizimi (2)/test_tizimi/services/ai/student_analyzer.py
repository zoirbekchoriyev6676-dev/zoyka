import json
import logging
from typing import Dict, Any, List
from services.ai.ai_gateway import AIGateway
from services.ai.cache import AICache
from services.ai.schemas import FactInterpretationResponse

logger = logging.getLogger(__name__)

class StudentAnalyzer:
    """
    O'quvchi natijasini tahlil qiluvchi modul.
    Faktlarni backend beradi, AI faqat pedagogik izoh va tavsiya yozadi.
    Fact + Interpretation ajratilgan: { facts, analysis, recommendations }
    """
    @classmethod
    def analyze(cls, result_data: Dict[str, Any], user_id: int = None, force_refresh: bool = False) -> Dict[str, Any]:
        student_id = result_data.get("student_id", 0)
        session_id = result_data.get("session_id", result_data.get("id", 0))
        cache_key = f"analysis_student_{student_id}_session_{session_id}"

        if not force_refresh:
            cached = AICache.get(cache_key)
            if cached:
                try:
                    return json.loads(cached)
                except Exception:
                    pass

        # 1. Backend faktlari (AI bu raqamlarga tegmaydi!)
        total_q = result_data.get("total_questions", 0)
        corr_q = result_data.get("correct_answers", 0)
        incorr_q = result_data.get("incorrect_answers", 0)
        score_pct = result_data.get("score_percent", 0.0)
        topics = result_data.get("topics", [])
        tab_switches = result_data.get("tab_switch_count", 0)

        facts = {
            "total_questions": total_q,
            "correct_answers": corr_q,
            "incorrect_answers": incorr_q,
            "score_percent": score_pct,
            "tab_switch_count": tab_switches,
            "topic_percentages": {
                t.get("topic_name", "Mavzu"): f"{t.get('percentage', 0)}% ({t.get('correct_answers', 0)}/{t.get('total_questions', 0)})"
                for t in topics
            }
        }

        # Prompt
        topics_str = "\n".join([
            f"- {t.get('topic_name')}: {t.get('percentage')}% ({t.get('correct_answers')}/{t.get('total_questions')})"
            for t in topics
        ]) or "Mavzu statistikasi mavjud emas"

        prompt = f"""O'quvchi natijasi (Faqat tahlil va pedagogik tavsiya ber, raqamlarni o'zgartirma):
O'quvchi: {result_data.get('student_name', 'O`quvchi')}
Test: {result_data.get('test_title', 'Imtihon')}
Fan: {result_data.get('subject_name', 'Fan')}
Backend hisoblagan natija: {score_pct}% ({corr_q}/{total_q} to'g'ri)
Chiqib ketishlar soni: {tab_switches}

Mavzular bo'yicha ko'rsatkichlar:
{topics_str}

Vazifa: Natijani pedagogik tahlil qil va amaliy tavsiyalar ber.
Javobni FAQAT toza JSON formatida quyidagicha qaytar:
{{
  "analysis": [
    "Kuchli tomonlar haqida fikr...",
    "Rivojlantirish kerak bo'lgan tomonlar haqida fikr...",
    "Umumiy pedagogik xulosa..."
  ],
  "recommendations": [
    "1-amaliy tavsiya...",
    "2-amaliy tavsiya..."
  ]
}}"""

        def run_analysis(client, model_name):
            raw = client.analyze(
                prompt=prompt,
                model=model_name,
                system_instruction="Sen professional pedagogik tahlilchisan. Faqat pedagogik tahlil va tavsiya ber, raqam to'qima."
            )
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text.rsplit("\n", 1)[0]
            parsed = json.loads(text)
            return {
                "facts": facts,
                "analysis": parsed.get("analysis", []),
                "recommendations": parsed.get("recommendations", [])
            }

        def fallback_action():
            # Section 7.6 Fallback siyosati: Faqat backend faktlari ko'rsatiladi, AI izohi "izoh vaqtincha mavjud emas"
            strong = [t.get("topic_name") for t in topics if t.get("percentage", 0) >= 70]
            weak = [t.get("topic_name") for t in topics if t.get("percentage", 0) < 60]
            return {
                "facts": facts,
                "analysis": [
                    f"Umumiy o'zlashtirish: {score_pct}%.",
                    f"Kuchli mavzular: {', '.join(strong) if strong else 'Aniqlanmadi'}.",
                    f"Takrorlash talab etiladigan mavzular: {', '.join(weak) if weak else 'Yo`q'}."
                ],
                "recommendations": [
                    "Qo'shimcha darslik va amaliy mashqlar ustida ishlash tavsiya etiladi."
                ],
                "ai_note": "AI to'liq izohi vaqtincha mavjud emas (Backend faktlari ko'rsatildi)"
            }

        response_dict = AIGateway.execute_with_retry(
            task_func=run_analysis,
            task_name="student_analysis",
            request_data={"student_id": student_id, "score": score_pct},
            user_id=user_id,
            max_retries=2,
            fallback_allowed=True,
            fallback_func=fallback_action
        )

        AICache.set(cache_key, json.dumps(response_dict, ensure_ascii=False))
        return response_dict
