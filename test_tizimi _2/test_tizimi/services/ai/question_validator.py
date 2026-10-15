import re
import logging
from typing import List, Dict, Any, Tuple
from services.ai.schemas import GeneratedQuestion, QuestionOption

logger = logging.getLogger(__name__)

class QuestionValidator:
    """
    Savollarni sintaktik va semantik tekshirish hamda takrorlanish (duplicate) filtratsiyasi.
    """
    @staticmethod
    def _normalize_text(text: str) -> str:
        """Matnni solishtirish uchun tozalash va normalizatsiya qilish."""
        clean = re.sub(r'[^\w\s]', '', text.lower())
        words = clean.split()
        # O'zbek tili uchun eng ko'p uchraydigan to'xtash so'zlarini qisqartirish
        stopwords = {"nima", "qanday", "qaysi", "vazifasi", "haqida", "uchun", "bo'lgan", "qiladi", "dasturlash", "tilida"}
        meaningful = [w for w in words if w not in stopwords]
        return " ".join(sorted(meaningful)) if meaningful else " ".join(words)

    @staticmethod
    def _is_similar(text1: str, text2: str, threshold: float = 0.65) -> bool:
        """Ikki savol sinonim yoki juda o'xshash ekanligini aniqlash (Jaccard ko'rsatkichi)."""
        w1 = set(QuestionValidator._normalize_text(text1).split())
        w2 = set(QuestionValidator._normalize_text(text2).split())
        if not w1 or not w2:
            return text1.strip().lower() == text2.strip().lower()
        intersection = len(w1.intersection(w2))
        union = len(w1.union(w2))
        similarity = intersection / union if union > 0 else 0.0
        return similarity >= threshold

    @classmethod
    def validate_and_filter(
        cls,
        raw_questions: List[Dict[str, Any]],
        topic_name: str,
        existing_questions: List[str] = None
    ) -> Tuple[List[GeneratedQuestion], List[Dict[str, Any]], List[str]]:
        """
        Savollarni tekshirish va filtrdan o'tkazish.
        Qaytaradi: (qabul_qilingan_savollar, rad_etilgan_savollar, sabablar)
        """
        accepted: List[GeneratedQuestion] = []
        rejected: List[Dict[str, Any]] = []
        reasons: List[str] = []

        seen_texts: List[str] = list(existing_questions or [])

        for idx, q in enumerate(raw_questions):
            q_text = str(q.get("question_text", "")).strip()
            options = q.get("options", [])
            diff = q.get("difficulty", "medium")
            exp = q.get("explanation", "")
            pts = q.get("points", 1)

            # 1. Savol matni tekshiruvi
            if len(q_text) < 5:
                rejected.append(q)
                reasons.append(f"{idx+1}-savol: Matn juda qisqa yoki bo'sh")
                continue

            # 2. Aynan 4 ta variant tekshiruvi
            if not isinstance(options, list) or len(options) != 4:
                rejected.append(q)
                reasons.append(f"{idx+1}-savol: Variantlar soni aynan 4 ta emas ({len(options) if isinstance(options, list) else 0} ta)")
                continue

            # 3. Aynan 1 ta to'g'ri javob tekshiruvi
            correct_count = 0
            opt_texts = set()
            parsed_options: List[QuestionOption] = []

            for opt in options:
                if isinstance(opt, dict):
                    txt = str(opt.get("option_text", "")).strip()
                    is_c = 1 if opt.get("is_correct") in (1, True, "1", "true") else 0
                else:
                    txt = str(opt).strip()
                    is_c = 0
                
                opt_texts.add(txt.lower())
                if is_c == 1:
                    correct_count += 1
                parsed_options.append(QuestionOption(option_text=txt, is_correct=is_c))

            if correct_count != 1:
                rejected.append(q)
                reasons.append(f"{idx+1}-savol: Aynan 1 ta to'g'ri javob bo'lishi shart (topildi: {correct_count})")
                continue

            if len(opt_texts) != 4:
                rejected.append(q)
                reasons.append(f"{idx+1}-savol: Variantlar bir-birini takrorlamasligi kerak")
                continue

            # 4. Duplicate (takrorlanish va sinonim) filtri
            is_duplicate = False
            for prev_text in seen_texts:
                if cls._is_similar(q_text, prev_text):
                    is_duplicate = True
                    break

            if is_duplicate:
                rejected.append(q)
                reasons.append(f"{idx+1}-savol: Avvalgi savolning sinonimi yoki takrori ('{q_text}')")
                continue

            # Qabul qilindi
            seen_texts.append(q_text)
            accepted.append(GeneratedQuestion(
                question_text=q_text,
                options=parsed_options,
                difficulty=diff,
                topic=topic_name,
                points=pts,
                explanation=exp,
                quality_score=None,
                status="accepted"
            ))

        return accepted, rejected, reasons
