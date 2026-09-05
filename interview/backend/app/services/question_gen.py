"""根据简历 + JD 生成结构化面试题库（7 维度覆盖）。"""
from __future__ import annotations

import json
import re
from typing import List

from ..schemas import JDParseOut, ResumeParseOut, InterviewQuestion, QuestionBankOut
from ..providers.llm import LLMProvider, ChatMessage

DIMENSIONS = ["简历匹配", "专业技能", "项目经验", "逻辑思维", "沟通表达", "职业规划", "综合素养"]

SYSTEM_PROMPT = """你是一位资深招聘面试官。请根据候选人简历与岗位 JD，生成一份结构化面试题。
请输出严格 JSON，不写任何其它文字。格式：
{
  "position": "岗位名称",
  "count": 7,
  "questions": [
    {"id": 1, "dimension": "简历匹配|专业技能|项目经验|逻辑思维|沟通表达|职业规划|综合素养",
     "question": "具体的中文面试题", "hint": "给候选人的简要作答提示/可写空串"}
  ]
}
要求：
1. count 默认 7 题，维度分布：简历匹配 1、专业技能 2、项目经验 1、逻辑思维 1、沟通表达 1、职业规划/综合素养 1。
2. 问题必须紧扣简历和 JD，避免空泛。
3. 题目与提示均为中文。
"""


async def generate_question_bank(resume: ResumeParseOut, jd: JDParseOut, *, llm: LLMProvider, count: int = 7) -> QuestionBankOut:
    prompt = f"""【候选人简历】
姓名：{resume.name or '（未知）'}
技能：{', '.join(resume.skills) or '（空）'}
项目：{'; '.join(resume.projects[:2]) or '（空）'}
原始文本摘要：
{resume.raw_text[:1200]}

【岗位 JD】
岗位：{jd.position or '（未知）'}
所需技能：{', '.join(jd.required_skills) or '（空）'}
考察知识点：{', '.join(jd.knowledge_points) or '（空）'}
原始文本摘要：
{jd.raw_text[:1200]}

请生成 {count} 道面试题，严格覆盖简历匹配、专业技能、项目经验、逻辑思维、沟通表达、职业规划/综合素养。
"""
    try:
        raw = await llm.chat(
            [ChatMessage(role="system", content=SYSTEM_PROMPT),
             ChatMessage(role="user", content=prompt)],
            temperature=0.6, response_json=True,
        )
        data = json.loads(_strip(raw))
        position = data.get("position") or jd.position or "候选人定制面试"
        qs_raw = data.get("questions") or []
    except Exception:
        position = jd.position or "候选人定制面试"
        qs_raw = _fallback_questions(resume, jd, count)

    qs: List[InterviewQuestion] = []
    for i, q in enumerate(qs_raw[:max(5, count)]):
        dim = str(q.get("dimension") or "专业技能").strip()
        if dim not in DIMENSIONS:
            if "项目" in dim:
                dim = "项目经验"
            elif "简历" in dim or "匹配" in dim:
                dim = "简历匹配"
            elif "逻辑" in dim or "思维" in dim:
                dim = "逻辑思维"
            elif "沟通" in dim or "表达" in dim:
                dim = "沟通表达"
            elif "职业" in dim or "规划" in dim:
                dim = "职业规划"
            elif "综合" in dim or "素养" in dim:
                dim = "综合素养"
            else:
                dim = "专业技能"
        qq = str(q.get("question") or "").strip()
        if qq:
            qs.append(InterviewQuestion(id=i + 1, dimension=dim, question=qq, hint=str(q.get("hint") or "").strip()))

    if len(qs) < 5:
        for q in _fallback_questions(resume, jd, count)[len(qs):]:
            qs.append(InterviewQuestion(id=len(qs) + 1, dimension=q["dimension"], question=q["question"], hint=q.get("hint", "")))
            if len(qs) >= count:
                break
    return QuestionBankOut(position=position, count=len(qs), questions=qs)


def _fallback_questions(resume: ResumeParseOut, jd: JDParseOut, n: int):
    skill = jd.required_skills[0] if jd.required_skills else (resume.skills[0] if resume.skills else "核心技术")
    proj = (resume.projects[0][:30] + "…") if resume.projects else "你简历中最近的一个项目"
    return [
        {"dimension": "简历匹配", "question": f"请先做 1-2 分钟自我介绍，结合简历中的项目与技能，说明你为什么适合【{jd.position or '该岗位'}】。", "hint": "STAR 法则；突出与 JD 匹配的亮点。"},
        {"dimension": "专业技能", "question": f"请深入讲讲你对 {skill} 的理解：常见使用场景、踩过的坑，以及你如何定位和解决相关问题？", "hint": "原理 + 工程实践 + 数据指标。"},
        {"dimension": "专业技能", "question": f"针对岗位核心要求，任选一个你熟悉的技术点（如：{', '.join(jd.knowledge_points[:3]) or '数据库索引/缓存策略'}），结合项目说明你的落地方式。", "hint": "具体场景 + 选型理由 + 效果量化。"},
        {"dimension": "项目经验", "question": f"请详细展开“{proj}”：你的角色、最大技术难点，如何解决、效果如何量化？", "hint": "背景→目标→行动→结果（带数据）。"},
        {"dimension": "逻辑思维", "question": "假设你负责的线上核心服务 10 分钟内 P99 延迟从 200ms 暴涨到 2s，CPU 飙升 90%，请描述完整排查与止损流程。", "hint": "先止损、再定位；监控、日志、链路、依赖到代码。"},
        {"dimension": "沟通表达", "question": "描述一次你需要跨部门/跨团队推动才能完成的事情：阻力、如何沟通协调、最终结果。", "hint": "突出你作为推动者的关键动作。"},
        {"dimension": "职业规划", "question": "未来 1-3 年，你在技术深度、业务理解、团队协作三方面的成长目标是什么？为什么选择本方向？", "hint": "真实具体，体现对岗位与自身优劣势的理解。"},
    ][:n]


def _strip(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()
