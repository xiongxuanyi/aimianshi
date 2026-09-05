# 题库模块（question）技术实现报告

## 1. 模块概述

提供内置题库模板的查询，以及基于岗位 JD 调用大模型（DeepSeek）生成面试题的能力。

## 2. 分层结构与文件

```
backend/app/modules/question/
  schemas.py      TemplateOut / JdIn / GeneratedQuestionsOut
  repository.py   TemplateRepository
  service.py      QuestionService（含 JD 生成）
  router.py       3 个端点
  tests/test_question.py
```

## 3. 数据模型

`question_templates`：`id / title / industry / position / dimensions(JSON) / questions(JSON) / created_at / updated_at`。

## 4. API 接口

| 方法 | 路径 | 鉴权 |
|------|------|------|
| GET | /api/v1/templates | 企业 |
| GET | /api/v1/templates/{template_id} | 企业 |
| POST | /api/v1/interviews/generate-questions | 企业 |

`generate-questions` 请求体 `{jd}`，响应 `{dimensions, questions}`。

## 5. LLM 集成（DeepSeek）

- 通过 `LLMClient.chat_json()` 调用，要求模型返回 JSON 对象。
- `GEN_SYSTEM` 提示词要求输出 `{"dimensions": [...], "questions": [{"question","hint","dimension"}]}`。
- 生产实现 `DeepSeekLLMClient` 使用 `response_format={"type":"json_object"}` 强制 JSON 输出（DeepSeek 的 OpenAI 兼容接口）。
- 测试注入 `FakeLLMClient`，断言 `json_calls` 被调用一次，且返回内容被正确解析。

## 6. 业务逻辑

- `list_templates` / `get_template`：查询模板；模板不存在 → `NotFoundError`。
- `generate_questions`：JD 为空 → `ValidationError`；否则调用 LLM 并抽取 `dimensions` / `questions` 字段。

## 7. 单元测试（5 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_list_templates | 列表返回种子模板 |
| test_get_template | 详情返回 |
| test_get_template_not_found | 404 |
| test_generate_questions | JD 生成（fake 响应 + 调用计数） |
| test_generate_questions_empty_jd | 空 JD → 422 |

## 8. 依赖

`models.interview.QuestionTemplate`、`llm.base`（`ChatMessage` / `LLMClient`）。
