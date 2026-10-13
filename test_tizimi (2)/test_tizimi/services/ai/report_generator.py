from typing import Dict, Any

class ReportGenerator:
    """
    Tahlil natijalarini formatlangan matnga (HTML yoki Markdown) o'giruvchi modul.
    """
    @staticmethod
    def format_student_report(analysis_dict: Dict[str, Any]) -> str:
        facts = analysis_dict.get("facts", {})
        analysis_lines = analysis_dict.get("analysis", [])
        rec_lines = analysis_dict.get("recommendations", [])

        md = f"### 📊 Test Natijalari Bo'yicha Pedagogik Xulosa\n\n"
        md += f"- **Umumiy ball:** {facts.get('score_percent', 0)}%\n"
        md += f"- **To'g'ri javoblar:** {facts.get('correct_answers', 0)} / {facts.get('total_questions', 0)}\n\n"

        if analysis_lines:
            md += "#### 🎯 Tahliliy Fikrlar:\n"
            for line in analysis_lines:
                md += f"- {line}\n"
            md += "\n"

        if rec_lines:
            md += "#### 💡 Tavsiyalar:\n"
            for i, r in enumerate(rec_lines, 1):
                md += f"{i}. {r}\n"

        if facts.get("tab_switch_count", 0) > 0:
            md += f"\n*Eslatma: Test jarayonida {facts.get('tab_switch_count')} marta oynadan chiqish holati qayd etildi.*"

        return md

    @staticmethod
    def format_group_report(analysis_dict: Dict[str, Any]) -> str:
        facts = analysis_dict.get("facts", {})
        analysis_lines = analysis_dict.get("analysis", [])
        rec_lines = analysis_dict.get("recommendations", [])

        md = f"### 🏫 Guruh Ko'rsatkichlari Tahlili ({facts.get('group_name', '')} • {facts.get('subject_name', '')})\n\n"
        md += f"- **Ishtirokchilar:** {facts.get('student_count', 0)} nafar\n"
        md += f"- **O'rtacha ball:** {facts.get('avg_score', 0)}%\n\n"

        if analysis_lines:
            md += "#### 📌 Xulosa:\n"
            for line in analysis_lines:
                md += f"- {line}\n"
            md += "\n"

        if rec_lines:
            md += "#### 👩‍🏫 Metodik Tavsiyalar:\n"
            for i, r in enumerate(rec_lines, 1):
                md += f"{i}. {r}\n"

        return md

    @staticmethod
    def format_school_report(analysis_dict: Dict[str, Any]) -> str:
        facts = analysis_dict.get("facts", {})
        analysis_lines = analysis_dict.get("analysis", [])
        rec_lines = analysis_dict.get("recommendations", [])

        md = f"### 🏛️ Muassasa Bo'yicha Ta'lim Sifati Tahlili\n\n"
        md += f"- **O'rtacha ko'rsatkich:** {facts.get('avg_score', 0)}%\n"
        md += f"- **O'quvchilar soni:** {facts.get('total_students', 0)}\n\n"

        if analysis_lines:
            md += "#### 📊 Tahlil:\n"
            for line in analysis_lines:
                md += f"- {line}\n"
            md += "\n"

        if rec_lines:
            md += "#### 📋 Boshqaruv Tavsiyalari:\n"
            for i, r in enumerate(rec_lines, 1):
                md += f"{i}. {r}\n"

        return md
