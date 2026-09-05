# 认证模块（auth）技术实现报告

## 1. 模块概述

实现企业用户与候选人两类账户的注册与登录，签发 JWT。两类账户共用 `users` 表，通过 `user_type` 字段区分。

## 2. 分层结构与文件

```
backend/app/modules/auth/
  schemas.py      RegisterIn / LoginIn / UserOut / TokenOut
  repository.py   UserRepository
  service.py      AuthService
  router.py       4 个端点
  tests/test_auth.py
```

- **router**：解析请求、调用 service、用 `TokenOut` 序列化响应。
- **service**：注册（邮箱唯一校验、密码哈希、签发 token）、登录（密码校验、账户类型校验）。
- **repository**：`get_by_email`、`create`。

## 3. 数据模型

`users` 表（`backend/app/models/user.py`）：`id / email(唯一) / hashed_password / user_type / name / created_at / updated_at`。

## 4. API 接口

| 方法 | 路径 | 请求体 | 响应 |
|------|------|--------|------|
| POST | /api/v1/auth/register | `{email, password, name}` | `{token, user_type, user}` |
| POST | /api/v1/auth/login | `{email, password}` | `{token, user_type, user}` |
| POST | /api/v1/auth/candidate/register | `{email, password, name}` | `{token, user_type, user}` |
| POST | /api/v1/auth/candidate/login | `{email, password}` | `{token, user_type, user}` |

## 5. 业务逻辑

- 密码用 `bcrypt` 哈希（`core/security.py`），明文不落库。
- JWT `sub` 为用户 ID，`user_type` 存入 claim，过期时间由 `ACCESS_TOKEN_EXPIRE_MINUTES` 控制。
- 注册重复邮箱 → `ConflictError`（409）；密码错误 → `UnauthorizedError`（401）；账户类型不匹配（候选人登录企业入口）→ `ForbiddenError`（403）。

## 6. 错误处理

复用 `core/errors.py` 的类型化错误，由 `main.py` 全局处理器统一返回 `{"code","detail"}`。

## 7. 单元测试（6 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_health | 健康检查 |
| test_enterprise_register_and_login | 企业注册 + 登录成功 |
| test_register_duplicate_email_conflict | 重复邮箱 409 |
| test_login_wrong_password_unauthorized | 错误密码 401 |
| test_candidate_register_and_login | 候选人注册 + 登录成功 |
| test_candidate_cannot_login_enterprise | 候选人登企业入口 403 |

## 8. 依赖

`core.security`、`core.errors`、`models.user`。无跨模块依赖。
