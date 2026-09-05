-- ============================================================================
-- AI 面试官 App —— MySQL 数据库设计脚本 (script.sql)
-- ----------------------------------------------------------------------------
-- 依据文档 : docs/PRD.md（v0.1）
-- 数据库   : MySQL 8.0+（InnoDB / utf8mb4）
-- 说明     : 本脚本覆盖 PRD §9.5 的关键数据实体，映射关系如下：
--            User              -> users                （企业用户 + 候选人，两类账户）
--            Organization      -> organizations        （企业/组织）
--            Membership        -> memberships          （组织-用户，角色 admin/hr）
--            QuestionTemplate  -> question_templates   （内置题库模板）
--            Interview         -> interviews           （面试配置）
--            InterviewSession  -> interview_sessions   （候选人单场面试会话）
--            Message           -> messages             （对话消息）
--            Evaluation        -> evaluations          （AI 评分 = 报告内容）
--            Report            -> evaluations + reviews（报告 = 评分 + HR 人工评审）
--            Invitation        -> invitations          （候选人邀请链接）
-- ----------------------------------------------------------------------------
-- 设计要点：
--   * 可变结构（题目列表、维度权重、维度得分、逐题点评等）用 JSON 类型承载，
--     以支持「维度集 / 阈值 / 题目字段」随岗位不同而变化的业务需求。
--   * 会话消息的 seq 用于排序，UNIQUE(session_id, seq) 保证顺序唯一。
--   * 语音作答的录音文件存对象存储（MinIO/OSS），表内仅存引用 URL。
-- ============================================================================

SET NAMES utf8mb4;
SET FOREIGN_KEY_CHECKS = 0;

-- ----------------------------------------------------------------------------
-- 删除旧表（按依赖逆序）
-- ----------------------------------------------------------------------------
DROP TABLE IF EXISTS reviews;
DROP TABLE IF EXISTS evaluations;
DROP TABLE IF EXISTS messages;
DROP TABLE IF EXISTS interview_sessions;
DROP TABLE IF EXISTS invitations;
DROP TABLE IF EXISTS interviews;
DROP TABLE IF EXISTS memberships;
DROP TABLE IF EXISTS question_templates;
DROP TABLE IF EXISTS organizations;
DROP TABLE IF EXISTS users;

SET FOREIGN_KEY_CHECKS = 1;

-- ----------------------------------------------------------------------------
-- 1. users —— 用户表（企业用户与候选人共用，user_type 区分）
-- ----------------------------------------------------------------------------
CREATE TABLE users (
    id              BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    email           VARCHAR(255)    NOT NULL                COMMENT '登录邮箱（全局唯一）',
    hashed_password VARCHAR(255)    NOT NULL                COMMENT '密码哈希（bcrypt）',
    user_type       ENUM('enterprise','candidate') NOT NULL COMMENT '账户类型：enterprise=企业用户, candidate=候选人',
    name            VARCHAR(100)    NOT NULL                COMMENT '姓名/昵称',
    created_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at      DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_users_email (email),
    KEY idx_users_type (user_type)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='用户表（企业用户与候选人）';

-- ----------------------------------------------------------------------------
-- 2. organizations —— 组织（企业）
-- ----------------------------------------------------------------------------
CREATE TABLE organizations (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    name       VARCHAR(200)    NOT NULL                COMMENT '企业名称',
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组织/企业表';

-- ----------------------------------------------------------------------------
-- 3. memberships —— 组织成员（用户与组织的多对多，含角色）
-- ----------------------------------------------------------------------------
CREATE TABLE memberships (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    org_id     BIGINT UNSIGNED NOT NULL                COMMENT '组织 ID',
    user_id    BIGINT UNSIGNED NOT NULL                COMMENT '用户 ID（企业用户）',
    role       ENUM('admin','hr') NOT NULL             COMMENT '角色：admin=管理员, hr=HR/面试官',
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_memberships_org_user (org_id, user_id),
    KEY idx_memberships_user (user_id),
    CONSTRAINT fk_memberships_org  FOREIGN KEY (org_id)  REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_memberships_user FOREIGN KEY (user_id) REFERENCES users(id)         ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='组织成员表';

-- ----------------------------------------------------------------------------
-- 4. question_templates —— 内置题库模板
--     dimensions / questions 用 JSON 承载可变结构
-- ----------------------------------------------------------------------------
CREATE TABLE question_templates (
    id         BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    title      VARCHAR(200)    NOT NULL                COMMENT '模板标题',
    industry   VARCHAR(100)    NOT NULL                COMMENT '行业',
    position   VARCHAR(200)    NOT NULL                COMMENT '岗位',
    dimensions JSON            NOT NULL                COMMENT '考察维度数组，如 ["专业技能","逻辑思维"]',
    questions  JSON            NOT NULL                COMMENT '题目数组，元素形如 {"question","hint","dimension"}',
    created_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_templates_industry_position (industry, position)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='内置题库模板';

-- ----------------------------------------------------------------------------
-- 5. interviews —— 面试配置
--     questions / dimension_weights / pass_thresholds 用 JSON 承载，
--     question_source 区分「题库模板」或「JD 生成」
-- ----------------------------------------------------------------------------
CREATE TABLE interviews (
    id                BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    org_id            BIGINT UNSIGNED NOT NULL                COMMENT '所属组织 ID',
    title             VARCHAR(200)    NOT NULL                COMMENT '面试名称',
    position          VARCHAR(200)    NOT NULL                COMMENT '岗位名称',
    jd                TEXT            NULL                    COMMENT '岗位 JD（JD 生成题目时的原文）',
    question_source   ENUM('template','jd_generated') NOT NULL COMMENT '题目来源：template=题库模板, jd_generated=JD 生成',
    questions         JSON            NOT NULL                COMMENT '面试题目数组',
    dimension_weights JSON            NOT NULL                COMMENT '维度权重，如 {"专业技能":0.6,"沟通表达":0.4}',
    pass_thresholds   JSON            NOT NULL                COMMENT '通过阈值，如 {"pass":75,"pending":60}',
    status            ENUM('draft','published','closed') NOT NULL DEFAULT 'draft' COMMENT '状态：draft=草稿, published=已发布, closed=已结束',
    created_by        BIGINT UNSIGNED NOT NULL                COMMENT '创建人（企业用户）ID',
    created_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    updated_at        DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP COMMENT '更新时间',
    PRIMARY KEY (id),
    KEY idx_interviews_org (org_id),
    KEY idx_interviews_status (status),
    KEY idx_interviews_creator (created_by),
    CONSTRAINT fk_interviews_org     FOREIGN KEY (org_id)     REFERENCES organizations(id) ON DELETE CASCADE,
    CONSTRAINT fk_interviews_creator FOREIGN KEY (created_by) REFERENCES users(id)         ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试配置表';

-- ----------------------------------------------------------------------------
-- 6. interview_sessions —— 面试会话（候选人参加的一场面试实例）
-- ----------------------------------------------------------------------------
CREATE TABLE interview_sessions (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    interview_id BIGINT UNSIGNED NOT NULL                COMMENT '面试配置 ID',
    candidate_id BIGINT UNSIGNED NOT NULL                COMMENT '候选人用户 ID',
    status       ENUM('in_progress','finished','evaluated') NOT NULL DEFAULT 'in_progress' COMMENT '状态：in_progress=进行中, finished=已完成待评分, evaluated=已出报告',
    started_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '开始时间',
    finished_at  DATETIME        NULL                    COMMENT '完成时间',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_sessions_interview_candidate (interview_id, candidate_id),
    KEY idx_sessions_candidate (candidate_id),
    CONSTRAINT fk_sessions_interview FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    CONSTRAINT fk_sessions_candidate FOREIGN KEY (candidate_id) REFERENCES users(id)      ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='面试会话表';

-- ----------------------------------------------------------------------------
-- 7. messages —— 对话消息
--     role 区分 interviewer / candidate；kind 区分 text / voice；
--     语音消息的录音文件引用存 recording_url
-- ----------------------------------------------------------------------------
CREATE TABLE messages (
    id            BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    session_id    BIGINT UNSIGNED NOT NULL                COMMENT '所属会话 ID',
    role          ENUM('interviewer','candidate') NOT NULL COMMENT '角色：interviewer=AI 面试官, candidate=候选人',
    content       TEXT            NOT NULL                COMMENT '消息文本（语音消息为转写文本）',
    kind          ENUM('text','voice') NOT NULL DEFAULT 'text' COMMENT '类型：text=文字, voice=语音',
    recording_url VARCHAR(500)    NULL                    COMMENT '语音录音文件引用（对象存储 URL，非语音消息为 NULL）',
    seq           INT UNSIGNED    NOT NULL                COMMENT '会话内消息序号（从 1 递增，用于排序）',
    created_at    DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '发送时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_messages_session_seq (session_id, seq),
    CONSTRAINT fk_messages_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='对话消息表';

-- ----------------------------------------------------------------------------
-- 8. evaluations —— AI 评分（即评估报告内容）
--     一个会话最多一条评分（重评则更新）
-- ----------------------------------------------------------------------------
CREATE TABLE evaluations (
    id               BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    session_id       BIGINT UNSIGNED NOT NULL                COMMENT '所属会话 ID',
    total_score      INT UNSIGNED    NOT NULL                COMMENT '总分（0-100）',
    dimension_scores JSON            NOT NULL                COMMENT '各维度得分，如 {"专业技能":85}',
    per_question     JSON            NOT NULL                COMMENT '逐题点评数组，元素形如 {"question","comment"}',
    highlights       TEXT            NOT NULL                COMMENT '亮点',
    weaknesses       TEXT            NOT NULL                COMMENT '不足',
    recommendation   ENUM('pass','pending','reject') NOT NULL COMMENT '建议：pass=建议通过, pending=建议待定, reject=建议淘汰',
    reason           TEXT            NOT NULL                COMMENT '推荐理由',
    created_at       DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评分时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_evaluations_session (session_id),
    CONSTRAINT fk_evaluations_session FOREIGN KEY (session_id) REFERENCES interview_sessions(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='AI 评分/评估报告表';

-- ----------------------------------------------------------------------------
-- 9. reviews —— HR 人工评审（在 AI 报告之上的最终决策）
-- ----------------------------------------------------------------------------
CREATE TABLE reviews (
    id          BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    session_id  BIGINT UNSIGNED NOT NULL                COMMENT '所属会话 ID',
    reviewer_id BIGINT UNSIGNED NOT NULL                COMMENT '评审人（HR/面试官）ID',
    decision    ENUM('pass','reject','pending') NOT NULL COMMENT '决策：pass=通过, reject=淘汰, pending=待定',
    note        TEXT            NULL                    COMMENT '评审备注',
    created_at  DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '评审时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_reviews_session_reviewer (session_id, reviewer_id),
    KEY idx_reviews_reviewer (reviewer_id),
    CONSTRAINT fk_reviews_session  FOREIGN KEY (session_id)  REFERENCES interview_sessions(id) ON DELETE CASCADE,
    CONSTRAINT fk_reviews_reviewer FOREIGN KEY (reviewer_id) REFERENCES users(id)             ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='HR 人工评审表';

-- ----------------------------------------------------------------------------
-- 10. invitations —— 候选人邀请链接
-- ----------------------------------------------------------------------------
CREATE TABLE invitations (
    id           BIGINT UNSIGNED NOT NULL AUTO_INCREMENT COMMENT '主键',
    interview_id BIGINT UNSIGNED NOT NULL                COMMENT '面试配置 ID',
    token        VARCHAR(64)     NOT NULL                COMMENT '邀请 token（带签名，URL 安全）',
    expires_at   DATETIME        NOT NULL                COMMENT '过期时间',
    created_by   BIGINT UNSIGNED NULL                    COMMENT '创建人（HR）ID',
    created_at   DATETIME        NOT NULL DEFAULT CURRENT_TIMESTAMP COMMENT '创建时间',
    PRIMARY KEY (id),
    UNIQUE KEY uk_invitations_token (token),
    KEY idx_invitations_interview (interview_id),
    CONSTRAINT fk_invitations_interview FOREIGN KEY (interview_id) REFERENCES interviews(id) ON DELETE CASCADE,
    CONSTRAINT fk_invitations_creator   FOREIGN KEY (created_by)   REFERENCES users(id)       ON DELETE SET NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='候选人邀请表';

-- ============================================================================
-- 种子数据 —— 内置题库模板（对应 PRD FR-07 内置题库）
-- ============================================================================
INSERT INTO question_templates (title, industry, position, dimensions, questions) VALUES
(
    'Java 后端工程师通用面试',
    '互联网',
    'Java 后端工程师',
    JSON_ARRAY('专业技能', '逻辑思维', '沟通表达'),
    JSON_ARRAY(
        JSON_OBJECT('question', '请介绍一个你最有挑战的项目，以及你在其中的角色与贡献。',
                    'hint', '关注技术难点、方案选型与个人贡献',
                    'dimension', '专业技能'),
        JSON_OBJECT('question', '请解释 Java 中 HashMap 的底层实现原理。',
                    'hint', '考察数据结构与源码理解',
                    'dimension', '专业技能'),
        JSON_OBJECT('question', '如果线上服务出现大量慢查询，你会如何排查定位？',
                    'hint', '考察问题分析与结构化表达',
                    'dimension', '逻辑思维')
    )
),
(
    '通用软技能面试',
    '通用',
    '通用岗位',
    JSON_ARRAY('逻辑思维', '沟通表达', '岗位匹配度'),
    JSON_ARRAY(
        JSON_OBJECT('question', '请描述一次你与团队意见分歧的经历，以及你如何处理。',
                    'hint', '考察沟通与协作能力',
                    'dimension', '沟通表达'),
        JSON_OBJECT('question', '为什么选择应聘我们公司这个岗位？',
                    'hint', '考察求职动机与岗位匹配度',
                    'dimension', '岗位匹配度'),
        JSON_OBJECT('question', '请举例说明你如何拆解一个复杂问题。',
                    'hint', '考察结构化思维',
                    'dimension', '逻辑思维')
    )
);

-- ============================================================================
-- 完成
-- ============================================================================
