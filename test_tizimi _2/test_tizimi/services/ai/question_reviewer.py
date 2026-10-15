import json
import logging
from typing import List, Dict, Any, Tuple
from services.ai.ai_gateway import AIGateway
from services.ai.schemas import GeneratedQuestion

logger = logging.getLogger(__name__)

class QuestionReviewer:
    """
    Alohida AI sessiyasidagi nazoratchi (Reviewer).
    Generatorga ko'r-ko'rona ishonmaydi, savollarning to'g'riligini va sifatini baholaydi.
    """
    @staticmethod
    def review_questions(
        questions: List[GeneratedQuestion],
        subject: str,
        topic: str,
        user_id: int = None
    ) -> Tuple[List[GeneratedQuestion], List[GeneratedQuestion], List[str]]:
        if not questions:
            return [], [], []

        prep_data = []
        for i, q in enumerate(questions):
            prep_data.append({
                "index": i,
                "question": q.question_text,
                "options": [f"{o.option_text} {'(TO`G`RI)' if o.is_correct else ''}" for o in q.options],
                "explanation": q.explanation
            })

        review_prompt = f"""Sen qat'iy va mustaqil ta'lim ekspertisan.
Mavzu: "{subject} - {topic}".
Senga boshqa tizim tomonidan generatsiya qilingan quyidagi test savollari berilmoqda:
{json.dumps(prep_data, ensure_ascii=False, indent=2)}

Vazifang: Har bir savolni tekshir:
1. Savol rostdan ham ushbu mavzuga mosmi?
2. To'g'ri deb belgilangan javob haqiqatan ham yagona to'g'ri javobmi?
3. Noto'g'ri variantlar mantiqan ishonarlimi (juda bachkana yoki ochiq xato emasmi)?
4. Savollar orasida bir-birini takrorlovchi yoki sinonim savollar bormi?

Javobni FAQAT JSON formatida quyidagicha qaytar:
{{
  "approved_indices": [0, 1, 2, ...],
  "rejected_indices": [ ... ],
  "reasons": {{
    "0": "Sabab (agar rad etilgan bo'lsa)",
    ...
  }}
}}"""

        def run_review(client, model_name):
            raw = client.review(
                prompt=review_prompt,
                model=model_name,
                system_instruction="Sen mustaqil va qat'iy reviewer ekspertsan. Xato va sifatsiz savollarni ayovsiz rad et.",
            )
            text = raw.strip()
            if text.startswith("```"):
                text = text.split("\n", 1)[1]
                if text.endswith("```"):
                    text = text.rsplit("\n", 1)[0]
            return json.loads(text)

        def strict_heuristic_fallback():
            """AI reviewer xatoga uchrasa, ko'r-ko'rona tasdiqlash o'rniga qat'iy tekshiruv qo'llash."""
            approved = []
            rejected = []
            reasons = {}
            for i, q in enumerate(questions):
                q_text = q.question_text.strip()
                options = q.options
                exp = (q.explanation or "").strip()

                if len(q_text) < 15:
                    rejected.append(i)
                    reasons[str(i)] = "Savol matni juda qisqa yoki mazmunsiz"
                    continue
                if len(options) != 4:
                    rejected.append(i)
                    reasons[str(i)] = "Variantlar soni to'liq 4 ta emas"
                    continue
                if not any(o.is_correct == 1 for o in options):
                    rejected.append(i)
                    reasons[str(i)] = "To'g'ri javob belgilanmagan"
                    continue
                if not exp:
                    rejected.append(i)
                    reasons[str(i)] = "Savolga tushuntirish (izoh) mavjud emas"
                    continue
                approved.append(i)

            return {"approved_indices": approved, "rejected_indices": rejected, "reasons": reasons}

        try:
            review_result = AIGateway.execute_with_retry(
                task_func=run_review,
                task_name="review_questions",
                request_data={"count": len(questions), "topic": topic},
                user_id=user_id,
                max_retries=2,
                fallback_allowed=True,
                fallback_func=strict_heuristic_fallback
            )

            approved_idx = set(review_result.get("approved_indices", []))
            reasons_dict = review_result.get("reasons", {})

            accepted: List[GeneratedQuestion] = []
            rejected: List[GeneratedQuestion] = []
            reasons_list: List[str] = []

            for i, q in enumerate(questions):
                if i in approved_idx:
                    accepted.append(q)
                else:
                    rejected.append(q)
                    r_text = reasons_dict.get(str(i), reasons_dict.get(i, "Reviewer tomonidan rad etildi"))
                    reasons_list.append(f"{i+1}-savol: {r_text}")

            return accepted, rejected, reasons_list

        except Exception as e:
            logger.warning(f"Reviewer xatosi: {e}. Qat'iy evristik tekshiruv qo'llanmoqda.")
            fallback_res = strict_heuristic_fallback()
            appr = [questions[i] for i in fallback_res["approved_indices"]]
            rej = [questions[i] for i in fallback_res["rejected_indices"]]
            r_list = [f"{i+1}-savol: {fallback_res['reasons'].get(str(i), 'Sifat talabiga javob bermadi')}" for i in fallback_res["rejected_indices"]]
            return appr, rej, r_list
