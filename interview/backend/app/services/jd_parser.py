"""JD 岗位需求解析：规则抽取 + LLM 增强（LLM 失败自动兜底）。"""
from __future__ import annotations

import json
import re
from typing import List

from ..schemas import JDParseOut
from ..providers.llm import LLMProvider, ChatMessage

JD_SYSTEM = """你是资深招聘专家。请从岗位 JD 文本中抽取结构化信息，输出严格 JSON：
{
  "position": "岗位名称",
  "required_skills": ["Java", "MySQL"],
  "responsibilities": ["职责1"],
  "knowledge_points": ["考察核心知识点1"],
  "soft_skills": ["沟通协作"]
}
字段缺失时填空数组/空串；仅中文；无任何额外文字。"""


def _local_extract(text: str) -> JDParseOut:
    position = ""
    for line in text.splitlines():
        s = line.strip()
        if 2 <= len(s) <= 30 and any(k in s for k in ("岗", "工程", "开发", "经理", "师", "专员", "产品")):
            position = s
            break
    if not position:
        m = re.search(r"岗位[^：:：]{0,3}[：:]\s*([^\n\r]{2,40})", text)
        position = m.group(1).strip() if m else ""

    resp = _extract_block(text, ["岗位职责", "工作内容", "你将负责", "Responsibilities"])
    req = _extract_block(text, ["任职要求", "岗位要求", "任职资格", "技能要求", "Requirements", "Qualifications"])
    combined = "\n".join(resp + req)

    KEYS = ["Java", "Spring Boot", "Spring", "MyBatis", "MySQL", "Redis", "Kafka", "MongoDB", "RabbitMQ", "Docker",
            "Kubernetes", "Nginx", "Linux", "Python", "FastAPI", "Django", "Flask", "Golang", "Go", "TypeScript",
            "JavaScript", "Vue", "React", "SQL", "JVM", "分布式", "微服务", "高并发", "Hadoop", "Spark", "Flink",
            "Hive", "ETL", "机器学习", "深度学习", "NLP", "LLM", "RAG", "LangChain", "数据结构", "算法", "TCP",
            "HTTP", "项目管理", "沟通表达", "英语", "数据分析", "Tableau", "Excel", "PowerBI", "Celery"]
    skills = []
    for k in KEYS:
        if re.search(r"(?<![A-Za-z])" + re.escape(k) + r"(?![A-Za-z])", combined, flags=re.I) and k not in skills:
            skills.append(k)

    SOFT = ["沟通", "团队", "协作", "抗压", "责任心", "学习能力", "逻辑", "表达", "自驱", "英文", "英语", "文档", "跨部门", "分析", "解决问题"]
    soft = [s for s in SOFT if s in combined]

    kps = [
        *skills[:8], *soft[:4],
        "系统设计能力" if any(k in combined for k in ("架构", "设计", "分布式")) else "",
        "代码质量意识" if any(k in combined for k in ("规范", "代码", "review")) else "",
    ]
    kps = [k for k in kps if k]

    return JDParseOut(
        raw_text=text,
        position=position[:50],
        required_skills=skills[:20],
        responsibilities=resp[:10],
        knowledge_points=kps[:15],
        soft_skills=soft[:8],
    )


def _extract_block(text: str, keywords: List[str]) -> List[str]:
    lines = [l.strip() for l in text.splitlines() if l.strip()]
    capture, buf, result = False, "", []
    for line in lines:
        if any(k in line for k in keywords):
            capture = True
            if buf.strip():
                result.append(buf.strip())
            buf = ""
            continue
        if capture:
            if re.match(r"^[\u4e00-\u9fa5A-Za-z]{2,12}[：:]$", line) or (
                re.match(r"^[\u4e00-\u9fa5A-Za-z]{2,12}\s*$", line)
                and not any(c in "0123456789.、-（）()【】·•" for c in line)
            ):
                if buf.strip():
                    result.append(buf.strip())
                capture, buf = False, ""
                continue
            if re.match(r"^[\d一二三四五六七八九十①②③④⑤⑥⑦⑧⑨⑩·\-\.•、\)]", line) or len(buf) == 0:
                if buf.strip():
                    result.append(buf.strip())
                buf = line
            else:
                buf = (buf + " " + line).strip()
    if buf.strip():
        result.append(buf.strip())
    return [r[:500] for r in result if 6 < len(r) < 700][:12]


async def parse_jd_text(text: str, *, llm: LLMProvider) -> JDParseOut:
    if not text or len(text.strip()) < 10:
        raise ValueError("JD 内容过短，请输入完整岗位描述与任职要求")
    local = _local_extract(text.strip())
    need_llm = len(local.required_skills) < 3 or len(local.knowledge_points) < 4 or not local.position
    if not need_llm:
        return local
    try:
        raw = await llm.chat(
            [ChatMessage(role="system", content=JD_SYSTEM),
             ChatMessage(role="user", content=text.strip()[:6000])],
            temperature=0.2, response_json=True,
        )
        data = json.loads(_strip(raw))
        return JDParseOut(
            raw_text=text.strip(),
            position=data.get("position") or local.position,
            required_skills=_merge(local.required_skills, data.get("required_skills", []))[:20],
            responsibilities=_merge(local.responsibilities, data.get("responsibilities", []))[:12],
            knowledge_points=_merge(local.knowledge_points, data.get("knowledge_points", []))[:15],
            soft_skills=_merge(local.soft_skills, data.get("soft_skills", []))[:10],
        )
    except Exception:
        return local


def _strip(s: str) -> str:
    s = s.strip()
    if s.startswith("```"):
        s = re.sub(r"^```(?:json)?\s*", "", s)
        s = re.sub(r"\s*```$", "", s)
    return s.strip()


def _merge(a, b):
    seen, out = set(), []
    for x in [*a, *b]:
        xs = str(x).strip()
        if xs and xs not in seen:
            seen.add(xs)
            out.append(xs)
    return out
