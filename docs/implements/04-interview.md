# 面试配置模块（interview）技术实现报告

## 1. 模块概述

实现面试的创建、列表、详情查询与状态流转（草稿/发布/关闭）。一场面试包含岗位信息、题目来源、题目集、维度权重与通过阈值。

## 2. 分层结构与文件

```
backend/app/modules/interview/
  schemas.py      InterviewIn / InterviewOut / InterviewStatusIn
  repository.py   InterviewRepository
  service.py      InterviewService
  router.py       4 个端点
  tests/test_interview.py
```

## 3. 数据模型

`interviews`：`id / org_id / title / position / jd / question_source(template|jd_generated) / questions(JSON) / dimension_weights(JSON) / pass_thresholds(JSON) / status(draft|published|closed) / created_by / created_at / updated_at`。

## 4. API 接口

| 方法 | 路径 | 说明 |
|------|------|------|
| POST | /api/v1/interviews | 创建面试 |
| GET | /api/v1/interviews?org_id= | 列表（可选按组织过滤） |
| GET | /api/v1/interviews/{interview_id} | 详情 |
| PATCH | /api/v1/interviews/{interview_id}/status | 状态流转 |

## 5. 业务逻辑

- `create`：校验组织存在、`question_source` 合法（template/jd_generated）、题目非空，再创建（`created_by` 记录创建人）。
- `list_interviews`：按 `org_id` 过滤，未提供则返回全部。
- `get`：不存在 → `NotFoundError`。
- `update_status`：校验状态值在 `{draft, published, closed}` 内。

## 6. 错误处理

组织不存在 → 404；题目来源非法 / 题目为空 / 状态非法 → 422。

## 7. 单元测试（6 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_create_interview | 创建成功（默认 draft） |
| test_create_interview_org_not_found | 组织不存在 → 404 |
| test_create_interview_invalid_source | 非法来源 → 422 |
| test_list_and_get_interview | 列表 + 详情 |
| test_get_interview_not_found | 404 |
| test_update_status | 发布状态流转 |

## 8. 依赖

`models.interview.Interview`、`modules.org.repository.OrgRepository`。
