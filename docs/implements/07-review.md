# 评审模块（review）技术实现报告

## 1. 模块概述

在 AI 评分报告之上，由 HR 进行人工复核：标注「通过 / 淘汰 / 待定」并附备注，支持查询某场面试的评审记录。

## 2. 分层结构与文件

```
backend/app/modules/review/
  schemas.py      ReviewIn / ReviewOut
  repository.py   ReviewRepository
  service.py      ReviewService
  router.py       2 个端点
  tests/test_review.py
```

## 3. 数据模型

`reviews`：`id / session_id / reviewer_id / decision(pass|reject|pending) / note / created_at`。

## 4. API 接口

| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/v1/sessions/{session_id}/review | 企业 |
| GET | /api/v1/sessions/{session_id}/reviews | 企业 |

## 5. 业务逻辑

- `add_review`：会话不存在 → 404；决策值校验（`pass/reject/pending`，非法 → 422）；写入评审记录（`reviewer_id` 为当前用户）。
- `list_reviews`：按会话返回评审记录列表。

## 6. 单元测试（3 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_add_and_list_review | 添加 + 列表 |
| test_add_review_invalid_decision | 非法决策 → 422 |
| test_add_review_session_not_found | 404 |

## 7. 依赖

`models.evaluation.Review`、`modules.session.repository.SessionRepository`。
