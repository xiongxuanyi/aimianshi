# 评分模块（evaluation）技术实现报告

## 1. 模块概述

面试结束后，由企业端触发 AI 对整场面试对话进行结构化评分，产出评估报告（总分、维度分、逐题点评、亮点/不足、通过建议与理由）。

## 2. 分层结构与文件

```
backend/app/modules/evaluation/
  schemas.py      EvaluationOut
  repository.py   EvaluationRepository
  service.py      EvaluationService（LLM 结构化评分）
  router.py       2 个端点
  tests/test_evaluation.py
```

## 3. 数据模型

`evaluations`：`id / session_id / total_score / dimension_scores(JSON) / per_question(JSON) / highlights / weaknesses / recommendation(pass|pending|reject) / reason / created_at`（一个会话一条评分）。

## 4. API 接口

| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/v1/sessions/{session_id}/evaluate | 企业 |
| GET | /api/v1/sessions/{session_id}/evaluation | 企业 |

## 5. LLM 集成（DeepSeek）

- `evaluate` 通过 `LLMClient.chat_json()` 要求模型返回结构化 JSON。
- `EVAL_SYSTEM` 提示词规定评分 JSON 结构；输入为整场对话转写（`面试官：... / 候选人：...` 逐行拼接）。
- 生产 `DeepSeekLLMClient` 使用 `response_format={"type":"json_object"}` 保证 JSON 输出。
- 测试注入 `FakeLLMClient`（`json_reply`），断言评分字段正确写入、`json_calls` 被调用一次。

## 6. 业务逻辑

- `evaluate`：会话不存在 → 404；获取对话转写 → LLM 结构化评分 → 校验 7 个必填字段（`total_score / dimension_scores / per_question / highlights / weaknesses / recommendation / reason`，缺字段 → 422）→ 写入 `evaluations` → 会话状态置 `evaluated`、写入 `finished_at`。
- `get_evaluation`：查询已生成的评估报告，不存在 → 404。

## 7. 单元测试（3 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_evaluate_and_get | 评分 + 查询报告（含调用计数） |
| test_evaluate_session_not_found | 404 |
| test_get_evaluation_not_found | 404 |

## 8. 依赖

`models.evaluation.Evaluation`、`modules.session.repository`（`SessionRepository` / `MessageRepository`）、`llm.base`。
