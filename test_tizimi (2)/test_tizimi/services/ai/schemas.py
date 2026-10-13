from typing import List, Optional, Dict, Any, Union
# pyrefly: ignore [missing-import]
from pydantic import BaseModel

class QuestionOption(BaseModel):
    option_text: str
    is_correct: int = 0

class GeneratedQuestion(BaseModel):
    question_text: str
    options: List[QuestionOption]
    difficulty: str = "medium"
    topic: str = "Umumiy"
    points: int = 1
    explanation: str = ""
    quality_score: Optional[float] = None
    status: str = "accepted"

class QualityScoreDetail(BaseModel):
    accuracy: float = 0.95
    relevance: float = 0.95
    uniqueness: float = 0.95
    difficulty: float = 0.90
    clarity: float = 0.95
    overall: float = 0.94

class GenerateTestRequest(BaseModel):
    subject_name: str = "IT"
    topic_name: str
    count: int = 10
    difficulty: str = "medium"
    grade_level: int = 10
    points: int = 1
    include_explanation: bool = True
    extra_prompt: Optional[str] = ""
    source_based: bool = False
    material_text: Optional[str] = None

class GenerateTestResponse(BaseModel):
    subject: str
    topic: str
    count: int
    questions: List[GeneratedQuestion]
    quality_score: float = 0.95
    status: str = "accepted"
    pipeline_stats: Optional[Dict[str, Any]] = None

class ReviewQuestionRequest(BaseModel):
    subject: str
    topic: str
    questions: List[GeneratedQuestion]

class ReviewQuestionResponse(BaseModel):
    accepted_questions: List[GeneratedQuestion]
    rejected_questions: List[GeneratedQuestion] = []
    rejection_reasons: List[str] = []
    overall_quality: float = 0.95

class FactInterpretationResponse(BaseModel):
    facts: Union[List[Any], Dict[str, Any]]
    analysis: List[str]
    recommendations: List[str]

class StudentAnalysisRequest(BaseModel):
    student_name: str
    group_name: str
    test_title: str
    score_percent: float
    total_questions: int
    correct_answers: int
    incorrect_answers: int
    tab_switch_count: int = 0
    time_spent_seconds: int = 0
    topics: List[Dict[str, Any]] = []
    questions: List[Dict[str, Any]] = []

class TeacherAnalysisRequest(BaseModel):
    group_name: str
    subject_name: str
    student_count: int
    avg_score: float
    topic_stats: List[Dict[str, Any]] = []

class AdminAnalysisRequest(BaseModel):
    total_students: int
    total_teachers: int
    total_subjects: int
    avg_score: float
    subject_analytics: List[Dict[str, Any]] = []
