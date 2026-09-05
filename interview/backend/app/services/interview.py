"""
面试会话核心：状态机 + 逐轮提问 + 追问生成 + 结束判断 + SSE 流。
状态机指标全部后端显式维护（round/followup_count/current_idx/finished），不依赖 prompt。
"""
from __future__ import annotations

import json
import re
import time
from typing import AsyncIterator, List

from ..schemas import ActionOut, InterviewQuestion, JDParseOut, MessageOut, ResumeParseOut
from ..session_store import InterviewSession, get_session, new_session
from ..providers.llm import LLMProvider, ChatMessage

WELCOME = "你好，我是今天的 AI 面试官 🤖。接下来我会根据你的简历和岗位要求，围绕 简历匹配 / 专业技能 / 项目经验 / 逻辑思维 / 沟通表达 / 职业规划 等维度，向你提问 5-7 个主问题，并会适时追问。请尽量具体、用真实案例和量化数据作答。准备好了我们就开始～"
CLOSING = "好的，今天的面试就到这里，感谢你的时间 🙏。我会基于整个对话从多个维度给出评分和改进建议，请点击下方【生成面试报告】按钮查看结果。"

MAX_MAIN_ROUNDS = 7
MAX_FOLLOWUP_PER_QUESTION = 1   # 每题最多追 1 次，避免卡节奏
MIN_ANSWER_CHARS = 25
MIN_KEYWORD_HITS_TO_SKIP_FOLLOWUP = 2


def create_session(*, resume: ResumeParseOut, jd: JDParseOut, questions: List[InterviewQuestion]) -> InterviewSession:
    sess = new_session(resume=resume.model_dump(), jd=jd.model_dump(), questions=questions)
    sess.history.append({"role": "interviewer", "content": WELCOME, "ts": time.time(), "round": 0, "is_followup": False})
    return sess


def build_initial_state(session: InterviewSession) -> dict:
    first_q = session.current_q
    return {
        "session_id": session.session_id,
        "position": (session.jd or {}).get("position", ""),
        "welcome": WELCOME,
        "total_rounds": session.total_rounds(),
        "first_question": {"id": first_q.id, "dimension": first_q.dimension, "question": first_q.question, "hint": first_q.hint} if first_q else None,
    }


def decide_next(session: InterviewSession) -> ActionOut:
    main = len(session.questions)
    if session.finished:
        return ActionOut(action="finish", finished=True, reason="会话已结束")

    total_rounds_with_followups = int(main * 1.6 + 2)
    if session.round >= total_rounds_with_followups or session.current_idx >= main:
        return ActionOut(action="finish", finished=True, reason="已完成预设题目")

    last_answer = _last_candidate_answer(session)
    is_short = len(last_answer) < MIN_ANSWER_CHARS

    if is_short and session.followup_count == 0:
        return ActionOut(action="followup", reason="回答偏短，请补充背景、方案与结果",
                         next_question="你的回答略显简短，可以再展开一下吗？请补充一下具体的背景、你做的方案以及量化的结果数据。")

    if session.followup_count < MAX_FOLLOWUP_PER_QUESTION and _should_followup(session, last_answer):
        return ActionOut(action="followup", reason="追问当前题目细节")

    # 切下一题
    session.current_idx += 1
    session.followup_count = 0
    if session.current_idx >= main:
        return ActionOut(action="finish", finished=True, reason="题库已完成")
    nxt = session.questions[session.current_idx]
    session.current_q = nxt
    return ActionOut(action="ask", next_question=nxt.question, reason=f"进入第 {session.current_idx+1} 题：{nxt.dimension}")


def _should_followup(session: InterviewSession, answer: str) -> bool:
    # 1) 当前题目关键词已在答案命中 >= 2 个 -> 不追
    q = session.current_q
    q_text = (q.question + q.hint) if q else ""
    keywords = list({w for w in re.findall(r"[\u4e00-\u9fa5A-Za-z0-9\+#\.]{2,}", q_text)
                     if len(w) >= 2 and w not in ("什么", "如何", "哪些", "怎么", "请你", "请介绍", "请简")})
    hits = sum(1 for w in keywords if w in answer)
    if hits >= MIN_KEYWORD_HITS_TO_SKIP_FOLLOWUP:
        return False
    # 显式回答完毕不追
    if re.search(r"(回答完毕|没有了|暂时没有|以上就是|结束)$", answer[-25:]):
        return False
    # 2) 短/缺数字/缺关键句，3 条中 >= 2 条才追
    short = len(answer) < 60
    no_number = not re.search(r"\d", answer)
    no_key_sentence = not any(k in answer for k in (
        "方案", "优化", "因为", "所以", "通过", "项目", "提升", "降低", "重构", "解决", "负责",
        "选型", "对比", "备选", "指标", "命中率", "分库", "分表", "缓存", "MQ", "事务", "故障", "回滚"))
    return int(short) + int(no_number) + int(no_key_sentence) >= 2


def _last_candidate_answer(s: InterviewSession) -> str:
    for h in reversed(s.history):
        if h.get("role") == "candidate":
            return h.get("content", "")
    return ""


def append_message(session: InterviewSession, role: str, content: str, *, is_followup: bool = False):
    if role == "candidate":
        session.round += 1
        if is_followup:
            session.followup_count += 1
    session.history.append({"role": role, "content": content, "ts": time.time(),
                            "round": session.round, "is_followup": is_followup})
    session.touch()


# ==================== LLM 追问生成 ====================
FOLLOWUP_SYS = (
    "你是资深中文面试官。根据上一题「{question}」与候选人刚才的回答：\n"
    "---\n{answer}\n---\n"
    "请用 1 句话提一个自然的、聚焦细节/量化/落地的追问。不要复述题目，不要客套，直接问问题，30-60 字，纯中文。"
)

_DIM_FALLBACK_FOLLOWUPS = {
    "简历匹配": [
        "刚才提到的这段经历里，你有没有量化的产出数据（节省成本/提升效率/上线规模）？",
        "你在这段经历里的个人贡献和团队/平台贡献怎么切分？能举一个你独立推动的例子吗？",
    ],
    "专业技能": [
        "这个技术点你有深入到源码或原理级别吗？有没有遇到过反直觉的 corner case？",
        "如果让你带一个 0 经验的新人掌握这个点，你会怎么安排 1 周的学习路径和验证题？",
    ],
    "项目经验": [
        "这个项目里你主导的最大一次技术决策是什么？如果重来一次会做哪些不一样的选择？",
        "项目上线后你有没有做过复盘：哪部分的实际收益远低于预期？为什么？",
    ],
    "逻辑思维": [
        "你给出的方案最容易在哪个环节被攻击或出现瓶颈？对应的降级/熔断策略是什么？",
        "如果只给你 1/3 的资源（人力和机器），你会优先保障哪几个核心能力？为什么？",
    ],
    "沟通表达": [
        "那次协作里对方有没有反对过你的方案？你怎么回应并调整的？最终达成了什么量化结果？",
        "如果让你现在对那次沟通做一次复盘，你会把哪 2 句话换掉以提高沟通效率？",
    ],
    "职业规划": [
        "为了实现这个目标，最近 3 个月你具体做过哪些学习或实践？能展开 1-2 个例子吗？",
        "如果入职后前 6 个月和你的预期不一样，你会怎么做？说一个触发你离开的底线条件。",
    ],
    "综合素养": [
        "讲一次你在压力最大的时刻做过的关键决定：为什么这么选、结果如何？",
        "最近 6 个月，你觉得自己成长最快和成长最慢的各是什么？原因分别是什么？",
    ],
}


async def generate_followup_text(llm: LLMProvider, *, question: str, answer: str, dimension: str = "") -> str:
    try:
        msg = FOLLOWUP_SYS.format(question=question, answer=answer[:600])
        result = (await llm.chat([ChatMessage(role="user", content=msg)], temperature=0.8)).strip()[:200]
        if result and ("你刚才提到的这个项目，当时你是如何衡量技术方案的优劣" in result):
            raise ValueError("重复追问检测，回退本地维度兜底")
        if result:
            return result
    except Exception:
        pass
    import hashlib as _hl
    dim = dimension or "专业技能"
    tpls = _DIM_FALLBACK_FOLLOWUPS.get(dim) or _DIM_FALLBACK_FOLLOWUPS["专业技能"]
    h = int(_hl.md5((question + "||" + answer).encode("utf-8")).hexdigest(), 16)
    return tpls[h % len(tpls)]


# ==================== SSE 流 ====================
async def stream_text(llm: LLMProvider, text: str) -> AsyncIterator[str]:
    import asyncio
    for ch in text:
        yield ch
        await asyncio.sleep(0.015)


def wrap_data(chunk: str, *, done: bool = False, extra: dict | None = None) -> str:
    payload = {"chunk": chunk, "done": done}
    if extra:
        payload.update(extra)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def wrap_message_out(msg: MessageOut) -> str:
    return f"data: {json.dumps({'type': 'message', 'message': msg.model_dump()}, ensure_ascii=False)}\n\n"


# ==================== 会话清理 ====================
def close_session(sid: str, *, reason: str = "用户主动结束") -> bool:
    s = get_session(sid)
    if not s:
        return False
    s.finished = True
    s.history.append({"role": "interviewer", "content": CLOSING + f"（{reason}）",
                      "ts": time.time(), "round": s.round, "is_followup": False})
    s.touch()
    return True
