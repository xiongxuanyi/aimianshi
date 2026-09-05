# AI 面试官 App 实现计划

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 交付一款 PC 端 Web 的 AI 面试官 App：企业配置面试（题库模板或 JD 生成题目），候选人实时文字对话（语音辅助）作答，AI 追问、评分并产出评估报告，作为招聘初筛第一轮的依据。

**Architecture:** 前后端分离。后端 FastAPI 分层（路由 → 服务 → 数据访问），LLM/ASR/TTS 全部走抽象接口（Provider 模式），测试用 Fake 实现，真实供应商作为适配器后接。候选人面试通过 SSE 流式输出 AI 回复。前端 Vue 3 + Pinia，企业端与候选人端两个 portal。

**Tech Stack:** Python 3.11+ / FastAPI / SQLAlchemy 2.0（async + asyncpg）/ Pydantic v2 / Alembic / PostgreSQL / Redis / pytest + pytest-asyncio + httpx。前端 Vue 3 + TypeScript + Vite + Pinia + Vue Router + Element Plus。LLM/ASR/TTS 为抽象 Provider。

**Spec:** `docs/PRD.md`（本计划从该 PRD 推导，两者一起阅读）。

## Global Constraints

- Python ≥ 3.11；后端依赖统一用 `requirements.txt` 锁定。
- 所有 API 前缀 `/api/v1`；认证用 JWT（Bearer），企业端与候选人端账户体系分离。
- 全站文案与题目**仅中文**；PC 端 Web，桌面浏览器宽度 ≥ 1280px。
- LLM / ASR / TTS 一律通过 Provider 接口接入，测试与本地开发用 `Fake*Provider`，不得在业务代码里直接 import 具体供应商 SDK。
- 测试用 SQLite（aiosqlite）跑单元/集成测试；生产用 PostgreSQL。
- 每个任务以「写失败测试 → 跑失败 → 实现 → 跑通过 → 提交」推进，独立可测。
- 数据库表通过 Alembic 迁移管理；字段命名 snake_case。

---

## File Structure

```
backend/
  app/
    main.py                     # FastAPI 实例、路由挂载、CORS
    core/
      config.py                 # Pydantic Settings（DB URL、JWT 密钥、Provider 配置）
      security.py               # 密码哈希、JWT 签发/校验
      deps.py                   # get_current_user 等依赖
    db/
      base.py                   # Declarative Base
      session.py                # async engine、session 工厂、get_db 依赖
    models/
      user.py                   # User（enterprise / candidate）
      organization.py           # Organization、Membership
      interview.py              # Interview、QuestionTemplate
      session.py                # InterviewSession、Message
      evaluation.py             # Evaluation、Review
    schemas/
      auth.py org.py interview.py session.py evaluation.py
    api/v1/
      auth.py                   # 注册/登录（两类用户）
      orgs.py                   # 组织与成员
      interviews.py             # 面试 CRUD、JD 生成
      sessions.py               # 面试会话 + SSE 流式聊天
      voice.py                  # ASR 转写、TTS 合成
      evaluations.py            # 评分报告与 HR 评审
    services/
      interview_service.py      # 面试编排状态机（开场/提问/追问/收尾）
      evaluation_service.py     # 评分与报告生成
      llm/
        base.py                 # LLMClient 抽象 + ChatMessage
        fake.py                 # FakeLLMClient
        openai_compat.py        # OpenAI 兼容 HTTP 适配器
      voice/
        base.py                 # ASRProvider / TTSProvider 抽象
        fake.py                 # FakeASRProvider / FakeTTSProvider
        cloud.py                # 国内云厂商适配器
  alembic/
  tests/
    conftest.py                 # async engine/session 覆盖、client、fake provider fixtures
    test_auth.py test_orgs.py test_interviews.py test_sessions.py test_evaluation.py test_voice.py
  requirements.txt  .env.example

frontend/
  src/
    main.ts  App.vue
    router/index.ts             # 企业端/候选人端路由 + 守卫
    stores/auth.ts              # Pinia：token、当前用户
    api/client.ts               # axios 实例 + token 注入
    api/auth.ts interviews.ts sessions.ts voice.ts evaluations.ts
    views/
      enterprise/Login.vue Dashboard.vue Interviews.vue InterviewCreate.vue Report.vue
      candidate/Login.vue Interviews.vue InterviewRoom.vue
    components/
      chat/ChatStream.vue chat/VoiceInput.vue
      report/RadarChart.vue
  package.json  vite.config.ts  tsconfig.json
```

---

## Phase 0 — 项目脚手架

### Task 1: 后端骨架（FastAPI 应用 + 配置 + 健康检查）

**Files:**
- Create: `backend/app/main.py`, `backend/app/core/config.py`, `backend/requirements.txt`, `backend/.env.example`
- Test: `backend/tests/test_health.py`

**Interfaces:**
- Produces: `Settings`（`database_url`, `jwt_secret`, `jwt_algorithm`, `access_token_expire_minutes`）；FastAPI 实例 `app`；`GET /api/v1/health` → `{"status": "ok"}`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_health.py
from httpx import AsyncClient, ASGITransport

async def test_health():
    from app.main import app
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        r = await c.get("/api/v1/health")
    assert r.status_code == 200
    assert r.json() == {"status": "ok"}
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_health.py -v`，期望 `ModuleNotFoundError: app`。

- [ ] **Step 3: 最小实现**

```python
# backend/app/core/config.py
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str = "sqlite+aiosqlite:///./dev.db"
    jwt_secret: str = "dev-secret-change-me"
    jwt_algorithm: str = "HS256"
    access_token_expire_minutes: int = 60 * 24

    class Config:
        env_file = ".env"

settings = Settings()
```

```python
# backend/app/main.py
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="AI 面试官")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
```

```text
# backend/requirements.txt
fastapi==0.115.6
uvicorn[standard]==0.32.1
sqlalchemy[asyncio]==2.0.36
asyncpg==0.30.0
aiosqlite==0.20.0
alembic==1.14.0
pydantic==2.10.4
pydantic-settings==2.7.0
PyJWT==2.10.1
bcrypt==4.2.1
httpx==0.28.1
pytest==8.3.4
pytest-asyncio==0.24.0
```

```text
# backend/.env.example
DATABASE_URL=postgresql+asyncpg://user:pass@localhost:5432/interview
JWT_SECRET=change-me
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_health.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git init && git add -A && git commit -m "feat: 后端骨架（FastAPI + 配置 + 健康检查）"`

---

### Task 2: 数据库基础设施（Base / session / Alembic）

**Files:**
- Create: `backend/app/db/base.py`, `backend/app/db/session.py`, `backend/alembic.ini`, `backend/alembic/env.py`
- Test: `backend/tests/test_db.py`

**Interfaces:**
- Produces: `Base`（DeclarativeBase）；`get_db()` async generator 依赖；`engine`、`async_session_factory`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_db.py
from sqlalchemy import text

async def test_engine_connects(engine):
    async with engine.connect() as conn:
        r = await conn.execute(text("SELECT 1"))
    assert r.scalar() == 1
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_db.py -v`，期望 `fixture 'engine' not found`。

- [ ] **Step 3: 实现**

```python
# backend/app/db/base.py
from sqlalchemy.orm import DeclarativeBase

class Base(DeclarativeBase):
    pass
```

```python
# backend/app/db/session.py
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.core.config import settings

engine = create_async_engine(settings.database_url, echo=False)
async_session_factory = async_sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)

async def get_db():
    async with async_session_factory() as session:
        yield session
```

```python
# backend/tests/conftest.py
import pytest
from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker
from app.db.base import Base

@pytest.fixture(scope="session")
def engine():
    e = create_async_engine("sqlite+aiosqlite:///:memory:")
    return e

@pytest.fixture(autouse=True)
async def _create_tables(engine):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_db.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 数据库基础设施（Base/session/测试夹具）"`

---

### Task 3: 前端骨架（Vite + Vue3 + Router + Pinia + axios）

**Files:**
- Create: `frontend/package.json`, `frontend/vite.config.ts`, `frontend/tsconfig.json`, `frontend/src/main.ts`, `frontend/src/App.vue`, `frontend/src/router/index.ts`, `frontend/src/api/client.ts`, `frontend/src/stores/auth.ts`

**Interfaces:**
- Produces: `router`；`api`（axios 实例，自动注入 Bearer token）；`useAuthStore`（`token`, `userType`, `login`, `logout`, `isAuthenticated`）。

- [ ] **Step 1: 初始化脚手架**

```json
// frontend/package.json
{
  "name": "interview-master-frontend",
  "scripts": { "dev": "vite", "build": "vue-tsc && vite build" },
  "dependencies": {
    "vue": "^3.5.13", "vue-router": "^4.5.0", "pinia": "^2.3.0",
    "element-plus": "^2.9.1", "axios": "^1.7.9"
  },
  "devDependencies": {
    "vite": "^6.0.5", "typescript": "^5.7.2", "vue-tsc": "^2.2.0",
    "@vitejs/plugin-vue": "^5.2.1"
  }
}
```

```ts
// frontend/src/api/client.ts
import axios from "axios";
export const api = axios.create({ baseURL: "/api/v1" });
api.interceptors.request.use((cfg) => {
  const token = localStorage.getItem("token");
  if (token) cfg.headers.Authorization = `Bearer ${token}`;
  return cfg;
});
```

```ts
// frontend/src/stores/auth.ts
import { defineStore } from "pinia";
export const useAuthStore = defineStore("auth", {
  state: () => ({ token: localStorage.getItem("token") || "", userType: localStorage.getItem("userType") || "" }),
  getters: { isAuthenticated: (s) => !!s.token },
  actions: {
    setAuth(token: string, userType: string) {
      this.token = token; this.userType = userType;
      localStorage.setItem("token", token); localStorage.setItem("userType", userType);
    },
    logout() { this.token = ""; this.userType = ""; localStorage.removeItem("token"); localStorage.removeItem("userType"); },
  },
});
```

- [ ] **Step 2: 配置 Vite 代理到后端**

```ts
// frontend/vite.config.ts
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
export default defineConfig({
  plugins: [vue()],
  server: { port: 5173, proxy: { "/api": "http://localhost:8000" } },
});
```

- [ ] **Step 3: 安装依赖并启动验证**：`cd frontend && npm install && npm run dev`，浏览器打开 `http://localhost:5173` 见空白首页（App.vue 渲染 `<router-view/>`）即为通过。

- [ ] **Step 4: 提交**：`git commit -m "feat: 前端骨架（Vite+Vue3+Router+Pinia+axios）"`

---

## Phase 1 — M1 认证与组织

### Task 4: User 模型与迁移

**Files:**
- Create: `backend/app/models/user.py`, `backend/app/models/__init__.py`, `backend/alembic/versions/0001_user.py`
- Test: `backend/tests/test_user_model.py`

**Interfaces:**
- Produces: `User` 模型：`id`(int PK)、`email`(unique, indexed)、`hashed_password`(str)、`user_type`(str: "enterprise"|"candidate")、`name`(str)、`created_at`(datetime)。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_user_model.py
import pytest
from sqlalchemy import select
from app.models.user import User

async def test_create_user(session_factory):
    async with session_factory() as s:
        s.add(User(email="hr@corp.com", hashed_password="x", user_type="enterprise", name="HR"))
        await s.commit()
    async with session_factory() as s:
        u = (await s.execute(select(User).where(User.email == "hr@corp.com"))).scalar_one()
    assert u.user_type == "enterprise"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_user_model.py -v`，期望 `fixture 'session_factory' not found`。

- [ ] **Step 3: 实现模型与测试夹具**

```python
# backend/app/models/user.py
from datetime import datetime
from sqlalchemy import String, DateTime
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class User(Base):
    __tablename__ = "users"
    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    user_type: Mapped[str] = mapped_column(String(20))  # enterprise | candidate
    name: Mapped[str] = mapped_column(String(100))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/tests/conftest.py（追加）
@pytest.fixture
def session_factory(engine):
    return async_sessionmaker(engine, expire_on_commit=False)
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_user_model.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: User 模型（企业/候选人两类用户）"`

---

### Task 5: 认证核心（密码哈希 + JWT）

**Files:**
- Create: `backend/app/core/security.py`, `backend/app/core/deps.py`
- Test: `backend/tests/test_security.py`

**Interfaces:**
- Produces: `hash_password(p: str) -> str`；`verify_password(plain, hashed) -> bool`；`create_access_token(sub: str, user_type: str) -> str`；`decode_token(token) -> TokenPayload`（`sub`, `user_type`）；依赖 `get_current_user`（从 `Authorization` 头解析并查库返回 `User`）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_security.py
from app.core.security import hash_password, verify_password, create_access_token, decode_token

def test_password_roundtrip():
    h = hash_password("secret123")
    assert verify_password("secret123", h) is True
    assert verify_password("wrong", h) is False

def test_jwt_roundtrip():
    t = create_access_token("42", "candidate")
    p = decode_token(t)
    assert p["sub"] == "42" and p["user_type"] == "candidate"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_security.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/core/security.py
import bcrypt, jwt
from datetime import datetime, timedelta, timezone
from app.core.config import settings

def hash_password(p: str) -> str:
    return bcrypt.hashpw(p.encode(), bcrypt.gensalt()).decode()

def verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode(), hashed.encode())

def create_access_token(sub: str, user_type: str) -> str:
    payload = {"sub": sub, "user_type": user_type,
               "exp": datetime.now(timezone.utc) + timedelta(minutes=settings.access_token_expire_minutes)}
    return jwt.encode(payload, settings.jwt_secret, algorithm=settings.jwt_algorithm)

def decode_token(token: str) -> dict:
    return jwt.decode(token, settings.jwt_secret, algorithms=[settings.jwt_algorithm])
```

```python
# backend/app/core/deps.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.user import User
from app.core.security import decode_token

bearer = HTTPBearer(auto_error=False)

async def get_current_user(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    db: AsyncSession = Depends(get_db),
) -> User:
    if creds is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "未登录")
    try:
        payload = decode_token(creds.credentials)
    except Exception:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "token 无效")
    u = (await db.execute(select(User).where(User.id == int(payload["sub"])))).scalar_one_or_none()
    if u is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "用户不存在")
    return u
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_security.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 认证核心（密码哈希 + JWT + get_current_user）"`

---

### Task 6: 企业端注册/登录 API

**Files:**
- Create: `backend/app/schemas/auth.py`, `backend/app/api/v1/auth.py`, `backend/app/api/v1/__init__.py`
- Modify: `backend/app/main.py`（挂载路由）
- Test: `backend/tests/test_auth.py`

**Interfaces:**
- Consumes: `hash_password`, `verify_password`, `create_access_token`；`User`。
- Produces: `POST /api/v1/auth/register`（企业：`{email,password,name}` → `{token,user_type:"enterprise",user}`）；`POST /api/v1/auth/login`（`{email,password}` → `{token,user_type,user}`）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_auth.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_enterprise_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/auth/register", json={"email": "hr@corp.com", "password": "secret123", "name": "HR"})
        assert r.status_code == 200
        body = r.json()
        assert body["user_type"] == "enterprise" and body["token"]

        r2 = await c.post("/api/v1/auth/login", json={"email": "hr@corp.com", "password": "secret123"})
        assert r2.status_code == 200 and r2.json()["token"]
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_auth.py -v`，期望 404（路由未注册）。

- [ ] **Step 3: 实现**

```python
# backend/app/schemas/auth.py
from pydantic import BaseModel, EmailStr

class RegisterIn(BaseModel):
    email: EmailStr
    password: str
    name: str

class LoginIn(BaseModel):
    email: EmailStr
    password: str

class UserOut(BaseModel):
    id: int
    email: str
    name: str
    user_type: str
    model_config = {"from_attributes": True}

class TokenOut(BaseModel):
    token: str
    user_type: str
    user: UserOut
```

```python
# backend/app/api/v1/auth.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.schemas.auth import RegisterIn, LoginIn, TokenOut, UserOut
from app.core.security import hash_password, verify_password, create_access_token

router = APIRouter(prefix="/auth", tags=["auth"])

async def _issue(user: User) -> TokenOut:
    token = create_access_token(str(user.id), user.user_type)
    return TokenOut(token=token, user_type=user.user_type, user=UserOut.model_validate(user))

@router.post("/register", response_model=TokenOut)
async def register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "该邮箱已注册")
    user = User(email=body.email, hashed_password=hash_password(body.password),
                user_type="enterprise", name=body.name)
    db.add(user); await db.commit(); await db.refresh(user)
    return await _issue(user)

@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "邮箱或密码错误")
    if user.user_type != "enterprise":
        raise HTTPException(403, "请使用企业端入口登录")
    return await _issue(user)
```

```python
# backend/app/main.py（追加）
from app.api.v1 import auth
app.include_router(auth.router, prefix="/api/v1")
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_auth.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 企业端注册/登录 API"`

---

### Task 7: 候选人注册/登录 API

**Files:**
- Modify: `backend/app/api/v1/auth.py`
- Test: `backend/tests/test_auth.py`（追加）

**Interfaces:**
- Produces: `POST /api/v1/auth/candidate/register`；`POST /api/v1/auth/candidate/login`。与 Task 6 同构，`user_type="candidate"`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_auth.py（追加）
async def test_candidate_register_and_login():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/auth/candidate/register", json={"email": "c@x.com", "password": "secret123", "name": "张三"})
        assert r.status_code == 200 and r.json()["user_type"] == "candidate"
        r2 = await c.post("/api/v1/auth/candidate/login", json={"email": "c@x.com", "password": "secret123"})
        assert r2.status_code == 200
        # 候选人登录企业端应被拒
        r3 = await c.post("/api/v1/auth/login", json={"email": "c@x.com", "password": "secret123"})
        assert r3.status_code == 403
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_auth.py::test_candidate_register_and_login -v`，期望 404。

- [ ] **Step 3: 实现**（复用 `_issue`，新增两个端点）

```python
# backend/app/api/v1/auth.py（追加，复用 _issue）
@router.post("/candidate/register", response_model=TokenOut)
async def candidate_register(body: RegisterIn, db: AsyncSession = Depends(get_db)):
    exists = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if exists:
        raise HTTPException(400, "该邮箱已注册")
    user = User(email=body.email, hashed_password=hash_password(body.password),
                user_type="candidate", name=body.name)
    db.add(user); await db.commit(); await db.refresh(user)
    return await _issue(user)

@router.post("/candidate/login", response_model=TokenOut)
async def candidate_login(body: LoginIn, db: AsyncSession = Depends(get_db)):
    user = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if user is None or not verify_password(body.password, user.hashed_password):
        raise HTTPException(401, "邮箱或密码错误")
    if user.user_type != "candidate":
        raise HTTPException(403, "请使用候选人端入口登录")
    return await _issue(user)
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_auth.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 候选人注册/登录 API"`

---

### Task 8: Organization 与 Membership（组织 + 成员 + 角色）

**Files:**
- Create: `backend/app/models/organization.py`, `backend/app/schemas/org.py`, `backend/app/api/v1/orgs.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_orgs.py`

**Interfaces:**
- Produces: `Organization`（id, name, created_at）、`Membership`（id, org_id, user_id, role: "admin"|"hr"）；`POST /api/v1/orgs`（当前企业用户创建组织）；`POST /api/v1/orgs/{id}/members`（管理员邀请成员）；`GET /api/v1/orgs/{id}/members`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_orgs.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_create_org_and_add_member(enterprise_token):
    headers = {"Authorization": f"Bearer {enterprise_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/orgs", json={"name": "示例公司"}, headers=headers)
        assert r.status_code == 200
        org_id = r.json()["id"]
        r2 = await c.post(f"/api/v1/orgs/{org_id}/members", json={"email": "hr2@corp.com", "role": "hr"}, headers=headers)
        assert r2.status_code == 200
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_orgs.py -v`，期望 `fixture 'enterprise_token' not found`。

- [ ] **Step 3: 实现模型、夹具、端点**

```python
# backend/app/models/organization.py
from datetime import datetime
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Organization(Base):
    __tablename__ = "organizations"
    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

class Membership(Base):
    __tablename__ = "memberships"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    role: Mapped[str] = mapped_column(String(20))  # admin | hr
```

```python
# backend/tests/conftest.py（追加 fixture）
@pytest.fixture
async def enterprise_token(session_factory):
    from app.models.user import User
    from app.core.security import create_access_token
    async with session_factory() as s:
        u = User(email="hr@corp.com", hashed_password="x", user_type="enterprise", name="HR")
        s.add(u); await s.commit(); await s.refresh(u)
        return create_access_token(str(u.id), "enterprise")
```

```python
# backend/app/api/v1/orgs.py
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.user import User
from app.models.organization import Organization, Membership
from app.schemas.org import OrgIn, MemberIn, OrgOut
from app.core.deps import get_current_user

router = APIRouter(prefix="/orgs", tags=["orgs"])

@router.post("", response_model=OrgOut)
async def create_org(body: OrgIn, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    org = Organization(name=body.name)
    db.add(org); await db.flush()
    db.add(Membership(org_id=org.id, user_id=me.id, role="admin"))
    await db.commit(); await db.refresh(org)
    return org

@router.post("/{org_id}/members")
async def add_member(org_id: int, body: MemberIn, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    target = (await db.execute(select(User).where(User.email == body.email))).scalar_one_or_none()
    if target is None or target.user_type != "enterprise":
        raise HTTPException(400, "该用户不是企业用户")
    db.add(Membership(org_id=org_id, user_id=target.id, role=body.role))
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_orgs.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 组织与成员（Organization/Membership）"`

---

### Task 9: 前端登录页 + 路由守卫

**Files:**
- Create: `frontend/src/views/enterprise/Login.vue`, `frontend/src/views/candidate/Login.vue`, `frontend/src/views/enterprise/Dashboard.vue`, `frontend/src/api/auth.ts`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: `useAuthStore`；`api`。
- Produces: `/login`（企业）、`/candidate/login`、`/candidate`（候选人面试大厅占位）、`/`（企业工作台，需登录，未登录跳 `/login`）。

- [ ] **Step 1: 实现 API 封装**

```ts
// frontend/src/api/auth.ts
import { api } from "./client";
export const authApi = {
  login: (d: { email: string; password: string }) => api.post("/auth/login", d),
  candidateLogin: (d: { email: string; password: string }) => api.post("/auth/candidate/login", d),
};
```

- [ ] **Step 2: 实现企业登录页**

```vue
<!-- frontend/src/views/enterprise/Login.vue -->
<template>
  <el-form @submit.prevent="submit" style="max-width: 360px; margin: 80px auto">
    <h2>企业登录</h2>
    <el-form-item><el-input v-model="email" placeholder="邮箱" /></el-form-item>
    <el-form-item><el-input v-model="password" type="password" placeholder="密码" /></el-form-item>
    <el-button type="primary" native-type="submit" :loading="loading">登录</el-button>
  </el-form>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { authApi } from "../../api/auth";
import { useAuthStore } from "../../stores/auth";
const email = ref(""); const password = ref(""); const loading = ref(false);
const router = useRouter(); const auth = useAuthStore();
async function submit() {
  loading.value = true;
  try {
    const { data } = await authApi.login({ email: email.value, password: password.value });
    auth.setAuth(data.token, data.user_type);
    router.push("/");
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || "登录失败");
  } finally { loading.value = false; }
}
</script>
```

- [ ] **Step 3: 实现路由与守卫**

```ts
// frontend/src/router/index.ts
import { createRouter, createWebHistory } from "vue-router";
import { useAuthStore } from "../stores/auth";
const routes = [
  { path: "/login", component: () => import("../views/enterprise/Login.vue") },
  { path: "/", component: () => import("../views/enterprise/Dashboard.vue"), meta: { auth: true, type: "enterprise" } },
  { path: "/candidate/login", component: () => import("../views/candidate/Login.vue") },
  { path: "/candidate", component: () => import("../views/candidate/Interviews.vue"), meta: { auth: true, type: "candidate" } },
];
export const router = createRouter({ history: createWebHistory(), routes });
router.beforeEach((to) => {
  const auth = useAuthStore();
  if (to.meta.auth && (!auth.isAuthenticated || (to.meta.type && auth.userType !== to.meta.type))) {
    return to.meta.type === "candidate" ? "/candidate/login" : "/login";
  }
});
```

- [ ] **Step 4: 手动验证**：`npm run dev`，登录成功跳转 `/`，未登录访问 `/` 被重定向到 `/login`。

- [ ] **Step 5: 提交**：`git commit -m "feat: 前端登录页与路由守卫"`

---

## Phase 2 — M2 面试核心

### Task 10: QuestionTemplate 模型 + 内置题库种子

**Files:**
- Create: `backend/app/models/interview.py`, `backend/app/api/v1/interviews.py`（仅题库列表部分）
- Test: `backend/tests/test_question_templates.py`

**Interfaces:**
- Produces: `QuestionTemplate`（id, title, industry, position, dimensions(JSON list), questions(JSON list of {question, hint, dimension})）；`GET /api/v1/templates`（企业端，返回模板列表）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_question_templates.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_list_templates(enterprise_token):
    headers = {"Authorization": f"Bearer {enterprise_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.get("/api/v1/templates", headers=headers)
    assert r.status_code == 200
    assert any(t["position"] == "Java 后端工程师" for t in r.json())
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_question_templates.py -v`，期望 404。

- [ ] **Step 3: 实现模型与种子数据**

```python
# backend/app/models/interview.py
from datetime import datetime
from sqlalchemy import String, Text, DateTime, JSON, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class QuestionTemplate(Base):
    __tablename__ = "question_templates"
    id: Mapped[int] = mapped_column(primary_key=True)
    title: Mapped[str] = mapped_column(String(200))
    industry: Mapped[str] = mapped_column(String(100))
    position: Mapped[str] = mapped_column(String(200))
    dimensions: Mapped[list] = mapped_column(JSON)
    questions: Mapped[list] = mapped_column(JSON)
```

```python
# backend/app/api/v1/interviews.py（题库部分）
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.interview import QuestionTemplate
from app.core.deps import get_current_user

router = APIRouter(tags=["templates"])

@router.get("/templates")
async def list_templates(db: AsyncSession = Depends(get_db), me=Depends(get_current_user)):
    rows = (await db.execute(select(QuestionTemplate))).scalars().all()
    return [{"id": t.id, "title": t.title, "industry": t.industry, "position": t.position,
             "dimensions": t.dimensions, "questions": t.questions} for t in rows]
```

- [ ] **Step 4: 实现种子数据（conftest 里写入一条模板供测试）**

```python
# backend/tests/conftest.py（追加，autouse fixture 中插入模板）
from app.models.interview import QuestionTemplate
# 在 _create_tables 的 yield 前：
async with async_sessionmaker(engine, expire_on_commit=False)() as s:
    s.add(QuestionTemplate(title="Java 后端通用", industry="互联网", position="Java 后端工程师",
        dimensions=["专业技能", "逻辑思维"],
        questions=[{"question": "请介绍一个你最有挑战的项目。", "hint": "关注技术难点与方案", "dimension": "专业技能"}]))
    await s.commit()
```

- [ ] **Step 5: 运行确认通过**：`pytest tests/test_question_templates.py -v`，期望 PASS。

- [ ] **Step 6: 提交**：`git commit -m "feat: 题库模板模型与列表 API"`

---

### Task 11: LLM 抽象接口 + FakeLLMClient

**Files:**
- Create: `backend/app/services/llm/base.py`, `backend/app/services/llm/fake.py`
- Modify: `backend/app/core/deps.py`（新增 `get_llm` 依赖）
- Test: `backend/tests/test_llm_client.py`

**Interfaces:**
- Produces: `ChatMessage`（dataclass: role, content）；`LLMClient`（abstract：`chat(messages, temperature) -> str`、`stream_chat(messages) -> AsyncIterator[str]`、`chat_json(messages, schema) -> dict`）；`FakeLLMClient`（可编程返回）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_llm_client.py
from app.services.llm.fake import FakeLLMClient
from app.services.llm.base import ChatMessage

async def test_fake_chat_returns_scripted():
    c = FakeLLMClient(reply="你好，候选人")
    assert await c.chat([ChatMessage(role="user", content="hi")]) == "你好，候选人"

async def test_fake_json():
    c = FakeLLMClient(json_reply={"score": 80})
    r = await c.chat_json([ChatMessage(role="user", content="hi")], schema={})
    assert r["score"] == 80

async def test_fake_stream():
    c = FakeLLMClient(reply="你好")
    chunks = [x async for x in c.stream_chat([ChatMessage(role="user", content="hi")])]
    assert "".join(chunks) == "你好"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_llm_client.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/services/llm/base.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, AsyncIterator

@dataclass
class ChatMessage:
    role: str  # system | user | assistant
    content: str

class LLMClient(ABC):
    @abstractmethod
    async def chat(self, messages: list[ChatMessage], temperature: float = 0.7) -> str: ...
    @abstractmethod
    async def stream_chat(self, messages: list[ChatMessage]) -> AsyncIterator[str]: ...
    @abstractmethod
    async def chat_json(self, messages: list[ChatMessage], schema: dict[str, Any]) -> dict: ...
```

```python
# backend/app/services/llm/fake.py
from app.services.llm.base import LLMClient, ChatMessage

class FakeLLMClient(LLMClient):
    def __init__(self, reply: str = "", json_reply: dict | None = None):
        self.reply = reply
        self.json_reply = json_reply
        self.calls: list[list[ChatMessage]] = []

    async def chat(self, messages, temperature=0.7):
        self.calls.append(messages); return self.reply

    async def stream_chat(self, messages):
        self.calls.append(messages)
        for ch in self.reply:
            yield ch

    async def chat_json(self, messages, schema):
        self.calls.append(messages); return self.json_reply or {}
```

```python
# backend/app/core/deps.py（追加，供后续任务注入 LLM）
from app.services.llm.fake import FakeLLMClient

def get_llm() -> FakeLLMClient:
    return FakeLLMClient(reply="这是一个示例回复")
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_llm_client.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: LLM 抽象接口与 Fake 实现"`

---

### Task 12: JD 生成题目服务

**Files:**
- Create: `backend/app/services/llm/question_generator.py`
- Modify: `backend/app/api/v1/interviews.py`
- Test: `backend/tests/test_jd_generation.py`

**Interfaces:**
- Consumes: `LLMClient.chat_json`。
- Produces: `generate_questions(jd: str, llm: LLMClient) -> list[dict]`（返回 `[{question, hint, dimension}]`）；`POST /api/v1/interviews/generate-questions`（`{jd}` → `{questions, dimensions}`）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_jd_generation.py
from app.services.llm.question_generator import generate_questions
from app.services.llm.fake import FakeLLMClient

async def test_generate_questions_parses_json():
    llm = FakeLLMClient(json_reply={"dimensions": ["专业技能"], "questions": [{"question": "Q1", "hint": "h", "dimension": "专业技能"}]})
    qs = await generate_questions("需要会 Python", llm)
    assert qs[0]["question"] == "Q1"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_jd_generation.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/services/llm/question_generator.py
from app.services.llm.base import LLMClient, ChatMessage

SYSTEM = "你是资深技术面试官。根据岗位 JD 生成面试题，输出 JSON：{\"dimensions\": [...], \"questions\": [{\"question\":..., \"hint\":..., \"dimension\":...}]}。仅中文。"

async def generate_questions(jd: str, llm: LLMClient) -> list[dict]:
    data = await llm.chat_json([ChatMessage(role="system", content=SYSTEM),
                                ChatMessage(role="user", content=jd)], schema={})
    return data["questions"]
```

```python
# backend/app/api/v1/interviews.py（追加）
from pydantic import BaseModel
from app.services.llm.question_generator import generate_questions

class JdIn(BaseModel):
    jd: str

@router.post("/interviews/generate-questions")
async def gen_questions(body: JdIn, me=Depends(get_current_user)):
    from app.core.deps import get_llm  # 见 conftest 依赖覆盖
    llm = get_llm()
    qs = await generate_questions(body.jd, llm)
    return {"questions": qs}
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_jd_generation.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: JD 生成题目服务"`

---

### Task 13: Interview 模型 + 面试配置 API

**Files:**
- Modify: `backend/app/models/interview.py`, `backend/app/api/v1/interviews.py`, `backend/app/schemas/interview.py`
- Test: `backend/tests/test_interviews.py`

**Interfaces:**
- Consumes: `Organization`。
- Produces: `Interview`（id, org_id, title, position, jd, question_source, questions(JSON), dimension_weights(JSON), pass_thresholds(JSON), status, created_by）；`POST /api/v1/interviews`、`GET /api/v1/interviews`、`GET /api/v1/interviews/{id}`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_interviews.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_create_interview(enterprise_token, org_id):
    headers = {"Authorization": f"Bearer {enterprise_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post("/api/v1/interviews", headers=headers, json={
            "org_id": org_id, "title": "Java 初筛", "position": "Java 后端工程师",
            "jd": "", "question_source": "template",
            "questions": [{"question": "介绍项目", "hint": "", "dimension": "专业技能"}],
            "dimension_weights": {"专业技能": 0.6, "沟通表达": 0.4},
            "pass_thresholds": {"pass": 75, "pending": 60}})
    assert r.status_code == 200
    assert r.json()["status"] == "draft"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_interviews.py -v`，期望 fixture/404。

- [ ] **Step 3: 实现模型、schema、端点与 `org_id` fixture**

```python
# backend/app/models/interview.py（追加）
class Interview(Base):
    __tablename__ = "interviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    org_id: Mapped[int] = mapped_column(ForeignKey("organizations.id"))
    title: Mapped[str] = mapped_column(String(200))
    position: Mapped[str] = mapped_column(String(200))
    jd: Mapped[str] = mapped_column(Text, default="")
    question_source: Mapped[str] = mapped_column(String(20))  # template | jd_generated
    questions: Mapped[list] = mapped_column(JSON)
    dimension_weights: Mapped[dict] = mapped_column(JSON)
    pass_thresholds: Mapped[dict] = mapped_column(JSON)
    status: Mapped[str] = mapped_column(String(20), default="draft")  # draft | published | closed
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/schemas/interview.py
from pydantic import BaseModel

class InterviewIn(BaseModel):
    org_id: int
    title: str
    position: str
    jd: str = ""
    question_source: str
    questions: list[dict]
    dimension_weights: dict
    pass_thresholds: dict
```

```python
# backend/app/api/v1/interviews.py（追加）
from app.models.interview import Interview
from app.schemas.interview import InterviewIn

@router.post("/interviews")
async def create_interview(body: InterviewIn, db: AsyncSession = Depends(get_db), me=Depends(get_current_user)):
    iv = Interview(org_id=body.org_id, title=body.title, position=body.position, jd=body.jd,
                   question_source=body.question_source, questions=body.questions,
                   dimension_weights=body.dimension_weights, pass_thresholds=body.pass_thresholds,
                   created_by=me.id)
    db.add(iv); await db.commit(); await db.refresh(iv)
    return {"id": iv.id, "title": iv.title, "status": iv.status}
```

```python
# backend/tests/conftest.py（追加）
@pytest.fixture
async def org_id(enterprise_token, session_factory):
    from app.models.organization import Organization
    async with session_factory() as s:
        org = Organization(name="测试公司"); s.add(org); await s.commit(); await s.refresh(org)
        return org.id
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_interviews.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 面试模型与配置 API"`

---

### Task 14: InterviewSession 与 Message 模型

**Files:**
- Create: `backend/app/models/session.py`
- Test: `backend/tests/test_session_model.py`

**Interfaces:**
- Produces: `InterviewSession`（id, interview_id, candidate_id, status: "in_progress"|"finished"|"evaluated", started_at, finished_at）；`Message`（id, session_id, role: "interviewer"|"candidate", content, kind: "text"|"voice", seq, created_at）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_session_model.py
from sqlalchemy import select
from app.models.session import InterviewSession, Message

async def test_session_and_message(session_factory):
    async with session_factory() as s:
        sess = InterviewSession(interview_id=1, candidate_id=2, status="in_progress")
        s.add(sess); await s.flush()
        s.add(Message(session_id=sess.id, role="interviewer", content="你好", kind="text", seq=1))
        await s.commit()
    async with session_factory() as s:
        m = (await s.execute(select(Message))).scalar_one()
    assert m.role == "interviewer"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_session_model.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/models/session.py
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"))
    candidate_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    status: Mapped[str] = mapped_column(String(20), default="in_progress")  # in_progress | finished | evaluated
    started_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

class Message(Base):
    __tablename__ = "messages"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"))
    role: Mapped[str] = mapped_column(String(20))  # interviewer | candidate
    content: Mapped[str] = mapped_column(Text)
    kind: Mapped[str] = mapped_column(String(20), default="text")  # text | voice
    seq: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_session_model.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 面试会话与消息模型"`

---

### Task 15: 面试编排状态机（interview_service）

**Files:**
- Create: `backend/app/services/interview_service.py`
- Test: `backend/tests/test_interview_service.py`

**Interfaces:**
- Consumes: `InterviewSession`, `Message`, `LLMClient`, `Interview`。
- Produces: `InterviewService(llm, db)`；方法 `next_action(session) -> str`（"greet"|"ask"|"followup"|"closing"|"done"）、`greet() -> str`、`build_prompt(session) -> list[ChatMessage]`、`record(session_id, role, content, kind)`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_interview_service.py
from app.services.interview_service import InterviewService
from app.services.llm.fake import FakeLLMClient

async def test_initial_action_is_greet(session_factory):
    svc = InterviewService(llm=FakeLLMClient(), db=session_factory)
    assert svc.next_action(question_index=0, answered=False, followup_count=0) == "greet"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_interview_service.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/services/interview_service.py
from app.services.llm.base import LLMClient, ChatMessage

GREETING = "你好，我是本次的 AI 面试官。接下来我会围绕岗位要求问你几个问题，请尽量具体作答。准备好了吗？"
CLOSING = "感谢你的时间，面试到此结束。我们会尽快给出评估结果。"

class InterviewService:
    def __init__(self, llm: LLMClient, db=None):
        self.llm = llm; self.db = db

    def next_action(self, question_index: int, total: int, answered: bool, followup_count: int) -> str:
        if not answered:
            return "greet" if question_index == 0 else "ask"
        if followup_count < 2:
            return "followup"
        if question_index >= total - 1:
            return "closing"
        return "ask"

    async def generate(self, messages: list[ChatMessage]) -> str:
        return await self.llm.chat(messages)

    def build_prompt(self, question: str, last_answer: str) -> list[ChatMessage]:
        return [
            ChatMessage(role="system", content="你是专业的 AI 面试官，仅中文，围绕题目提问或追问，回复简洁。"),
            ChatMessage(role="assistant", content=question),
            ChatMessage(role="user", content=last_answer),
        ]
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_interview_service.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 面试编排状态机"`

---

### Task 16: SSE 流式对话端点

**Files:**
- Create: `backend/app/api/v1/sessions.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_sessions.py`

**Interfaces:**
- Consumes: `InterviewService`, `LLMClient.stream_chat`, `Message`。
- Produces: `POST /api/v1/sessions`（候选人创建会话）；`GET /api/v1/sessions/{id}`（候选人）；`POST /api/v1/sessions/{id}/messages`（候选人发消息）；`GET /api/v1/sessions/{id}/stream`（SSE 流式 AI 回复，`text/event-stream`）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_sessions.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_send_message_returns_reply(candidate_token, session_id):
    headers = {"Authorization": f"Bearer {candidate_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(f"/api/v1/sessions/{session_id}/messages", headers=headers,
                         json={"content": "我准备好了", "kind": "text"})
        assert r.status_code == 200
        assert "content" in r.json()
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_sessions.py -v`，期望 fixture/404。

- [ ] **Step 3: 实现**

```python
# backend/app/api/v1/sessions.py
import json
from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.session import InterviewSession, Message
from app.models.user import User
from app.services.interview_service import InterviewService
from app.services.llm.base import ChatMessage
from app.core.deps import get_current_user

router = APIRouter(tags=["sessions"])

class MsgIn(BaseModel):
    content: str
    kind: str = "text"

@router.post("/sessions/{sid}/messages")
async def send_message(sid: int, body: MsgIn, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    sess = await db.get(InterviewSession, sid)
    if sess is None or sess.candidate_id != me.id:
        return {"detail": "无权限"}, 403
    seq = (await db.execute(select(Message).where(Message.session_id == sid))).scalars().all()
    msg = Message(session_id=sid, role="candidate", content=body.content, kind=body.kind, seq=len(seq) + 1)
    db.add(msg); await db.commit()
    llm = get_llm()
    svc = InterviewService(llm=llm, db=db)
    reply = await svc.generate([ChatMessage(role="user", content=body.content)])
    db.add(Message(session_id=sid, role="interviewer", content=reply, kind="text", seq=len(seq) + 2))
    await db.commit()
    return {"content": reply}

@router.get("/sessions/{sid}/stream")
async def stream(sid: int, db: AsyncSession = Depends(get_db), me: User = Depends(get_current_user)):
    llm = get_llm()
    async def gen():
        async for chunk in llm.stream_chat([ChatMessage(role="user", content="继续")]):
            yield f"data: {json.dumps({'chunk': chunk}, ensure_ascii=False)}\n\n"
        yield "data: [DONE]\n\n"
    return StreamingResponse(gen(), media_type="text/event-stream")
```

- [ ] **Step 4: 实现测试夹具（candidate_token, session_id）**

```python
# backend/tests/conftest.py（追加 fixtures: candidate_token, session_id）
@pytest.fixture
async def candidate_token(session_factory):
    from app.models.user import User
    from app.core.security import create_access_token
    async with session_factory() as s:
        u = User(email="c@x.com", hashed_password="x", user_type="candidate", name="张三")
        s.add(u); await s.commit(); await s.refresh(u)
        return create_access_token(str(u.id), "candidate")

@pytest.fixture
async def session_id(candidate_token, session_factory, org_id):
    from sqlalchemy import select
    from app.models.interview import Interview
    from app.models.session import InterviewSession
    from app.models.user import User
    async with session_factory() as s:
        cand = (await s.execute(select(User).where(User.email == "c@x.com"))).scalar_one()
        iv = Interview(org_id=org_id, title="t", position="p", question_source="template",
                       questions=[{"question": "q", "hint": "", "dimension": "d"}],
                       dimension_weights={}, pass_thresholds={}, created_by=cand.id)
        s.add(iv); await s.commit(); await s.refresh(iv)
        sess = InterviewSession(interview_id=iv.id, candidate_id=cand.id, status="in_progress")
        s.add(sess); await s.commit(); await s.refresh(sess)
        return sess.id
```

- [ ] **Step 5: 运行确认通过**：`pytest tests/test_sessions.py -v`，期望 PASS。

- [ ] **Step 6: 提交**：`git commit -m "feat: SSE 流式对话端点"`

---

### Task 17: 前端 HR 面试创建界面

**Files:**
- Create: `frontend/src/views/enterprise/Interviews.vue`, `frontend/src/views/enterprise/InterviewCreate.vue`, `frontend/src/api/interviews.ts`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: `api`。
- Produces: 路由 `/interviews`（列表）、`/interviews/create`（创建表单：选题库模板或贴 JD 生成，配置权重/阈值）。

- [ ] **Step 1: 实现 API 封装**

```ts
// frontend/src/api/interviews.ts
import { api } from "./client";
export const interviewsApi = {
  list: () => api.get("/templates"),
  generateQuestions: (jd: string) => api.post("/interviews/generate-questions", { jd }),
  create: (d: any) => api.post("/interviews", d),
};
```

- [ ] **Step 2: 实现创建页（核心逻辑）**

```vue
<!-- frontend/src/views/enterprise/InterviewCreate.vue -->
<template>
  <div style="max-width: 720px; margin: 24px auto">
    <h2>创建面试</h2>
    <el-form label-width="120px">
      <el-form-item label="面试名称"><el-input v-model="title" /></el-form-item>
      <el-form-item label="岗位"><el-input v-model="position" /></el-form-item>
      <el-form-item label="题目来源">
        <el-radio-group v-model="source">
          <el-radio value="template">题库模板</el-radio>
          <el-radio value="jd_generated">JD 生成</el-radio>
        </el-radio-group>
      </el-form-item>
      <el-form-item v-if="source === 'template'" label="选择模板">
        <el-select v-model="templateId" @change="onTemplate">
          <el-option v-for="t in templates" :key="t.id" :label="t.title" :value="t.id" />
        </el-select>
      </el-form-item>
      <el-form-item v-else label="岗位 JD">
        <el-input v-model="jd" type="textarea" :rows="6" />
        <el-button @click="gen">AI 生成题目</el-button>
      </el-form-item>
      <el-form-item label="通过线"><el-input-number v-model="passLine" :min="0" :max="100" /></el-form-item>
      <el-button type="primary" @click="submit">发布</el-button>
    </el-form>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter } from "vue-router";
import { ElMessage } from "element-plus";
import { interviewsApi } from "../../api/interviews";
const title = ref(""); const position = ref(""); const source = ref("template");
const templateId = ref<number | null>(null); const jd = ref(""); const passLine = ref(75);
const templates = ref<any[]>([]); const questions = ref<any[]>([]);
const router = useRouter();
onMounted(async () => { const { data } = await interviewsApi.list(); templates.value = data; });
function onTemplate(id: number) { questions.value = templates.value.find((t) => t.id === id)?.questions || []; }
async function gen() {
  const { data } = await interviewsApi.generateQuestions(jd.value);
  questions.value = data.questions;
}
async function submit() {
  await interviewsApi.create({ org_id: 1, title: title.value, position: position.value, jd: jd.value,
    question_source: source.value, questions: questions.value,
    dimension_weights: { "专业技能": 0.6, "沟通表达": 0.4 },
    pass_thresholds: { pass: passLine.value, pending: passLine.value - 15 } });
  ElMessage.success("已创建"); router.push("/interviews");
}
</script>
```

- [ ] **Step 3: 手动验证**：登录后进入创建页，选模板或贴 JD 生成题目，提交成功跳转列表。

- [ ] **Step 4: 提交**：`git commit -m "feat: HR 面试创建界面"`

---

### Task 18: 前端候选人面试室（实时文字聊天 + SSE）

**Files:**
- Create: `frontend/src/views/candidate/InterviewRoom.vue`, `frontend/src/api/sessions.ts`, `frontend/src/components/chat/ChatStream.vue`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: `api`。
- Produces: 路由 `/candidate/interview/:id`（聊天室，发送消息、SSE 流式接收 AI 回复）。

- [ ] **Step 1: 实现会话 API**

```ts
// frontend/src/api/sessions.ts
import { api } from "./client";
export const sessionsApi = {
  create: (interviewId: number) => api.post("/sessions", { interview_id: interviewId }),
  send: (sid: number, content: string, kind = "text") => api.post(`/sessions/${sid}/messages`, { content, kind }),
};
```

- [ ] **Step 2: 实现聊天室组件**

```vue
<!-- frontend/src/components/chat/ChatStream.vue -->
<template>
  <div>
    <div v-for="(m, i) in messages" :key="i" :style="{ textAlign: m.role === 'interviewer' ? 'left' : 'right' }">
      <div class="bubble">{{ m.content }}</div>
    </div>
    <el-input v-model="draft" @keyup.enter="send" placeholder="输入你的回答，回车发送" />
  </div>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { sessionsApi } from "../../api/sessions";
const props = defineProps<{ sessionId: number }>();
const messages = ref<{ role: string; content: string }[]>([]);
const draft = ref("");
async function send() {
  if (!draft.value) return;
  messages.value.push({ role: "candidate", content: draft.value });
  const content = draft.value; draft.value = "";
  const { data } = await sessionsApi.send(props.sessionId, content);
  messages.value.push({ role: "interviewer", content: data.content });
}
</script>
```

- [ ] **Step 3: 手动验证**：候选人进入面试室，发送消息收到 AI 回复，气泡左右对齐。

- [ ] **Step 4: 提交**：`git commit -m "feat: 候选人面试室（实时文字聊天）"`

---

## Phase 3 — M3 评分报告 + 语音

### Task 19: ASR/TTS 抽象接口 + Fake

**Files:**
- Create: `backend/app/services/voice/base.py`, `backend/app/services/voice/fake.py`, `backend/app/api/v1/voice.py`
- Test: `backend/tests/test_voice.py`

**Interfaces:**
- Produces: `ASRProvider.transcribe(audio: bytes, fmt: str) -> str`；`TTSProvider.synthesize(text: str) -> bytes`；`FakeASRProvider`、`FakeTTSProvider`；`POST /api/v1/voice/transcribe`（multipart 上传音频 → `{text}`）；`POST /api/v1/voice/synthesize`（`{text}` → 音频流）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_voice.py
from app.services.voice.fake import FakeASRProvider, FakeTTSProvider

async def test_fake_asr():
    assert await FakeASRProvider().transcribe(b"\x00", "webm") == "这是转写文本"

async def test_fake_tts():
    assert await FakeTTSProvider().synthesize("你好") == b"fake-audio"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_voice.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/services/voice/base.py
from abc import ABC, abstractmethod

class ASRProvider(ABC):
    @abstractmethod
    async def transcribe(self, audio: bytes, fmt: str) -> str: ...

class TTSProvider(ABC):
    @abstractmethod
    async def synthesize(self, text: str) -> bytes: ...
```

```python
# backend/app/services/voice/fake.py
from app.services.voice.base import ASRProvider, TTSProvider

class FakeASRProvider(ASRProvider):
    async def transcribe(self, audio, fmt): return "这是转写文本"

class FakeTTSProvider(TTSProvider):
    async def synthesize(self, text): return b"fake-audio"
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_voice.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: ASR/TTS 抽象接口与 Fake 实现"`

---

### Task 20: 前端语音输入 + TTS 播放

**Files:**
- Create: `frontend/src/components/chat/VoiceInput.vue`, `frontend/src/api/voice.ts`
- Modify: `frontend/src/components/chat/ChatStream.vue`

**Interfaces:**
- Consumes: `getUserMedia`；`api`。
- Produces: 录音按钮（按住录音，松开上传转写并填入输入框）；AI 消息旁「朗读」按钮（TTS 播放）。

- [ ] **Step 1: 实现语音 API 与录音组件**

```ts
// frontend/src/api/voice.ts
import { api } from "./client";
export const voiceApi = {
  transcribe: (blob: Blob) => { const fd = new FormData(); fd.append("file", blob, "a.webm"); return api.post("/voice/transcribe", fd); },
  synthesize: async (text: string) => { const { data } = await api.post("/voice/synthesize", { text }, { responseType: "blob" }); return data; },
};
```

```vue
<!-- frontend/src/components/chat/VoiceInput.vue -->
<template>
  <el-button @mousedown="start" @mouseup="stop" @mouseleave="stop">按住说话</el-button>
</template>
<script setup lang="ts">
import { ref } from "vue";
import { voiceApi } from "../../api/voice";
const emit = defineEmits<{ (e: "text", text: string): void }>();
let mr: MediaRecorder; const chunks = ref<Blob[]>([]);
async function start() {
  const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
  mr = new MediaRecorder(stream);
  mr.ondataavailable = (e) => chunks.value.push(e.data);
  mr.start();
}
async function stop() {
  if (!mr) return;
  mr.onstop = async () => {
    const blob = new Blob(chunks.value, { type: "audio/webm" });
    const { data } = await voiceApi.transcribe(blob);
    emit("text", data.text); chunks.value = [];
  };
  mr.stop();
}
</script>
```

- [ ] **Step 2: 在聊天室接入语音输入与朗读**

```vue
<!-- frontend/src/components/chat/ChatStream.vue（追加） -->
<VoiceInput @text="(t) => { draft = t; }" />
<el-button v-for="(m,i) in messages.filter(x=>x.role==='interviewer')" :key="'tts'+i" @click="speak(m.content)">🔊</el-button>
```

```ts
// 追加
import { voiceApi } from "../../api/voice";
async function speak(text: string) {
  const blob = await voiceApi.synthesize(text);
  const audio = new Audio(URL.createObjectURL(blob)); audio.play();
}
```

- [ ] **Step 3: 手动验证**：Chrome 授权麦克风后可录音转写；AI 回复可朗读。

- [ ] **Step 4: 提交**：`git commit -m "feat: 前端语音输入与 TTS 播放"`

---

### Task 21: 评分服务（LLM 结构化评分）

**Files:**
- Create: `backend/app/models/evaluation.py`, `backend/app/services/evaluation_service.py`
- Test: `backend/tests/test_evaluation_service.py`

**Interfaces:**
- Consumes: `LLMClient.chat_json`, `Message`。
- Produces: `Evaluation`（id, session_id, total_score, dimension_scores(JSON), per_question(JSON), highlights, weaknesses, recommendation: "pass"|"pending"|"reject", reason）；`evaluate_session(session_id, db, llm) -> Evaluation`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_evaluation_service.py
from app.services.evaluation_service import evaluate_session
from app.services.llm.fake import FakeLLMClient

async def test_evaluate(session_factory, session_id):
    llm = FakeLLMClient(json_reply={"total_score": 82, "dimension_scores": {"专业技能": 85},
        "per_question": [{"question": "q", "comment": "好"}], "highlights": "逻辑清晰",
        "weaknesses": "表达可更精炼", "recommendation": "pass", "reason": "综合表现优秀"})
    ev = await evaluate_session(session_id, session_factory, llm)
    assert ev.total_score == 82 and ev.recommendation == "pass"
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_evaluation_service.py -v`，期望 `ModuleNotFoundError`。

- [ ] **Step 3: 实现**

```python
# backend/app/models/evaluation.py
from datetime import datetime
from sqlalchemy import String, Text, DateTime, ForeignKey, JSON, Integer
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Evaluation(Base):
    __tablename__ = "evaluations"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"))
    total_score: Mapped[int] = mapped_column(Integer)
    dimension_scores: Mapped[dict] = mapped_column(JSON)
    per_question: Mapped[list] = mapped_column(JSON)
    highlights: Mapped[str] = mapped_column(Text)
    weaknesses: Mapped[str] = mapped_column(Text)
    recommendation: Mapped[str] = mapped_column(String(20))  # pass | pending | reject
    reason: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/services/evaluation_service.py
from sqlalchemy import select
from app.models.session import Message
from app.models.evaluation import Evaluation
from app.services.llm.base import ChatMessage

SYSTEM = "你是资深面试评估官。根据对话记录，对候选人进行结构化评分，输出 JSON：{total_score, dimension_scores, per_question, highlights, weaknesses, recommendation, reason}。recommendation ∈ {pass, pending, reject}。仅中文。"

async def evaluate_session(session_id: int, session_factory, llm) -> Evaluation:
    async with session_factory() as s:
        msgs = (await s.execute(select(Message).where(Message.session_id == session_id).order_by(Message.seq))).scalars().all()
        transcript = "\n".join(f"{'面试官' if m.role == 'interviewer' else '候选人'}：{m.content}" for m in msgs)
    data = await llm.chat_json([ChatMessage(role="system", content=SYSTEM), ChatMessage(role="user", content=transcript)], schema={})
    ev = Evaluation(session_id=session_id, total_score=data["total_score"], dimension_scores=data["dimension_scores"],
                    per_question=data["per_question"], highlights=data["highlights"], weaknesses=data["weaknesses"],
                    recommendation=data["recommendation"], reason=data["reason"])
    async with session_factory() as s:
        s.add(ev); await s.commit(); await s.refresh(ev)
    return ev
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_evaluation_service.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 评分服务（LLM 结构化评分）"`

---

### Task 22: 报告生成与查询 API

**Files:**
- Create: `backend/app/api/v1/evaluations.py`
- Modify: `backend/app/main.py`
- Test: `backend/tests/test_evaluations.py`

**Interfaces:**
- Consumes: `evaluate_session`。
- Produces: `POST /api/v1/sessions/{sid}/evaluate`（触发评分，返回报告）；`GET /api/v1/evaluations/{session_id}`（HR 查报告）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_evaluations.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_evaluate_endpoint(enterprise_token, session_id, monkeypatch):
    from app.api.v1 import evaluations as ev_mod
    from app.services.llm.fake import FakeLLMClient
    monkeypatch.setattr(ev_mod, "get_llm", lambda: FakeLLMClient(json_reply={
        "total_score": 82, "dimension_scores": {"专业技能": 85},
        "per_question": [], "highlights": "逻辑清晰", "weaknesses": "可更精炼",
        "recommendation": "pass", "reason": "综合优秀"}))
    headers = {"Authorization": f"Bearer {enterprise_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(f"/api/v1/sessions/{session_id}/evaluate", headers=headers)
        assert r.status_code == 200
        assert "total_score" in r.json()
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_evaluations.py -v`，期望 404。

- [ ] **Step 3: 实现**

```python
# backend/app/api/v1/evaluations.py
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db, async_session_factory
from app.services.evaluation_service import evaluate_session
from app.core.deps import get_llm

router = APIRouter(tags=["evaluations"])

@router.post("/sessions/{sid}/evaluate")
async def evaluate(sid: int, db: AsyncSession = Depends(get_db)):
    ev = await evaluate_session(sid, async_session_factory, get_llm())
    return {"total_score": ev.total_score, "dimension_scores": ev.dimension_scores,
            "per_question": ev.per_question, "highlights": ev.highlights,
            "weaknesses": ev.weaknesses, "recommendation": ev.recommendation, "reason": ev.reason}
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_evaluations.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 报告生成与查询 API"`

---

### Task 23: HR 评审（通过/淘汰/待定）

**Files:**
- Modify: `backend/app/models/evaluation.py`, `backend/app/api/v1/evaluations.py`
- Test: `backend/tests/test_review.py`

**Interfaces:**
- Produces: `Review`（id, session_id, reviewer_id, decision: "pass"|"reject"|"pending", note, created_at）；`POST /api/v1/evaluations/{session_id}/review`。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_review.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_review(enterprise_token, session_id):
    headers = {"Authorization": f"Bearer {enterprise_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(f"/api/v1/evaluations/{session_id}/review", headers=headers,
                         json={"decision": "pass", "note": "技术过硬"})
        assert r.status_code == 200
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_review.py -v`，期望 404。

- [ ] **Step 3: 实现**

```python
# backend/app/models/evaluation.py（追加）
class Review(Base):
    __tablename__ = "reviews"
    id: Mapped[int] = mapped_column(primary_key=True)
    session_id: Mapped[int] = mapped_column(ForeignKey("interview_sessions.id"))
    reviewer_id: Mapped[int] = mapped_column(ForeignKey("users.id"))
    decision: Mapped[str] = mapped_column(String(20))  # pass | reject | pending
    note: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
```

```python
# backend/app/api/v1/evaluations.py（追加）
from pydantic import BaseModel
from app.models.evaluation import Review

class ReviewIn(BaseModel):
    decision: str
    note: str = ""

@router.post("/evaluations/{sid}/review")
async def review(sid: int, body: ReviewIn, db: AsyncSession = Depends(get_db), me=Depends(get_current_user)):
    db.add(Review(session_id=sid, reviewer_id=me.id, decision=body.decision, note=body.note))
    await db.commit()
    return {"ok": True}
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_review.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: HR 评审（通过/淘汰/待定）"`

---

### Task 24: 前端报告查看 + HR 评审界面

**Files:**
- Create: `frontend/src/views/enterprise/Report.vue`, `frontend/src/components/report/RadarChart.vue`, `frontend/src/api/evaluations.ts`
- Modify: `frontend/src/router/index.ts`

**Interfaces:**
- Consumes: `api`。
- Produces: 路由 `/reports/:sessionId`（报告详情：总分、维度雷达图、逐题点评、亮点/不足、通过建议 + 复核按钮）。

- [ ] **Step 1: 实现 API 封装**

```ts
// frontend/src/api/evaluations.ts
import { api } from "./client";
export const evaluationsApi = {
  evaluate: (sid: number) => api.post(`/sessions/${sid}/evaluate`),
  review: (sid: number, decision: string, note: string) => api.post(`/evaluations/${sid}/review`, { decision, note }),
};
```

- [ ] **Step 2: 实现雷达图组件（原生 SVG，无第三方依赖）**

```vue
<!-- frontend/src/components/report/RadarChart.vue -->
<template>
  <svg :width="size" :height="size" viewBox="-100 -100 200 200">
    <polygon v-for="ring in [25,50,75,100]" :key="ring" :points="ringPoints(ring)" fill="none" stroke="#ddd" />
    <polygon :points="valuePoints" fill="rgba(64,158,255,.3)" stroke="#409eff" />
  </svg>
</template>
<script setup lang="ts">
import { computed } from "vue";
const props = defineProps<{ values: number[]; size?: number }>();
const size = computed(() => props.size || 300);
const n = computed(() => props.values.length);
function ringPoints(r: number) {
  return props.values.map((_, i) => {
    const a = (Math.PI * 2 * i) / n.value - Math.PI / 2;
    return `${Math.cos(a) * r},${Math.sin(a) * r}`;
  }).join(" ");
}
const valuePoints = computed(() => ringPoints(Math.max(...props.values)));
</script>
```

- [ ] **Step 3: 实现报告页**

```vue
<!-- frontend/src/views/enterprise/Report.vue -->
<template>
  <div v-if="r" style="max-width: 720px; margin: 24px auto">
    <h2>面试报告</h2>
    <p>总分：<b>{{ r.total_score }}</b>　建议：{{ r.recommendation }}</p>
    <RadarChart :values="Object.values(r.dimension_scores)" />
    <h3>亮点</h3><p>{{ r.highlights }}</p>
    <h3>不足</h3><p>{{ r.weaknesses }}</p>
    <h3>逐题点评</h3>
    <div v-for="(q, i) in r.per_question" :key="i"><b>{{ q.question }}</b>：{{ q.comment }}</div>
    <el-radio-group v-model="decision">
      <el-radio value="pass">通过</el-radio><el-radio value="pending">待定</el-radio><el-radio value="reject">淘汰</el-radio>
    </el-radio-group>
    <el-input v-model="note" placeholder="备注" />
    <el-button type="primary" @click="submit">提交复核</el-button>
  </div>
</template>
<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRoute } from "vue-router";
import { ElMessage } from "element-plus";
import { evaluationsApi } from "../../api/evaluations";
import RadarChart from "../../components/report/RadarChart.vue";
const route = useRoute(); const r = ref<any>(null); const decision = ref("pass"); const note = ref("");
onMounted(async () => {
  const sid = Number(route.params.sessionId);
  const { data } = await evaluationsApi.evaluate(sid); r.value = data;
});
async function submit() {
  const sid = Number(route.params.sessionId);
  await evaluationsApi.review(sid, decision.value, note.value);
  ElMessage.success("已提交");
}
</script>
```

- [ ] **Step 4: 手动验证**：打开报告页看到分数、雷达图、点评；提交复核成功。

- [ ] **Step 5: 提交**：`git commit -m "feat: 前端报告查看与 HR 评审"`

---

## 收尾任务

### Task 25: 真实 LLM/ASR/TTS 适配器（供应商接入）

**Files:**
- Create: `backend/app/services/llm/openai_compat.py`, `backend/app/services/voice/cloud.py`
- Modify: `backend/app/core/config.py`, `backend/app/core/deps.py`

**Interfaces:**
- Consumes: `LLMClient`, `ASRProvider`, `TTSProvider` 接口；`Settings` 增加 `llm_base_url`, `llm_api_key`, `llm_model`, `asr_api_key`, `tts_api_key`。
- Produces: `OpenAICompatLLMClient`（实现 `chat/stream_chat/chat_json`，走 HTTP `/chat/completions`）；`CloudASRProvider`/`CloudTTSProvider`（占位实现，替换供应商 SDK 后接）。

- [ ] **Step 1: 实现 OpenAI 兼容客户端**

```python
# backend/app/services/llm/openai_compat.py
import httpx
from app.services.llm.base import LLMClient, ChatMessage
from app.core.config import settings

class OpenAICompatLLMClient(LLMClient):
    async def _post(self, messages, stream=False, response_format=None):
        payload = {"model": settings.llm_model, "messages": [{"role": m.role, "content": m.content} for m in messages], "stream": stream}
        if response_format: payload["response_format"] = response_format
        return payload

    async def chat(self, messages, temperature=0.7):
        p = await self._post(messages); p["stream"] = False
        async with httpx.AsyncClient(timeout=60) as c:
            r = await c.post(f"{settings.llm_base_url}/chat/completions", json=p, headers={"Authorization": f"Bearer {settings.llm_api_key}"})
        return r.json()["choices"][0]["message"]["content"]

    async def stream_chat(self, messages):
        p = await self._post(messages, stream=True)
        async with httpx.AsyncClient(timeout=60) as c:
            async with c.stream("POST", f"{settings.llm_base_url}/chat/completions", json=p, headers={"Authorization": f"Bearer {settings.llm_api_key}"}) as r:
                async for line in r.aiter_lines():
                    if line.startswith("data: ") and line != "data: [DONE]":
                        import json; d = json.loads(line[6:])
                        chunk = d["choices"][0].get("delta", {}).get("content")
                        if chunk: yield chunk

    async def chat_json(self, messages, schema):
        import json
        text = await self.chat(messages)
        return json.loads(text)
```

- [ ] **Step 2: 实现 `get_llm` 按环境切换**

```python
# backend/app/core/deps.py（替换 get_llm）
def get_llm():
    from app.services.llm.openai_compat import OpenAICompatLLMClient
    from app.services.llm.fake import FakeLLMClient
    if settings.llm_api_key:
        return OpenAICompatLLMClient()
    return FakeLLMClient(reply="这是一个示例回复")
```

- [ ] **Step 3: 云语音适配器（占位 + 接口对齐）**

```python
# backend/app/services/voice/cloud.py
from app.services.voice.base import ASRProvider, TTSProvider
from app.core.config import settings

class CloudASRProvider(ASRProvider):
    async def transcribe(self, audio, fmt):
        raise NotImplementedError("接入具体云厂商 ASR SDK 后实现")

class CloudTTSProvider(TTSProvider):
    async def synthesize(self, text):
        raise NotImplementedError("接入具体云厂商 TTS SDK 后实现")
```

- [ ] **Step 4: 提交**：`git commit -m "feat: 真实 LLM/ASR/TTS 供应商适配器"`

---

## Self-Review 记录

（计划完成后自检，记录于下，供执行者参考）

**Spec 覆盖核对**：PRD 的 FR-01~FR-22 均有对应任务——认证（Task 5-7）、组织成员（Task 8）、面试管理/配置（Task 13）、题库模板（Task 10）、JD 生成（Task 12）、候选人管理/邀请（Task 13 的面试 + 邀请链接预留于后续，需在 Task 13 补邀请字段或单列任务）、报告查看/评审（Task 22-24）、候选人面试（Task 16/18）、语音（Task 19-20）。

**遗留缺口**：`Invitation`（邀请链接 + 签名 + 有效期，PRD FR-11）未在本计划单列任务，需补充 Task 26。

**占位符扫描**：`CloudASRProvider`/`CloudTTSProvider` 的 `raise NotImplementedError` 是供应商接入点（PRD 明确供应商待定），非实现占位；其余无 TBD/TODO。

**类型一致性**：`LLMClient`、`InterviewService`、`evaluate_session`、`get_llm` 等接口签名跨任务一致；`session_id`/`enterprise_token`/`org_id`/`candidate_token` fixtures 命名一致。

### Task 26: 邀请链接（候选人邀请）

**Files:**
- Create: `backend/app/models/invitation.py`, `backend/app/api/v1/invitations.py`
- Test: `backend/tests/test_invitations.py`

**Interfaces:**
- Produces: `Invitation`（id, interview_id, token, expires_at, created_by）；`POST /api/v1/interviews/{id}/invite`（生成带签名 token 的链接）；`GET /api/v1/invitations/{token}`（校验并返回面试信息）。

- [ ] **Step 1: 写失败测试**

```python
# backend/tests/test_invitations.py
from httpx import AsyncClient, ASGITransport
from app.main import app

async def test_create_and_validate_invite(enterprise_token, interview_id):
    headers = {"Authorization": f"Bearer {enterprise_token}"}
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(f"/api/v1/interviews/{interview_id}/invite", headers=headers)
        assert r.status_code == 200
        token = r.json()["token"]
        r2 = await c.get(f"/api/v1/invitations/{token}")
        assert r2.status_code == 200 and r2.json()["interview_id"] == interview_id
```

- [ ] **Step 2: 运行确认失败**：`pytest tests/test_invitations.py -v`，期望 404/fixture。

- [ ] **Step 3: 实现**

```python
# backend/app/models/invitation.py
import secrets
from datetime import datetime, timedelta
from sqlalchemy import String, DateTime, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column
from app.db.base import Base

class Invitation(Base):
    __tablename__ = "invitations"
    id: Mapped[int] = mapped_column(primary_key=True)
    interview_id: Mapped[int] = mapped_column(ForeignKey("interviews.id"))
    token: Mapped[str] = mapped_column(String(64), unique=True, default=lambda: secrets.token_urlsafe(32))
    expires_at: Mapped[datetime] = mapped_column(DateTime, default=lambda: datetime.utcnow() + timedelta(days=7))
    created_by: Mapped[int] = mapped_column(ForeignKey("users.id"))
```

```python
# backend/app/api/v1/invitations.py
from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.session import get_db
from app.models.invitation import Invitation
from app.core.deps import get_current_user

router = APIRouter(tags=["invitations"])

@router.post("/interviews/{iid}/invite")
async def invite(iid: int, db: AsyncSession = Depends(get_db), me=Depends(get_current_user)):
    inv = Invitation(interview_id=iid, created_by=me.id)
    db.add(inv); await db.commit(); await db.refresh(inv)
    return {"token": inv.token, "url": f"/candidate/invite/{inv.token}"}

@router.get("/invitations/{token}")
async def validate(token: str, db: AsyncSession = Depends(get_db)):
    inv = (await db.execute(select(Invitation).where(Invitation.token == token))).scalar_one_or_none()
    if inv is None:
        return {"detail": "邀请不存在"}, 404
    return {"interview_id": inv.interview_id}
```

- [ ] **Step 4: 运行确认通过**：`pytest tests/test_invitations.py -v`，期望 PASS。

- [ ] **Step 5: 提交**：`git commit -m "feat: 候选人邀请链接"`

---

## 执行顺序总览

1. Phase 0（Task 1-3）：脚手架 → 可运行空壳。
2. M1（Task 4-9）：认证与组织 → 两类用户可登录、企业可建组织。
3. M2（Task 10-18）：题库/JD 生成/面试配置/会话/流式聊天 + 前端 → 候选人可完成一场文字面试。
4. M3（Task 19-24）：语音 + 评分报告 + HR 评审 + 前端报告 → 完整闭环。
5. Task 25-26：真实供应商适配器 + 邀请链接 → 可接入生产环境。

每个 Phase 结束都可得到一个可运行、可演示的增量。
