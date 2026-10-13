import json
import logging
from typing import Dict, Any, List
from services.ai.ai_gateway import AIGateway

logger = logging.getLogger(__name__)

class AdminAnalyzer:
    """
    Muassasa miqyosidagi umumiy tahlilchi (Admin Analyzer).
    Backend bergan statistikaga xolisona institutsional xulosa chiqaradi.
    """
    @classmethod
    def analyze_overview(cls, school_stats: Dict[str, Any], user_id: int = None) -> Dict[str, Any]:
        total_students = school_stats.get("total_students", 0)
        total_teachers = school_stats.get("total_teachers", 0)
        total_subjects = school_stats.get("total_subjects", 0)
        avg_score = school_stats.get("avg_score", 0.0)
        subject_analytics = school_stats.get("subject_analytics", [])

        facts = {
            "total_students": total_students,
            "total_teachers": total_teachers,
            "total_subjects": total_subjects,
            "avg_score": avg_score,
            "subjects": [
                {
                    "subject_name": s.get("subject_name"),
                    "avg_score": s.get("avg_score"),
                    "attempts": s.get("attempts_count", 0)
                }
                for s in subject_analytics
            ]
        }

        subj_str = "\n".join([
            f"- {s.get('subject_name')}: {s.get('avg_score')}% ({s.get('attempts_count', 0)} ta topshirish)"
            for s in subject_analytics
        ]) or "Fanlar statistikasi yo'q"

        prompt = f"""Muassasa darajasidagi monitoring (Faqat xulosa va strategik tavsiya ber, yangi raqam to'qima):
Jami o'quvchilar: {total_students}
Jami o'qituvchilar: {total_teachers}
Jami fanlar: {total_subjects}
O'rtacha muassasa ko'rsatkichi: {avg_score}%

Fanlar bo'yicha ko'rsatkichlar:
{subj_str}

Vazifa: Muassasa rahbariyati uchun xulosa va tavsiyalar tayyorla.
Javobni FAQAT toza JSON formatida quyidagicha qaytar:
{{
  "analysis": [
    "Muassasa umumiy ko'rsatkichiga baho...",
    "Yetakchi va e'tibor talab qiluvchi fanlar..."
  ],
  "recommendations": [
    "Ma'muriy va strategik 1-tavsiya...",
    "2-tavsiya..."
  ]
}}"""

        def run_analysis(client, model_name):
            raw = client.analyze(
                prompt=prompt,
                model=model_name,
                system_instruction="Sen ta'lim monitoringi bo'yicha bosh tahlilchisan. Rahbariyat uchun aniq va strategik tavsiyalar ber."
            )
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text.rsplit("\n", 1)[0]
            parsed = json.loads(text)
            analysis_list = parsed.get("analysis", [])
            return {
                "facts": facts,
                "analysis": analysis_list,
                "summary": " ".join(analysis_list) if analysis_list else "",
                "recommendations": parsed.get("recommendations", [])
            }

        def fallback_action():
            fb_analysis = [
                f"Muassasa bo'yicha o'rtacha ko'rsatkich: {avg_score}%. Jami {total_students} o'quvchi va {total_teachers} o'qituvchi.",
                "AI institutsional xulosasi vaqtincha mavjud emas."
            ]
            return {
                "facts": facts,
                "analysis": fb_analysis,
                "summary": " ".join(fb_analysis),
                "recommendations": [
                    "Har bir fan va guruh kesimida muntazam monitoring olib borish tavsiya etiladi."
                ],
                "ai_note": "AI xulosasi vaqtincha mavjud emas"
            }

        return AIGateway.execute_with_retry(
            task_func=run_analysis,
            task_name="admin_overview_analysis",
            request_data={"avg_score": avg_score},
            user_id=user_id,
            max_retries=2,
            fallback_allowed=True,
            fallback_func=fallback_action
        )
