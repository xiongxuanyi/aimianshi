/** 面试状态 */
export type InterviewStatus = 'pending' | 'evaluating' | 'reported'

/** 一场被邀请的面试（候选人视角） */
export interface Interview {
  /** 面试唯一标识 */
  id: string
  /** 岗位名称 */
  position: string
  /** 企业名称 */
  company: string
  /** 企业头像首字 */
  companyInitial: string
  /** 企业头像渐变色 */
  companyGradient: string
  /** 题目数量 */
  questionCount: number
  /** 预计时长描述 */
  duration: string
  /** 状态：待参加 / 评分中 / 已出报告 */
  status: InterviewStatus
  /** 邀请有效期（待参加时） */
  expireTime?: string
  /** 提交时间（评分中 / 已出报告时） */
  submittedAt?: string
}

/** AI 面试官的一段台词（用于推进面试进度） */
export interface ChatTurn {
  text: string
  /** 当前已问到的题号（0..总题数），用于进度展示 */
  q: number
}

/** 对话消息 */
export interface ChatMessage {
  role: 'ai' | 'user'
  text: string
  /** 是否正在「打字中」 */
  typing?: boolean
}
