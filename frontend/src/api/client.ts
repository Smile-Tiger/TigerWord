// 所有接口调用都收在这个文件里。
// 好处：以后要加统一的错误处理、加请求头、换地址，都只改这一处。

import type {
  AnswerMode,
  AnswerResult,
  ImportReport,
  Rating,
  Settings,
  Stats,
  TodayQueue,
} from '../types'

/** 后端返回的错误信息统一在这里转成可读的中文提示 */
async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(path, {
    headers: init?.body instanceof FormData ? undefined : { 'Content-Type': 'application/json' },
    ...init,
  })

  if (!response.ok) {
    // 后端的报错放在 detail 字段里（FastAPI 的约定）
    let detail = `${response.status} ${response.statusText}`
    try {
      const body = await response.json()
      if (body?.detail) detail = typeof body.detail === 'string' ? body.detail : JSON.stringify(body.detail)
    } catch {
      // 解析失败就用状态码兜底，不额外抛错
    }
    throw new Error(detail)
  }

  return (await response.json()) as T
}

export const api = {
  /** 今天该背什么 */
  today: () => request<TodayQueue>('/api/study/today'),

  /** 提交一次作答 */
  answer: (entryId: number, rating: Rating, mode: AnswerMode) =>
    request<AnswerResult>('/api/study/answer', {
      method: 'POST',
      body: JSON.stringify({ entry_id: entryId, rating, mode }),
    }),

  /** 上传生词文件 */
  upload: (file: File) => {
    const form = new FormData()
    form.append('file', file)
    return request<ImportReport>('/api/imports', { method: 'POST', body: form })
  },

  /** 统计 */
  stats: () => request<Stats>('/api/stats'),

  /** 读设置（Key 是打码的） */
  settings: () => request<Settings>('/api/settings'),

  /** 改设置 */
  updateSettings: (payload: Partial<{
    daily_new_limit: number
    enrich_enabled: boolean
    llm_provider: string
    llm_base_url: string
    llm_model: string
    llm_api_key: string
  }>) =>
    request<Settings>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(payload),
    }),
}
