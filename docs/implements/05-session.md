# 会话模块（session）技术实现报告

## 1. 模块概述

实现候选人面试会话的核心：开启会话（AI 开场白）、查询会话、查询消息历史、发送消息并获取 AI 面试官回复。

## 2. 分层结构与文件

```
backend/app/modules/session/
  schemas.py      SessionCreateIn / SessionOut / MessageOut / SendMessageIn
  repository.py   SessionRepository + MessageRepository
  service.py      SessionService（对话编排 + 提示词构建）
  router.py       4 个端点
  tests/test_session.py
```

## 3. 数据模型

- `interview_sessions`：`id / interview_id / candidate_id / status(in_progress|finished|evaluated) / started_at / finished_at / created_at`。
- `messages`：`id / session_id / role(interviewer|candidate) / content / kind(text|voice) / recording_url / seq / created_at`。

## 4. API 接口

| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/v1/sessions | 候选人 |
| GET | /api/v1/sessions/{session_id} | 候选人 |
| GET | /api/v1/sessions/{session_id}/messages | 候选人 |
| POST | /api/v1/sessions/{session_id}/messages | 候选人 |

## 5. LLM 集成（DeepSeek）

- `send_message` 通过 `LLMClient.chat()` 生成 AI 面试官回复。
- `_build_prompt` 组装消息：system 提示词 → 面试题目列表（system）→ 对话历史（按 `seq` 排序，映射为 assistant/user）。
- 测试注入 `FakeLLMClient`（`reply` 为脚本化回复），断言 `chat_calls` 被调用一次、回复内容正确、消息数正确。

## 6. 业务逻辑

- `start`：校验面试存在；同一候选人同一面试若已有会话则幂等返回；否则创建会话并写入开场白（seq=1）。
- `get`：会话存在 + 候选人所有权校验（`candidate_id` 匹配，否则 `ForbiddenError`）。
- `list_messages`：先做所有权校验，再按 `seq` 返回。
- `send_message`：校验内容非空 → 追加候选人消息（`seq` 自增）→ 构建提示词 → LLM 回复 → 追加面试官消息 → 返回回复。

## 7. 数据访问

`next_seq` 用 `MAX(seq)` 计算下一序号，保证会话内消息顺序唯一。

## 8. 错误处理

面试/会话不存在 → 404；非本人会话 → 403；空消息 → 422；非候选人 → 403（`require_candidate`）。

## 9. 单元测试（6 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_start_session_creates_greeting | 开场白写入 |
| test_start_session_requires_candidate | 企业用户开启 → 403 |
| test_start_session_interview_not_found | 404 |
| test_send_message_gets_ai_reply | AI 回复 + 调用计数 + 消息数 |
| test_send_message_empty_content | 空消息 → 422 |
| test_other_candidate_cannot_access | 他人会话 → 403 |

## 10. 依赖

`models.session`、`models.interview`（经 `modules.interview.repository.InterviewRepository`）、`llm.base`。
