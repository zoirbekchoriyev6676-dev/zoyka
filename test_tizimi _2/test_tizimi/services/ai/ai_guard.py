from typing import Optional

class AIGuard:
    """
    Hallucination Guard va Fan Konteksti nazorati.
    AI mavzudan chetga chiqmasligini va soxta faktlar to'qimasligini ta'minlaydi.
    """
    @staticmethod
    def build_system_instruction(
        subject: str,
        grade: int = 10,
        topic: str = "",
        level: str = "medium",
        source_based: bool = False,
        material_text: Optional[str] = None
    ) -> str:
        base = f"""Sen {subject} fani bo'yicha professional ta'lim ekspertisan.
Sinf darajasi: {grade}-sinf.
Mavzu: "{topic}".
Daraja: {level}.

Qat'iy qoidalar:
1. Mavzudan tashqari hech qanday savol yoki fakt qo'shma.
2. Har bir savol 4 ta variantga ega bo'lishi va faqat 1 ta to'g'ri javob bo'lishi SHART.
3. Chalg'ituvchi variantlar mantiqan ishonarli va pedagogik jihatdan to'g'ri bo'lsin.
4. Har bir savol uchun tushunarli va asosli izoh (explanation) ber."""

        if source_based and material_text:
            base += f"""\n\nDIQQAT: source_based = true rejimidasan.
Quyidagi berilgan manba materialidan tashqariga aslo chiqma va o'zingdan yangi faktlar to'qima!
--- MANBA MATERIALI BOSHLANISHI ---
{material_text[:4000]}
--- MANBA MATERIALI TUGASHI ---
Faqat va faqat ushbu materialdagi ma'lumotlarga tayanib savol yarat!"""

        return base
