import type { ChatTurn, Interview } from '../types'

/**
 * Mock 数据层 —— 模拟后端接口。
 * 首版不依赖后端，直接返回内置数据，便于本地运行测试。
 * 后续接入真实后端时，只需将本文件内的实现替换为 axios 调用即可。
 */

/** 模拟网络延迟 */
function sleep(ms = 350): Promise<void> {
  return new Promise((resolve) => setTimeout(resolve, ms))
}

/** 候选人被邀请的面试列表（模拟） */
const INTERVIEWS: Interview[] = [
  {
    id: 'iv-1001',
    position: '高级 Java 后端工程师',
    company: '云启科技有限公司',
    companyInitial: '云',
    companyGradient: 'linear-gradient(135deg, #6366f1, #8b5cf6)',
    questionCount: 6,
    duration: '约 30 分钟',
    status: 'pending',
    expireTime: '2026-09-08 18:00',
  },
  {
    id: 'iv-1002',
    position: '数据产品经理',
    company: '青橙科技有限公司',
    companyInitial: '青',
    companyGradient: 'linear-gradient(135deg, #0ea5e9, #2563eb)',
    questionCount: 5,
    duration: '约 25 分钟',
    status: 'evaluating',
    submittedAt: '2026-09-04 14:22',
  },
  {
    id: 'iv-1003',
    position: '前端开发工程师（React）',
    company: '星野网络',
    companyInitial: '星',
    companyGradient: 'linear-gradient(135deg, #f59e0b, #f97316)',
    questionCount: 6,
    duration: '约 30 分钟',
    status: 'reported',
    submittedAt: '2026-09-02 10:05',
  },
  {
    id: 'iv-1004',
    position: '算法工程师（NLP）',
    company: '深蓝智能',
    companyInitial: '深',
    companyGradient: 'linear-gradient(135deg, #10b981, #059669)',
    questionCount: 7,
    duration: '约 35 分钟',
    status: 'reported',
    submittedAt: '2026-08-28 16:40',
  },
]

/** 获取面试列表 */
export async function fetchInterviews(): Promise<Interview[]> {
  await sleep(300)
  // 返回深拷贝，避免外部修改污染 mock 源数据
  return JSON.parse(JSON.stringify(INTERVIEWS))
}

/** 获取单个面试详情 */
export async function fetchInterview(id: string): Promise<Interview | undefined> {
  await sleep(200)
  const found = INTERVIEWS.find((i) => i.id === id)
  return found ? JSON.parse(JSON.stringify(found)) : undefined
}

/**
 * AI 面试剧本（模拟）。
 * 说明：真实系统中，题目由面试配置（题库模板 / JD 生成）决定；
 * 此处为了可本地跑通，内置一份「高级 Java 后端工程师」的 6 题剧本，
 * 含开场白、2 次追问与收尾。
 */
const SCRIPT: ChatTurn[] = [
  {
    text:
      '你好，我是本次面试的 AI 面试官，很高兴认识你。接下来我会围绕「高级 Java 后端工程师」这个岗位，' +
      '向你提出 6 个问题，预计用时约 30 分钟。你可以用文字作答，也可以使用语音输入。' +
      '回答尽量具体、有例子，我会根据你的回答适当追问。准备好后，我们开始第一题。',
    q: 0,
  },
  {
    text: '请先做一个简短的自我介绍，并重点讲一个你最有代表性的后端项目经历，包括你在其中的角色和具体贡献。',
    q: 1,
  },
  {
    text: '你提到负责了核心模块的设计，能再具体说说这个模块在并发量上来之后，你做过哪些针对性的优化吗？',
    q: 1,
  },
  {
    text: '在你的项目里，是否遇到过性能瓶颈？请描述一次你定位问题、分析原因并最终解决它的完整过程。',
    q: 2,
  },
  {
    text: '请谈谈你对 MySQL 索引和事务隔离级别的理解，并结合你实际做过的项目，说明你是如何应用它们的。',
    q: 3,
  },
  {
    text: '针对你刚才提到的场景，如果出现慢查询，你会优先关注哪些指标？用什么思路去定位和优化？',
    q: 3,
  },
  {
    text: '介绍一下你在项目中使用 Redis 的典型场景，比如缓存、分布式锁等，并说明你是如何保证数据一致性的。',
    q: 4,
  },
  {
    text: '如果线上服务突然出现大量接口超时，你会按照什么思路来排查和定位？请说出你的排查步骤。',
    q: 5,
  },
  {
    text: '最后，关于这个岗位或我们公司，你有什么想了解或需要补充的吗？',
    q: 6,
  },
  {
    text: '好的，感谢你的分享。你的面试已经全部完成，可以点击右上角的「结束面试」按钮提交本次面试，系统将自动评分并生成报告。祝你顺利！',
    q: 6,
  },
]

/** 总题数 */
export const TOTAL_QUESTIONS = 6

/** 获取面试剧本（返回副本） */
export function getInterviewScript(): { turns: ChatTurn[]; total: number } {
  return { turns: JSON.parse(JSON.stringify(SCRIPT)), total: TOTAL_QUESTIONS }
}
