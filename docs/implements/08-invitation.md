# 邀请模块（invitation）技术实现报告

## 1. 模块概述

为面试生成候选人邀请链接（带不可猜测的签名 token 与有效期），并提供 token 校验端点供候选人通过链接进入面试。

## 2. 分层结构与文件

```
backend/app/modules/invitation/
  schemas.py      InvitationOut / InvitationValidateOut
  repository.py   InvitationRepository
  service.py      InvitationService
  router.py       2 个端点
  tests/test_invitation.py
```

## 3. 数据模型

`invitations`：`id / interview_id / token(唯一) / expires_at / created_by / created_at`。

## 4. API 接口

| 方法 | 路径 | 鉴权 |
|------|------|------|
| POST | /api/v1/interviews/{interview_id}/invite | 企业 |
| GET | /api/v1/invitations/{token} | 公开 |

## 5. 业务逻辑

- `create`：校验面试存在；用 `secrets.token_urlsafe(32)` 生成 token；默认 7 天有效期；返回 `{token, url, interview_id, expires_at}`。
- `validate`：token 不存在 → 404；已过期 → 422；否则返回 `{interview_id, valid: true}`。

## 6. 安全设计

- token 使用密码学安全随机数生成，不可猜测（对应 PRD「邀请链接带签名并支持有效期，防滥用」）。
- 校验端点公开访问，但不泄露面试细节，仅返回 `interview_id`，候选人凭 token 进入后续流程。

## 7. 单元测试（3 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_create_and_validate_invite | 生成 + 校验闭环 |
| test_create_invite_interview_not_found | 404 |
| test_validate_invalid_token | 404 |

## 8. 依赖

`models.invitation.Invitation`、`modules.interview.repository.InterviewRepository`。
