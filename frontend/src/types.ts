// 和后端接口一一对应的类型定义。
// 后端改字段时，这里跟着改，TypeScript 会在编译期把用到的地方全指出来。

export type Rating = 'known' | 'fuzzy' | 'unknown'
export type AnswerMode = 'choice' | 'self_report'

export interface Entry {
  id: number
  display: string
  kind: 'word' | 'phrase'
  phonetic_uk: string | null
  phonetic_us: string | null
  definition: string | null
  stage: string | null
  step: number | null
  due_at: string | null
}

export interface TodayQueue {
  new: Entry[]
  review: Entry[]
  daily_new_limit: number
}

export interface AnswerResult {
  stage: string
  step: number
  due_at: string | null
  again_today: boolean
  remaining: number
}

export interface ImportReport {
  batch_id: number
  source: string
  input_kind: string
  declared_count: number | null
  parsed: number
  imported: number
  added: number
  updated: number
  unchanged: number
  needs_review: number
  entries_in_db: number
  enrich?: {
    filled_phonetic: number
    filled_definition: number
    from_llm: number
    failed: number
    notes: string[]
  }
  warnings: string[]
}

export interface LLMSettings {
  provider: string
  base_url: string
  model: string
  api_key_set: boolean
  api_key_hint: string
}

export interface Settings {
  daily_new_limit: number
  enrich_enabled: boolean
  llm: LLMSettings
}

export interface Stats {
  entries_total: number
  by_stage: {
    new: number
    learning: number
    review: number
    graduated: number
  }
  answers_total: number
  accuracy: number | null
  recent_batches: Array<Record<string, unknown>>
}
