"""多维度评分 + 复盘报告。LLM 结构化输出 + 启发式兜底，字段严格遵循 EvaluationOut 契约。"""
from __future__ import annotations

import json
import re

from ..schemas import DimensionScore, EvaluationOut
from ..session_store import InterviewSession, get_session
from ..providers.llm import LLMProvider, ChatMessage

DIMENSIONS = ["专业匹配度", "逻辑表达", "应答完整性", "项目深度", "综合素养"]
_WEIGHTS = {"专业匹配度": 0.28, "逻辑表达": 0.20, "应答完整性": 0.20, "项目深度": 0.20, "综合素养": 0.12}

SCORE_SYSTEM = """你是资深招聘评估官。请基于下面的「面试对话全文、候选人简历摘要、岗位 JD 摘要」，给出严格 JSON 的结构化评分：
{
  "total_score": 0-100整数,
  "level": "优秀|良好|合格|待改进",
  "dimensions": [
    {"dimension":"专业匹配度","score":0-100整数,"comment":"1-2句中文点评"},
    {"dimension":"逻辑表达","score":0-100整数,"comment":""},
    {"dimension":"应答完整性","score":0-100整数,"comment":""},
    {"dimension":"项目深度","score":0-100整数,"comment":""},
    {"dimension":"综合素养","score":0-100整数,"comment":""}
  ],
  "highlights": "候选人亮点，100-150字中文",
  "weaknesses": "候选人不足，100-150字中文",
  "suggestions": ["改进建议1","建议2","建议3","建议4"],
  "transcript_summary": "面试过程一句话总结，60-100字"
}
要求：level 阈值 >=90优秀；>=75良好；>=60合格；<60待改进。所有维度 score 为 0-100 整数；字段非空；仅中文、仅输出 JSON。"""


def _transcript_text(s: InterviewSession, max_chars: int = 5000) -> str:
    lines = []
    for h in s.history:
        who = "面试官" if h.get("role") == "interviewer" else "候选人"
        lines.append(f"{who}（第{h.get('round',0)}轮）：{h.get('content','')}")
    text = "\n".join(lines)
    return text[:max_chars] + "\n...(已截断)" if len(text) > max_chars else text


def _last_cand_text(s: InterviewSession) -> str:
    for h in reversed(s.history):
        if h.get("role") == "candidate":
            return h.get("content", "")
    return ""


def _level(score: int) -> str:
    if score >= 90:
        return "优秀"
    if score >= 75:
        return "良好"
    if score >= 60:
        return "合格"
    return "待改进"


def _heuristic_eval(s: InterviewSession) -> EvaluationOut:
    n_answers = sum(1 for h in s.history if h.get("role") == "candidate")
    total_chars = sum(len(h.get("content", "")) for h in s.history if h.get("role") == "candidate")
    avg_chars = int(total_chars / max(1, n_answers))
    last = _last_cand_text(s)

    def score_dim(weight: int) -> int:
        s0 = min(100, 50 + avg_chars // 10)
        digit_bonus = 5 if re.search(r"\d", last) else 0
        kw_bonus = 5 if any(k in last for k in ("方案", "优化", "项目", "通过", "提升", "降低")) else 0
        return max(40, min(95, s0 + digit_bonus + kw_bonus + weight))

    dims = [
        DimensionScore(dimension="专业匹配度", score=score_dim(6), comment="从回答内容看，技能栈与岗位有一定交集，但技术深度细节可进一步补充。"),
        DimensionScore(dimension="逻辑表达", score=score_dim(2), comment="整体表达有结构，能分点叙述；部分过渡句与因果关系可以更清晰。"),
        DimensionScore(dimension="应答完整性", score=score_dim(0), comment="各题均有作答，部分题目量化指标与对比方案描述不充分。"),
        DimensionScore(dimension="项目深度", score=score_dim(4), comment="项目背景与职责描述清晰，遇到的难点与选型权衡描述偏浅。"),
        DimensionScore(dimension="综合素养", score=score_dim(-2), comment="态度端正、配合度高，职业方向基本稳定，具备较好成长性。"),
    ]
    total = int(round(sum(d.score * _WEIGHTS[d.dimension] for d in dims)))
    return EvaluationOut(
        total_score=total,
        level=_level(total),
        dimensions=dims,
        highlights=f"本次面试共作答 {n_answers} 轮，平均每轮 {avg_chars} 字，表现出较积极的面试态度。结合岗位技能栈，整体匹配度处于 {'中上' if total >= 70 else '中等'} 水平。",
        weaknesses="回答在量化指标、方案选型理由、跨模块协作细节方面偏弱，部分答案停留在叙述层面，缺少深度剖析。",
        suggestions=[
            "准备 2-3 个能突出技术深度与个人贡献的 STAR 案例，每案配 2-3 个量化指标（时延、成本、QPS 等）",
            "梳理岗位核心技能，逐条补齐：原理→常见坑→排查手段→调优经验的四段式回答",
            "项目介绍中强化“对比过的备选方案、为何没选、决策依据”的描述",
            "补充 1-2 个跨团队推动 / 线上故障实战的软技能故事，体现协作与抗压能力",
        ],
        transcript_summary=f"模拟面试共进行 {n_answers} 轮，候选人围绕简历与岗位完成了多维度问答，整体风格 {'较为务实' if avg_chars >= 120 else '偏简略'}，建议结合改进建议继续准备。",
    )


async def evaluate_session(sid: str, *, llm: LLMProvider) -> EvaluationOut:
    s = get_session(sid)
    if not s:
        raise LookupError("会话不存在或已过期")
    if s.evaluation:
        return EvaluationOut(**s.evaluation)

    user_prompt = f"""【岗位摘要】
{str(s.jd)[:1200]}

【简历摘要】
{str(s.resume)[:1200]}

【面试对话全文】
{_transcript_text(s)}

请严格按 JSON 协议输出评分与建议。"""

    try:
        raw = await llm.chat(
            [ChatMessage(role="system", content=SCORE_SYSTEM), ChatMessage(role="user", content=user_prompt)],
            temperature=0.2, response_json=True,
        )
        data = json.loads(_strip(raw))
        dims_map = {d["dimension"]: (d.get("score", 60), d.get("comment", "")) for d in data.get("dimensions", [])}
        dims_out = []
        for dim in DIMENSIONS:
            sc, cm = dims_map.get(dim, (65, "未提供评分细节，见总评。"))
            sc = int(max(0, min(100, sc)))
            dims_out.append(DimensionScore(dimension=dim, score=sc, comment=(cm or "无额外点评")[:200]))
        total = int(round(sum(d.score * _WEIGHTS[d.dimension] for d in dims_out)))
        level = data.get("level") if data.get("level") in ("优秀", "良好", "合格", "待改进") else _level(total)
        result = EvaluationOut(
            total_score=total,
            level=level,
            dimensions=dims_out,
            highlights=str(data.get("highlights") or "无")[:300],
            weaknesses=str(data.get("weaknesses") or "无")[:300],
            suggestions=[str(x) for x in (data.get("suggestions") or [])[:6]] or ["建议继续刷题与模拟面试复盘。"],
            transcript_summary=str(data.get("transcript_summary") or "已完成模拟面试。")[:200],
        )
    except Exception:
        result = _heuristic_eval(s)

    s.evaluation = result.model_dump()
    s.finished = True
    s.touch()
    return result


def _strip(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()
