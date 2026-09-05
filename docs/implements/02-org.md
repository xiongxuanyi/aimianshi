# 组织模块（org）技术实现报告

## 1. 模块概述

实现企业组织与成员管理：创建组织（创建者自动成为管理员）、添加成员（分配 admin/hr 角色）、查询成员列表。

## 2. 分层结构与文件

```
backend/app/modules/org/
  schemas.py      OrgIn / OrgOut / MemberIn / MemberOut
  repository.py   OrgRepository
  service.py      OrgService
  router.py       3 个端点
  tests/test_org.py
```

## 3. 数据模型

- `organizations`：`id / name / created_at / updated_at`。
- `memberships`：`id / org_id / user_id / role(admin|hr) / created_at`（组织-用户多对多，`org_id + user_id` 唯一）。

## 4. API 接口

| 方法 | 路径 | 请求体 | 鉴权 |
|------|------|--------|------|
| POST | /api/v1/orgs | `{name}` | 企业 |
| GET | /api/v1/orgs/{org_id}/members | — | 企业 |
| POST | /api/v1/orgs/{org_id}/members | `{email, role}` | 企业 |

## 5. 业务逻辑

- `create_org`：创建组织 + 为创建者写入 `admin` 成员关系（事务提交）。
- `add_member`：校验组织存在、角色合法（admin/hr）、目标用户存在且为 `enterprise` 类型，再写入成员关系。
- `list_members`：`Membership` 与 `User` JOIN 查询，返回成员及用户姓名/邮箱。

## 6. 数据访问

`list_members` 用单次 JOIN 查询避免 N+1（`membership.user_id == user.id`）。

## 7. 错误处理

组织不存在 → `NotFoundError`；角色非法或目标非企业用户 → `ValidationError`（422）；非企业用户访问 → `ForbiddenError`（403，来自 `require_enterprise`）。

## 8. 单元测试（5 个，全部通过）

| 测试 | 覆盖 |
|------|------|
| test_create_org | 创建组织成功 |
| test_create_org_requires_enterprise | 候选人创建 → 403 |
| test_add_member_and_list | 添加成员 + 列表（含 admin+hr） |
| test_add_member_invalid_role | 非法角色 → 422 |
| test_list_members_org_not_found | 组织不存在 → 404 |

## 9. 依赖

`models.organization`、`models.user`、`modules.auth.repository.UserRepository`。
