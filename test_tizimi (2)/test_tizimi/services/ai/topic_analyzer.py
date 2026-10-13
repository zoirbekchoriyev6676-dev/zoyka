from typing import List, Dict, Any

class TopicAnalyzer:
    """
    Mavzular bo'yicha kuchli va zaif nuqtalarni aniq hisoblash.
    """
    @staticmethod
    def identify_strengths_and_weaknesses(topic_stats: List[Dict[str, Any]]) -> Dict[str, Any]:
        strong = []
        weak = []
        moderate = []

        for t in topic_stats:
            pct = t.get("percentage", t.get("avg_percentage", 0))
            name = t.get("topic_name", "Mavzu")
            if pct >= 75:
                strong.append({"name": name, "percentage": pct})
            elif pct < 60:
                weak.append({"name": name, "percentage": pct})
            else:
                moderate.append({"name": name, "percentage": pct})

        return {
            "strong_topics": strong,
            "weak_topics": weak,
            "moderate_topics": moderate
        }
