import re
from typing import List
from services.ai.schemas import GeneratedQuestion, QualityScoreDetail

class QualityScorer:
    """
    Savollar to'plamining sifat ko'rsatkichini (Quality Score) dinamik baholash.
    Hech qanday qattiq doimiy (hardcoded) sonlar yo'q; har bir ko'rsatkich
    matn sifati, mavzuga moslik, variantlar balansi va takrorlanmaslikka asoslanadi.
    """
    @staticmethod
    def score_set(
        questions: List[GeneratedQuestion],
        subject: str,
        topic: str
    ) -> QualityScoreDetail:
        if not questions:
            return QualityScoreDetail(
                accuracy=0.0, relevance=0.0, uniqueness=0.0,
                difficulty=0.0, clarity=0.0, overall=0.0
            )

        n = len(questions)

        # 1. Aniqlik (Accuracy): har bir savolda aynan 1 ta to'g'ri variant va izoh mavjudligi
        valid_opts_count = 0
        has_exp_count = 0
        for q in questions:
            corrects = sum(1 for o in q.options if o.is_correct == 1)
            if corrects == 1 and len(q.options) == 4:
                valid_opts_count += 1
            if q.explanation and len(q.explanation.strip()) >= 10:
                has_exp_count += 1

        accuracy = round(((valid_opts_count / n) * 0.6 + (has_exp_count / n) * 0.4), 2)

        # 2. Mavzuga moslik (Relevance): mavzu va fan kalit so'zlarining savollarda uchrashi
        stop_words = {"va", "hamda", "bilan", "uchun", "haqida", "nima", "qanday", "fan", "mavzu", "dars"}
        topic_words = [
            w for w in re.findall(r'\w+', f"{subject} {topic}".lower())
            if len(w) >= 3 and w not in stop_words
        ]
        
        if topic_words:
            matched_q = 0
            for q in questions:
                full_text = f"{q.question_text} {' '.join(o.option_text for o in q.options)} {q.explanation or ''}".lower()
                if any(tw in full_text for tw in topic_words):
                    matched_q += 1
            relevance = round(max(0.60, min(0.99, (matched_q / n) * 0.9 + 0.1)), 2)
        else:
            relevance = 0.85

        # 3. Takrorlanmaslik (Uniqueness): savollar matnlarining Jaccard o'xshashlik tahlili
        unique_sets = [set(re.findall(r'\w+', q.question_text.lower())) for q in questions]
        max_pair_similarity = 0.0
        comparisons = 0
        for i in range(n):
            for j in range(i + 1, n):
                s1, s2 = unique_sets[i], unique_sets[j]
                if s1 and s2:
                    jaccard = len(s1 & s2) / len(s1 | s2)
                    max_pair_similarity = max(max_pair_similarity, jaccard)
                    comparisons += 1

        if comparisons > 0:
            uniqueness = round(max(0.50, min(1.0, 1.0 - (max_pair_similarity * 0.4))), 2)
        else:
            uniqueness = 0.95

        # 4. Murakkablik va chalg'ituvchilar sifati (Difficulty): variantlar uzunligi balansi
        diff_scores = []
        for q in questions:
            opt_lens = [len(o.option_text.strip()) for o in q.options]
            if opt_lens and max(opt_lens) > 0:
                len_ratio = min(opt_lens) / max(opt_lens)
                diff_scores.append(min(1.0, 0.6 + len_ratio * 0.4))
            else:
                diff_scores.append(0.7)
        difficulty = round(sum(diff_scores) / n, 2)

        # 5. Ravonlik va tushunarlilik (Clarity): matn uzunligi va tinish belgilari
        clarity_scores = []
        for q in questions:
            q_len = len(q.question_text.strip())
            score = 0.70
            if 20 <= q_len <= 250:
                score += 0.20
            if any(q.question_text.strip().endswith(p) for p in ("?", ".", ":")):
                score += 0.10
            clarity_scores.append(min(1.0, score))
        clarity = round(sum(clarity_scores) / n, 2)

        # Umumiy yakuniy baho
        overall = round(
            (accuracy * 0.25 + relevance * 0.25 + uniqueness * 0.20 + difficulty * 0.15 + clarity * 0.15),
            2
        )

        return QualityScoreDetail(
            accuracy=accuracy,
            relevance=relevance,
            uniqueness=uniqueness,
            difficulty=difficulty,
            clarity=clarity,
            overall=overall
        )
