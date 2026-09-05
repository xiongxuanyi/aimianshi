"""
LLM Provider 抽象。
- FakeLLM: 无密钥/调试时返回确定性中文脚本，实训离线可跑通；
- OpenAICompatLLM: 调用任何兼容 OpenAI /chat/completions 的服务。
"""
from __future__ import annotations

import json
import re
import hashlib
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import AsyncIterator, List

import httpx

from ..config import settings


@dataclass
class ChatMessage:
    role: str = "user"   # system / user / assistant
    content: str = ""


class LLMProvider(ABC):
    @abstractmethod
    async def chat(self, messages: List[ChatMessage], *, temperature: float | None = None,
                   response_json: bool = False) -> str: ...

    @abstractmethod
    async def stream(self, messages: List[ChatMessage], *, temperature: float | None = None) -> AsyncIterator[str]: ...


# ==================================================================
# Fake LLM（实训离线可运行）
# ==================================================================
class FakeLLM(LLMProvider):
    def __init__(self, *, delay_s: float = 0.02):
        self.delay_s = delay_s
        self.calls: List[List[ChatMessage]] = []

    async def _sleep(self):
        import asyncio
        await asyncio.sleep(self.delay_s)

    async def chat(self, messages, *, temperature=None, response_json=False):
        self.calls.append(messages)
        await self._sleep()
        last_user = ""
        for m in reversed(messages):
            if m.role == "user":
                last_user = m.content[:80]
                break

        if response_json or "请输出 JSON" in last_user or "JSON" in "".join(m.content for m in messages[:3]):
            return json.dumps(_FAKE_JSON_PAYLOAD, ensure_ascii=False)

        # 纯文本（追问）场景：维度感知模板库，避免"永远同一句话"
        return _fake_followup_from_messages(messages)

    async def stream(self, messages, *, temperature=None):
        text = await self.chat(messages, temperature=temperature)
        for ch in text:
            await self._sleep()
            yield ch


_FAKE_JSON_PAYLOAD = {
    "name": "张三",
    "skills": ["Java", "Spring Boot", "MySQL"],
    "experiences": ["后端开发 2 年", "高并发电商系统优化"],
    "projects": ["订单中台重构（QPS 从 800 提升到 5000）"],
    "knowledge_points": ["JVM", "多线程", "分布式缓存", "MySQL 索引"],
    "questions": [
        {"id": 1, "dimension": "简历匹配", "question": "请介绍你在订单中台重构项目中主要承担的工作，以及解决过的核心技术难点。", "hint": "可以按 STAR 法则展开"},
        {"id": 2, "dimension": "专业技能", "question": "HashMap 与 ConcurrentHashMap 在 JDK1.8 中的底层实现与线程安全策略有何区别？", "hint": "可从数组+链表+红黑树、锁粒度展开"},
        {"id": 3, "dimension": "项目经验", "question": "你提到把 QPS 从 800 提升到 5000，具体采用了哪些手段？瓶颈是如何定位的？", "hint": "关注监控、SQL、缓存、异步化"},
        {"id": 4, "dimension": "逻辑思维", "question": "假设 Redis 缓存集群整体不可用，你会如何降级和恢复？", "hint": "熔断、限流、本地缓存、预热"},
        {"id": 5, "dimension": "职业规划", "question": "未来 3 年的职业规划是什么？更偏架构、管理还是技术专家路线？", "hint": ""},
        {"id": 6, "dimension": "沟通表达", "question": "举一个跨部门协作的案例：你遇到的阻力、怎么沟通协调、最终结果与量化数据。", "hint": ""},
        {"id": 7, "dimension": "综合素养", "question": "说一次你遇到的线上严重故障：发生了什么、你怎么定位、如何止损复盘、避免复发。", "hint": ""},
    ],
    "total_score": 82,
    "level": "良好",
    "dimensions": [
        {"dimension": "专业匹配度", "score": 85, "comment": "简历技能栈与岗位要求匹配 85%，并有实际项目佐证"},
        {"dimension": "逻辑表达", "score": 78, "comment": "表达整体有条理，但在跨模块协作场景描述上略欠层次"},
        {"dimension": "应答完整性", "score": 80, "comment": "对技术问题能回答到实现层面，缺少量化结果与对比方案"},
        {"dimension": "项目深度", "score": 76, "comment": "项目背景与职责描述清晰，遇到的难点与选型权衡描述偏浅"},
        {"dimension": "综合素养", "score": 75, "comment": "态度端正、配合度高，职业方向基本稳定，具备较好成长性"},
    ],
    "highlights": "后端工程基础扎实，有真实高并发项目经验，回答诚实有条理。",
    "weaknesses": "分布式事务、容灾演练经验偏少；部分回答缺少量化指标对比。",
    "suggestions": [
        "补充分布式事务（TCC / SAGA / 本地消息表）的落地案例",
        "回答问题时注意量化：响应时间降低 XX%、资源成本节省 YY 元",
        "准备 1-2 个跨团队推动的软技能案例",
        "把 1 个项目按背景-目标-行动-结果（STAR）+ 指标复盘整理成背诵稿",
    ],
    "transcript_summary": "面试共 6 轮，候选人围绕简历项目逐一作答，技术问题大部分能答到实现层。",
}


# ==================================================================
# FakeLLM 中文追问模板库（按题目维度 + 回答要点个性化）
# ==================================================================
_FOLLOWUP_BY_HINT = {
    "MySQL": [
        "能否展开讲讲你加的索引是哪一种（联合/覆盖/前缀）？当时 SQL 的执行计划（EXPLAIN）哪些关键列变化了？",
        "当时有没有遇到加索引后写入放大、或选错索引的回表现象？怎么处理的？",
        "你提到的优化，是 OLTP 还是 OLAP 场景？命中率 / 返回行数 / 回表次数前后的数据是？",
    ],
    "Redis": [
        "具体用到了哪种数据结构（String/Hash/ZSet/Stream/Bitmap）？为什么选它而不是其他结构？",
        "有没有遇到缓存击穿 / 穿透 / 雪崩？怎么设过期策略、怎么做热点 key 的本地缓存兜底？",
        "Redis Cluster 还是主从 + 哨兵？故障切换时应用层有没有做双读 / 降级？",
    ],
    "Kafka": [
        "Topic 多少分区？消费位点是手动提交还是自动？如何保证 Exactly-Once 语义？",
        "遇到过消息堆积吗？当时消费 LAG 多少？怎么扩容消费者、如何处理消息乱序与重复？",
        "你提到的场景里，为什么选 Kafka 而不是 RocketMQ / RabbitMQ？选型的核心指标是什么？",
    ],
    "Java": [
        "JVM 当时用什么垃圾回收器？有没有观察过 GC 日志：YGC/FGC 次数、停顿时间怎么变化的？",
        "你提到过并发场景：用的是 synchronized / ReentrantLock 还是 ConcurrentHashMap？为什么？",
        "有没有用过线程池？核心参数（core/max/queue/reject）怎么设，依据是什么？",
    ],
    "Spring": [
        "有没有用到 Spring 的事务传播机制？遇到过事务不生效的场景吗？根因是什么？",
        "你提到的 Bean 循环依赖、AOP 切面失效，这类问题遇到过吗？如何排查？",
        "Spring Boot 自动装配原理能简单展开讲讲吗？Starter 是怎么被加载的？",
    ],
    "FastAPI": [
        "依赖注入（Depends）在你的项目里主要用于什么场景？有没有做过全局中间件？",
        "异步路由 vs 同步路由，在你的项目里怎么划分？async def 下是否有阻塞 IO 导致 starve？",
        "Pydantic 你常用哪些校验？请求体/响应模型分离了吗？",
    ],
    "Vue": [
        "Vue3 Composition API 下，你怎么拆分业务逻辑？有没有做过自定义 Hook 抽公共能力？",
        "响应式原理：ref 和 reactive 的区别？深层嵌套对象更新会触发视图重渲染吗？",
        "页面首屏性能优化做过哪些？Vite 打包体积从多少降到多少？",
    ],
    "React": [
        "你提到的性能优化：useMemo/useCallback 怎么用？什么情况下会反而更慢？",
        "Context vs Redux/Zustand 在你的项目里是如何划分职责的？",
        "SSR / CSR 在你的业务场景怎么选型？首屏 TTI 大概多少？",
    ],
    "项目": [
        "项目里你主导的最大一次技术决策是什么？如果重来一次你会怎么做不一样的选择？",
        "项目中最难推进的跨团队协作是什么？你作为推动者做了哪些具体动作？怎么说服对方的？",
        "你在项目里负责的模块，出过大故障吗？故障发现、定位、止损、复盘，你分别做了什么？",
    ],
    "架构": [
        "如果业务量翻 10 倍，你的系统会先在哪个环节瓶颈？如何提前扩容和降级？",
        "有没有做过可观测性建设？Metrics/Logging/Tracing 三条链路是怎么打通的？",
        "对于数据库主从延迟、消息重复、接口超时这 3 个典型分布式问题，你分别怎么治理？",
    ],
    "假设": [
        "你描述的方案如果在实际执行中遇到网络分区，数据一致性会降级到什么级别？业务方接受吗？",
        "在你给的方案里，哪一步最容易被攻击或滥用？有没有对应的限流、签名、幂等？",
        "如果只给你 1/3 的资源（人 + 机器），你会砍掉哪些功能、优先保障哪些？为什么？",
    ],
    "故障": [
        "当时 5xx 的比例是多少？核心交易订单有没有丢失或重复？怎么保证数据最终一致？",
        "监控告警在故障发生时是第几分钟触发的？后来你们做了哪些改进缩短 MTTD/MTTR？",
        "复盘会上有没有发现之前的压测没覆盖到的点？为什么？",
    ],
    "沟通": [
        "那次协作里，你有没有被对方否定过方案？你怎么回应和调整的？最终达成了什么数据结果？",
        "你怎么向上级汇报坏消息？有没有案例？汇报框架和数据是什么？",
        "当你和产品经理在需求理解上有分歧，你会用什么方式拉齐认知？",
    ],
    "职业": [
        "为了达到你说的 1 年/3 年目标，你现在具体在做什么学习或实践？能展开 1-2 个例子吗？",
        "为什么选择我们公司/这个方向？你对比过哪些备选 offer / 行业方向？",
        "如果入职 6 个月后发现岗位和预期不同，你会怎么做？",
    ],
    "__DEFAULT__": [
        "在你说的这个方案里，核心 trade-off 是什么？（一致性 vs 可用性 / 成本 vs 体验 / 开发速度 vs 长期可维护）",
        "当时有没有对比过至少 2 种备选方案？能分别列 3 条优缺点和最终选择依据吗？",
        "你刚才提到的那个指标（QPS / P99 / 成本 / 转化率 / 留存），具体是怎么测量的？基线是什么？",
        "如果让你现在复盘重做一遍，你会从哪 3 个方面改进？为什么这 3 个是收益最高的？",
        "这件事里你最满意和最后悔的点分别是什么？下次类似情况你会怎么不一样？",
    ],
}


def _detect_dimension_from_question(q: str) -> str:
    for k in _FOLLOWUP_BY_HINT.keys():
        if k == "__DEFAULT__":
            continue
        if k in q:
            return k
    if any(w in q for w in ("故障", "排查", "止损", "报警", "超时")):
        return "故障"
    if any(w in q for w in ("假设", "如果", "怎么设计", "如何处理")):
        return "假设"
    if any(w in q for w in ("项目", "负责", "承担", "重构")):
        return "项目"
    if any(w in q for w in ("架构", "高并发", "分布式", "可扩展")):
        return "架构"
    if any(w in q for w in ("沟通", "协作", "跨部门", "团队")):
        return "沟通"
    if any(w in q for w in ("规划", "未来", "目标", "职业", "三年", "1年")):
        return "职业"
    return "__DEFAULT__"


def _fake_followup_from_messages(messages: List[ChatMessage]) -> str:
    blob = "\n".join(m.content for m in messages)
    q_match = re.search(r"上一题「([\s\S]{1,200}?)」", blob)
    question = q_match.group(1).strip() if q_match else ""
    ans_match = re.search(r"---\n([\s\S]{1,800})\n---", blob)
    answer = ans_match.group(1).strip() if ans_match else blob[-200:]

    dim = _detect_dimension_from_question(question)
    templates = _FOLLOWUP_BY_HINT.get(dim) or _FOLLOWUP_BY_HINT["__DEFAULT__"]
    h = int(hashlib.md5((question + "||" + answer).encode("utf-8")).hexdigest(), 16)
    tpl = templates[h % len(templates)]

    hooks = []
    if not re.search(r"\d", answer):
        hooks.append("可以加上具体数字（QPS / P99 / 成本 / 百分比）再补充一下吗？")
    if not any(k in answer for k in ("方案", "选型", "备选", "对比", "为什么")):
        hooks.append("另外也想听听你当时对比过哪些备选方案，为什么选现在这个？")
    if not any(k in answer for k in ("结果", "效果", "数据", "降低", "提升", "节省")):
        hooks.append("最后能补一下这件事最终的效果数据与业务影响吗？")

    suffix = ""
    if hooks:
        suffix = " 另外，" + hooks[0]
    return (tpl + suffix).strip()[:200]


# ==================================================================
# OpenAI 兼容 HTTP Provider
# ==================================================================
class OpenAICompatLLM(LLMProvider):
    def __init__(self):
        self.base = settings.llm_base_url.rstrip("/")
        self.key = settings.llm_api_key
        self.model = settings.llm_model

    def _payload(self, messages, stream: bool, temperature: float, response_format=None) -> dict:
        payload = {
            "model": self.model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
            "stream": stream,
            "temperature": temperature,
        }
        if response_format:
            payload["response_format"] = response_format
        return payload

    def _headers(self) -> dict:
        return {"Authorization": f"Bearer {self.key}"}

    async def chat(self, messages, *, temperature=None, response_json=False):
        t = temperature if temperature is not None else settings.llm_temperature
        rf = {"type": "json_object"} if response_json else None
        payload = self._payload(messages, stream=False, temperature=t, response_format=rf)
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            r = await client.post(f"{self.base}/chat/completions", json=payload, headers=self._headers())
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]

    async def stream(self, messages, *, temperature=None):
        t = temperature if temperature is not None else settings.llm_temperature
        payload = self._payload(messages, stream=True, temperature=t)
        async with httpx.AsyncClient(timeout=settings.llm_timeout) as client:
            async with client.stream("POST", f"{self.base}/chat/completions", json=payload, headers=self._headers()) as resp:
                resp.raise_for_status()
                async for raw_line in resp.aiter_lines():
                    line = raw_line.strip()
                    if not line.startswith("data:"):
                        continue
                    body = line[5:].strip()
                    if not body or body == "[DONE]":
                        continue
                    try:
                        j = json.loads(body)
                        chunk = j["choices"][0].get("delta", {}).get("content")
                        if chunk:
                            yield chunk
                    except Exception:
                        continue


# ==================================================================
# 工厂
# ==================================================================
_provider: LLMProvider | None = None


def get_llm() -> LLMProvider:
    global _provider
    if _provider is None:
        _provider = OpenAICompatLLM() if settings.llm_api_key else FakeLLM()
    return _provider


def set_llm_for_tests(p: LLMProvider):
    global _provider
    _provider = p
