"""Pydantic 数据契约（前后端 + 存储三方唯一真源）。"""
from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field

# 7 大面试维度
Dimension = Literal["简历匹配", "专业技能", "项目经验", "逻辑思维", "沟通表达", "职业规划", "综合素养"]
Level = Literal["优秀", "良好", "合格", "待改进"]


# ---------------- 简历 ----------------
class ResumeParseOut(BaseModel):
    raw_text: str = ""
    name: str = ""
    education: List[str] = Field(default_factory=list)
    skills: List[str] = Field(default_factory=list)
    experiences: List[str] = Field(default_factory=list)
    projects: List[str] = Field(default_factory=list)


# ---------------- JD ----------------
class JDParseOut(BaseModel):
    raw_text: str = ""
    position: str = ""
    required_skills: List[str] = Field(default_factory=list)
    responsibilities: List[str] = Field(default_factory=list)
    knowledge_points: List[str] = Field(default_factory=list)
    soft_skills: List[str] = Field(default_factory=list)


# ---------------- 题库 ----------------
class InterviewQuestion(BaseModel):
    id: int
    dimension: Dimension
    question: str
    hint: str = ""


class QuestionBankOut(BaseModel):
    position: str = ""
    count: int = 0
    questions: List[InterviewQuestion] = Field(default_factory=list)


# ---------------- 会话 ----------------
class SessionCreateReq(BaseModel):
    resume: Optional[ResumeParseOut] = None
    jd: Optional[JDParseOut] = None
    questions: Optional[List[InterviewQuestion]] = None


class SessionCreateOut(BaseModel):
    session_id: str
    position: str = ""
    welcome: str = ""
    total_rounds: int = 0


class MessageIn(BaseModel):
    answer: str = ""


class MessageOut(BaseModel):
    role: Literal["interviewer", "candidate", "system"]
    content: str
    round: Optional[int] = None
    is_followup: bool = False
    finished: bool = False


class ActionOut(BaseModel):
    action: Literal["ask", "followup", "finish"]
    next_question: Optional[str] = None
    reason: str = ""
    finished: bool = False


# ---------------- 评分 ----------------
class DimensionScore(BaseModel):
    dimension: str
    score: int = 0
    comment: str = ""


class EvaluationOut(BaseModel):
    total_score: int = 0
    level: Level = "待改进"
    dimensions: List[DimensionScore] = Field(default_factory=list)
    highlights: str = ""
    weaknesses: str = ""
    suggestions: List[str] = Field(default_factory=list)
    transcript_summary: str = ""
