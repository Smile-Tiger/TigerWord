// 统计页面：词库规模、各阶段分布、正确率、最近的导入记录。
// 大数字放最上面（学 iOS 健身/健康那种做法），明细收在分组卡片里。

import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client'
import type { Stats } from '../types'

const STAGE_LABELS: Record<string, string> = {
  new: '还没学',
  learning: '今天在学',
  review: '复习中',
  graduated: '已毕业',
}

export default function StatsPage() {
  const [stats, setStats] = useState<Stats | null>(null)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    try {
      setStats(await api.stats())
    } catch (err) {
      setError((err as Error).message)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  if (error) return <p className="error">读统计失败：{error}</p>
  if (!stats) return <div className="group"><div className="row"><span className="row-label">加载中…</span></div></div>

  const accuracy =
    stats.accuracy === null ? '—' : `${Math.round(stats.accuracy * 100)}%`

  return (
    <>
      <div className="group">
        <div className="stat-hero">
          <div className="value">{stats.entries_total}</div>
          <div className="caption">词库里的词条总数</div>
        </div>
      </div>

      <div className="group-title">学习进度</div>
      <div className="group">
        {Object.entries(stats.by_stage).map(([stage, count]) => (
          <div className="row" key={stage}>
            <span className="row-label">{STAGE_LABELS[stage] ?? stage}</span>
            <span className="row-value">{count}</span>
          </div>
        ))}
      </div>

      <div className="group-title">答题情况</div>
      <div className="group">
        <div className="row">
          <span className="row-label">累计作答</span>
          <span className="row-value">{stats.answers_total} 次</span>
        </div>
        <div className="row">
          <span className="row-label">答对率</span>
          <span className="row-value">{accuracy}</span>
        </div>
      </div>

      <div className="group-title">最近的导入</div>
      {stats.recent_batches.length === 0 ? (
        <p className="note">还没有导入过文件。</p>
      ) : (
        <div className="group">
          {stats.recent_batches.map((batch) => (
            <div className="row" key={String(batch.id)}>
              <span className="row-label">
                <span className="filename">{String(batch.source).split(/[\\/]/).pop()}</span>
                <div className="row-sub">
                  解析 {String(batch.total)} 条 · 新增 {String(batch.added)} 条
                </div>
              </span>
            </div>
          ))}
        </div>
      )}
    </>
  )
}
