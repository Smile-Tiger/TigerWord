// 背单词页面（核心页面）。
//
// 布局参考了 iOS 播客播放页的思路：一屏只做一件事。
// 上方一条细进度条，中间一张大卡片放单词，下方三个大按钮。
// 没有边框、没有多余分隔线，靠字重和留白区分层级。
//
// 流程：加载今天的队列 -> 一张一张过 -> 每张自评 -> 答错的本场会再出现一次。
// 键盘快捷键：空格/回车 翻面，1/2/3 分别表示 认识/模糊/不认识。

import { useCallback, useEffect, useState } from 'react'

import { api } from '../api/client'
import type { Entry, Rating, TodayQueue } from '../types'

const TALLY_LABELS: Record<Rating, string> = {
  known: '认识',
  fuzzy: '模糊',
  unknown: '不认识',
}

export default function StudyPage() {
  // 本场要过的卡片。答错的词会被追加到末尾，所以这个列表会变长。
  const [cards, setCards] = useState<Entry[]>([])
  const [index, setIndex] = useState(0)
  const [revealed, setRevealed] = useState(false)
  const [tally, setTally] = useState<Record<Rating, number>>({
    known: 0,
    fuzzy: 0,
    unknown: 0,
  })
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const load = useCallback(async () => {
    setLoading(true)
    setError(null)
    try {
      const queue: TodayQueue = await api.today()
      // 先复习再学新：到期的词拖不得，这是记忆曲线能起作用的关键
      setCards([...queue.review, ...queue.new])
      setIndex(0)
      setRevealed(false)
      setTally({ known: 0, fuzzy: 0, unknown: 0 })
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    void load()
  }, [load])

  const card = cards[index]

  async function rate(rating: Rating) {
    if (!card || busy) return
    setBusy(true)
    try {
      const result = await api.answer(card.id, rating, 'self_report')
      setTally((prev) => ({ ...prev, [rating]: prev[rating] + 1 }))
      if (result.again_today) {
        // 答错的词本场再来一次，插到队尾
        setCards((list) => [...list, card])
      }
      setRevealed(false)
      setIndex((value) => value + 1)
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  // 键盘操作。依赖里带上 revealed 和 busy，保证拿到的是最新值。
  useEffect(() => {
    function onKeyDown(event: KeyboardEvent) {
      if (!cards[index]) return
      if (event.code === 'Space' || event.key === 'Enter') {
        event.preventDefault()
        setRevealed(true)
        return
      }
      if (!revealed) return
      if (event.key === '1') void rate('known')
      if (event.key === '2') void rate('fuzzy')
      if (event.key === '3') void rate('unknown')
    }
    window.addEventListener('keydown', onKeyDown)
    return () => window.removeEventListener('keydown', onKeyDown)
  }, [cards, index, revealed, busy])

  if (loading) {
    return <div className="group"><div className="row"><span className="row-label">正在加载…</span></div></div>
  }

  if (error) {
    return (
      <>
        <div className="group">
          <div className="row">
            <span className="row-label" style={{ color: 'var(--red)' }}>出错了</span>
          </div>
          <div className="row">
            <span className="row-sub">{error}</span>
          </div>
        </div>
        <p className="note">确认后端已经启动（在 backend 目录下运行 uvicorn）。</p>
        <button className="btn btn-primary" onClick={() => void load()}>重试</button>
      </>
    )
  }

  // 全部过完：给一个本场的总结
  if (!card) {
    const total = tally.known + tally.fuzzy + tally.unknown
    return (
      <>
        <div className="group">
          <div className="stat-hero">
            <div className="value">{total}</div>
            <div className="caption">今天过了这么多张卡</div>
          </div>
        </div>

        {total > 0 && (
          <div className="group" style={{ marginTop: 16 }}>
            <div className="row">
              <span className="row-label">认识</span>
              <span className="row-value">{tally.known}</span>
            </div>
            <div className="row">
              <span className="row-label">模糊</span>
              <span className="row-value">{tally.fuzzy}</span>
            </div>
            <div className="row">
              <span className="row-label">不认识</span>
              <span className="row-value">{tally.unknown}</span>
            </div>
          </div>
        )}

        {total === 0 && <p className="note">今天没有到期的词，也没有新词配额。去「导入」页加一些生词吧。</p>}

        <button className="btn btn-primary" onClick={() => void load()}>再学一轮</button>
      </>
    )
  }

  const progress = Math.round((index / cards.length) * 100)
  const isReview = card.stage === 'review'
  const phonetic =
    card.phonetic_uk && card.phonetic_us && card.phonetic_uk !== card.phonetic_us
      ? `英 ${card.phonetic_uk}   美 ${card.phonetic_us}`
      : card.phonetic_uk || card.phonetic_us || ''

  return (
    <>
      <div className="study-progress">
        <div style={{ width: `${progress}%` }} />
      </div>
      <div className="study-meta">
        <span>
          {index + 1} / {cards.length}
        </span>
        <span>{isReview ? '复习' : '新词'}</span>
      </div>

      <div className={isReview ? 'study-card is-review' : 'study-card'}>
        <div className="word">{card.display}</div>
        <div className="phonetic">{phonetic}</div>

        {revealed ? (
          <>
            <div className="study-divider" />
            <div className="definition">{card.definition || '这个词还没有释义'}</div>
          </>
        ) : (
          <div className="hint" style={{ marginTop: 32 }}>想一下它的意思</div>
        )}
      </div>

      {!revealed ? (
        <button className="btn btn-primary" onClick={() => setRevealed(true)}>翻面</button>
      ) : (
        <div className="rating-row">
          <button className="rating-btn known" disabled={busy} onClick={() => void rate('known')}>
            认识
          </button>
          <button className="rating-btn fuzzy" disabled={busy} onClick={() => void rate('fuzzy')}>
            模糊
          </button>
          <button className="rating-btn unknown" disabled={busy} onClick={() => void rate('unknown')}>
            不认识
          </button>
        </div>
      )}

      <p className="note">
        {revealed
          ? '认识往后推，模糊明天再来，不认识本场再考一次。'
          : '按空格翻面 · 1 认识 · 2 模糊 · 3 不认识'}
      </p>
    </>
  )
}
