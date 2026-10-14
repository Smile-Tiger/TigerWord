// 设置页面：用户在这里填自己的 API Key 和模型。
//
// 后端的规则是"用户填的优先，没填就用 .env 里的默认值"，
// 所以这里留空也不会出错，只是会用开发者配置的那份。
// Key 保存后接口只返回打码形式，页面上不回填明文。

import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client'
import type { Settings } from '../types'

export default function SettingsPage() {
  const [settings, setSettings] = useState<Settings | null>(null)
  const [dailyLimit, setDailyLimit] = useState(20)
  const [enrichEnabled, setEnrichEnabled] = useState(true)
  const [model, setModel] = useState('')
  const [baseUrl, setBaseUrl] = useState('')
  const [apiKey, setApiKey] = useState('')
  const [message, setMessage] = useState<string | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async () => {
    try {
      const data = await api.settings()
      setSettings(data)
      setDailyLimit(data.daily_new_limit)
      setEnrichEnabled(data.enrich_enabled)
      setModel(data.llm.model)
      setBaseUrl(data.llm.base_url)
      setApiKey('') // Key 不回填明文，留空表示"不改"
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  async function save() {
    setBusy(true)
    setError(null)
    setMessage(null)
    try {
      const payload: Record<string, string | number | boolean> = {
        daily_new_limit: dailyLimit,
        enrich_enabled: enrichEnabled,
        llm_model: model,
        llm_base_url: baseUrl,
      }
      // 只有真的填了新 Key 才提交，避免把已经存好的 Key 覆盖成空
      if (apiKey.trim()) payload.llm_api_key = apiKey.trim()

      const data = await api.updateSettings(payload)
      setSettings(data)
      setApiKey('')
      setMessage('已保存')
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  if (!settings) {
    return <div className="group"><div className="row"><span className="row-label">加载中…</span></div></div>
  }

  return (
    <>
      <div className="group-title">学习节奏</div>
      <div className="group">
        <label className="field">
          <div className="field-label">每日新词量</div>
          <input
            type="number"
            min={0}
            max={500}
            value={dailyLimit}
            onChange={(event) => setDailyLimit(Number(event.target.value))}
          />
        </label>
        <label className="switch-row">
          <span>导入时用 AI 补全缺失的音标和释义</span>
          <input
            type="checkbox"
            checked={enrichEnabled}
            onChange={(event) => setEnrichEnabled(event.target.checked)}
          />
        </label>
      </div>

      <div className="group-title">AI 补全（填你自己的 Key）</div>
      <div className="group">
        <label className="field">
          <div className="field-label">模型名</div>
          <input
            type="text"
            value={model}
            placeholder="deepseek-chat"
            onChange={(event) => setModel(event.target.value)}
          />
        </label>
        <label className="field">
          <div className="field-label">接口地址</div>
          <input
            type="text"
            value={baseUrl}
            placeholder="https://api.deepseek.com"
            onChange={(event) => setBaseUrl(event.target.value)}
          />
        </label>
        <label className="field">
          <div className="field-label">API Key</div>
          <input
            type="password"
            value={apiKey}
            placeholder={
              settings.llm.api_key_set
                ? `已配置（${settings.llm.api_key_hint}），留空表示不修改`
                : '还没配置'
            }
            onChange={(event) => setApiKey(event.target.value)}
          />
        </label>
      </div>

      <p className="note">
        Key 存在你自己电脑的本地数据库里，接口返回时只给打码形式。
        不填也能用，只是空缺的音标和释义会一直空着。
      </p>

      <button className="btn btn-primary" disabled={busy} onClick={() => void save()}>
        {busy ? '保存中…' : '保存'}
      </button>

      {message && <p className="ok">{message}</p>}
      {error && <p className="error">保存失败：{error}</p>}
    </>
  )
}
