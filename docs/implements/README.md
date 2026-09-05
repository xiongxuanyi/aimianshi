# AI 面试官后端 —— 技术实现报告（总览）

本目录包含后端每个模块的详细技术实现报告。对应源码位于 `backend/`。

## 1. 项目概述

基于 PRD 和 MySQL 设计（`docs/design/script.sql`）实现的企业招聘 AI 面试后端，提供：
企业端与候选人端账户、组织成员、内置题库与 JD 生成题目、面试配置、候选人面试会话（AI 对话）、AI 结构化评分、HR 评审、候选人邀请链接。

## 2. 技术栈

- Python 3.12 / FastAPI / SQLAlchemy 2.0（ORM，同步会话）
- 数据库：生产 MySQL（`mysql+pymysql`），测试 SQLite 内存库
- LLM：DeepSeek（OpenAI 兼容接口，`httpx` 直连）
- 认证：JWT（Bearer），`PyJWT` + `bcrypt`
- 测试：pytest + FastAPI TestClient + FakeLLMClient

## 3. 架构：分层 + 一模块一包

```
router（HTTP/校验） → service（业务逻辑） → repository（数据访问）
```

每个业务模块一个包，内部严格分层：

```
backend/app/
  core/           配置、数据库、安全(JWT/密码)、错误层级、依赖注入
  models/         SQLAlchemy 模型（对应 script.sql 的 10 张表）
  llm/            LLMClient 抽象 + DeepSeekLLMClient + FakeLLMClient
  modules/
    auth/         router.py service.py repository.py schemas.py tests/
    org/          同上
    question/     同上
    interview/    同上
    session/      同上
    evaluation/   同上
    review/       同上
    invitation/   同上
```

关键设计：
- **LLM 抽象**：业务代码只依赖 `LLMClient` 接口，生产用 `DeepSeekLLMClient`，测试用 `FakeLLMClient`（脚本化响应 + 记录调用），通过 `get_llm()` 依赖注入，测试 `dependency_overrides` 替换。
- **错误层级**：`AppError` 及其子类（NotFound/Unauthorized/Forbidden/Conflict/Validation），`main.py` 注册全局异常处理器，统一返回 `{"code", "detail"}`。
- **事务**：repository 负责 `add/flush`，service 负责 `commit`。
- **权限**：`require_enterprise` / `require_candidate` 依赖区分两类账户。

## 4. API 端点总览（25 个）

| 模块 | 方法 | 路径 | 鉴权 |
|------|------|------|------|
| auth | POST | /api/v1/auth/register | 公开 |
| auth | POST | /api/v1/auth/login | 公开 |
| auth | POST | /api/v1/auth/candidate/register | 公开 |
| auth | POST | /api/v1/auth/candidate/login | 公开 |
| org | POST | /api/v1/orgs | 企业 |
| org | GET | /api/v1/orgs/{org_id}/members | 企业 |
| org | POST | /api/v1/orgs/{org_id}/members | 企业 |
| question | GET | /api/v1/templates | 企业 |
| question | GET | /api/v1/templates/{template_id} | 企业 |
| question | POST | /api/v1/interviews/generate-questions | 企业 |
| interview | POST | /api/v1/interviews | 企业 |
| interview | GET | /api/v1/interviews | 企业 |
| interview | GET | /api/v1/interviews/{interview_id} | 企业 |
| interview | PATCH | /api/v1/interviews/{interview_id}/status | 企业 |
| session | POST | /api/v1/sessions | 候选人 |
| session | GET | /api/v1/sessions/{session_id} | 候选人 |
| session | GET | /api/v1/sessions/{session_id}/messages | 候选人 |
| session | POST | /api/v1/sessions/{session_id}/messages | 候选人 |
| evaluation | POST | /api/v1/sessions/{session_id}/evaluate | 企业 |
| evaluation | GET | /api/v1/sessions/{session_id}/evaluation | 企业 |
| review | POST | /api/v1/sessions/{session_id}/review | 企业 |
| review | GET | /api/v1/sessions/{session_id}/reviews | 企业 |
| invitation | POST | /api/v1/interviews/{interview_id}/invite | 企业 |
| invitation | GET | /api/v1/invitations/{token} | 公开 |
| — | GET | /api/v1/health | 公开 |

## 5. 如何运行

```bash
cd backend
py -3.12 -m venv .venv
.venv/Scripts/python.exe -m pip install -r requirements.txt

# 复制并填写 .env（DeepSeek Key、MySQL URL）
cp .env.example .env

# 启动（默认 sqlite 可本地起；生产填 MySQL URL）
.venv/Scripts/python.exe -m uvicorn app.main:app --reload

# 运行测试
.venv/Scripts/python.exe -m pytest
```

## 6. 测试结果

全量 **37 个测试全部通过**，覆盖 8 个模块的 25 个端点（含正常流程与错误分支）。

| 模块 | 测试数 | 报告 |
|------|--------|------|
| auth | 6 | [01-auth.md](01-auth.md) |
| org | 5 | [02-org.md](02-org.md) |
| question | 5 | [03-question.md](03-question.md) |
| interview | 6 | [04-interview.md](04-interview.md) |
| session | 6 | [05-session.md](05-session.md) |
| evaluation | 3 | [06-evaluation.md](06-evaluation.md) |
| review | 3 | [07-review.md](07-review.md) |
| invitation | 3 | [08-invitation.md](08-invitation.md) |

## 7. 已知简化与后续

- 会话编排当前为「LLM 依据面试题目 + 对话历史自由回复」，尚未实现严格的「逐题 → 追问上限 → 收尾」状态机（见 PRD §6.1）。
- 语音 ASR/TTS 未在本后端实现（前端录音上传 + 转写接口留待 M3）。
- 组织成员权限仅到「企业用户」粒度，未按「admin vs hr」细分操作授权。
- DeepSeek 的流式输出（SSE）未实现，当前为一次性补全。
- `datetime.utcnow()` 存在 Python 3.12 弃用告警（保留 naive UTC 以兼容 MySQL DATETIME），无功能影响。
