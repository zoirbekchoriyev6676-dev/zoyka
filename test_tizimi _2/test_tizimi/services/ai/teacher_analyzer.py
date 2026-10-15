import json
import logging
from typing import Dict, Any, List
from services.ai.ai_gateway import AIGateway
from services.ai.schemas import FactInterpretationResponse

logger = logging.getLogger(__name__)

class TeacherAnalyzer:
    """
    O'qituvchi va guruh monitoringi uchun tahlil moduli.
    Fact + Interpretation: Backend statistikasi + AI metodik tavsiyalari.
    """
    @classmethod
    def analyze_group(cls, stats: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        # 1. Backend faktlari
        group_name = stats.get("group_name", "Guruh")
        subject_name = stats.get("subject_name", "Fan")
        student_count = stats.get("student_count", 0)
        avg_score = stats.get("avg_score", 0.0)
        topic_stats = stats.get("topic_stats", [])

        facts = {
            "group_name": group_name,
            "subject_name": subject_name,
            "student_count": student_count,
            "avg_score": avg_score,
            "topics": [
                {
                    "topic_name": t.get("topic_name"),
                    "avg_percentage": t.get("avg_percentage"),
                    "correct": t.get("correct_q"),
                    "total": t.get("total_q")
                }
                for t in topic_stats
            ]
        }

        topics_str = "\n".join([
            f"- {t.get('topic_name')}: {t.get('avg_percentage')}%"
            for t in topic_stats
        ]) or "Mavzular statistikasi yo'q"

        prompt = f"""Guruh imtihon natijalari (Raqamlarni o'zgartirma, faqat pedagogik tahlil ber):
Guruh: {group_name}
Fan: {subject_name}
Ishtirokchilar soni: {student_count} nafar
O'rtacha ko'rsatkich: {avg_score}%

Mavzular o'zlashtirilishi:
{topics_str}

Vazifang: O'qituvchi uchun metodik tahlil tayyorla:
- eng qiyin mavzu qaysi va sababi
- eng yaxshi o'zlashtirilgan mavzu
- sinfning umumiy tayyorgarlik darajasi
- keyingi darslar uchun amaliy tavsiyalar

Javobni FAQAT toza JSON formatida quyidagicha qaytar:
{{
  "analysis": [
    "Eng qiyin mavzu tahlili...",
    "Yaxshi o'zlashtirilgan mavzu...",
    "Sinf darajasi bahosi..."
  ],
  "recommendations": [
    "Dars rejasiga o'zgartirish bo'yicha 1-tavsiya...",
    "2-tavsiya..."
  ]
}}"""

        def run_analysis(client, model_name):
            raw = client.analyze(
                prompt=prompt,
                model=model_name,
                system_instruction="Sen metodist va ta'lim tahlilchisisan. Qisqa, aniq va amaliy yoz."
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
            return {
                "facts": facts,
                "analysis": [
                    f"Guruh o'rtacha bali: {avg_score}%. Ishtirokchilar: {student_count} nafar.",
                    "AI izohi vaqtincha mavjud emas."
                ],
                "recommendations": [
                    "Past ko'rsatkich qayd etilgan mavzular bo'yicha qo'shimcha tushuntirish o'tkazish tavsiya etiladi."
                ],
                "ai_note": "AI tahlili vaqtincha mavjud emas"
            }

        return AIGateway.execute_with_retry(
            task_func=run_analysis,
            task_name="teacher_group_analysis",
            request_data={"group": group_name, "avg_score": avg_score},
            user_id=user_id,
            max_retries=2,
            fallback_allowed=True,
            fallback_func=fallback_action
        )
