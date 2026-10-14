// 首页：应用打开后看到的第一屏。
//
// 两种状态做两件事：
//   未登录 -> 回答"这是什么、我该点哪"：品牌区 + 登录按钮
//   已登录 -> 回答"我今天要干什么"：激励信息 + 今日任务 + 开始背单词
//
// 动效三件事（都是 CSS 做的，见 styles.css）：
//   1. 背景光斑缓慢漂移 —— 让静止的页面有"活着"的感觉
//   2. 元素依次上浮淡入 —— 有节奏地出现，不是一起蹦出来
//   3. 主按钮极轻微呼吸 —— 把视线吸过去，但不抢戏

import { useEffect, useState } from 'react'

import { api } from '../api/client'
import type { User } from '../auth'
import type { TodayQueue } from '../types'

interface Props {
  user: User | null
  onLogin: () => void
  onLogout: () => void
  onStart: () => void
}

/** TigerWord 的图标：虎脸。
 *
 * 品牌读法是「虎脸 = Tiger，文字 = Word」，合起来才是 TigerWord。
 * 所以这里只画脸，名字交给旁边的标题去说 —— 硬把虎塞进字母里
 * 会做出一个像城墙垛口的图形（试过，不行）。
 */
function LogoMark({ size }: { size: number }) {
  return (
    <svg viewBox="0 0 180 180" width={size} height={size} className="logo-mark">
      <rect width="180" height="180" rx="44" fill="#007AFF" />
      {/* 耳朵，以及耳朵里的深色 */}
      <circle cx="52" cy="52" r="22" fill="#fff" />
      <circle cx="128" cy="52" r="22" fill="#fff" />
      <circle cx="52" cy="52" r="10" fill="#007AFF" />
      <circle cx="128" cy="52" r="10" fill="#007AFF" />
      {/* 头 */}
      <circle cx="90" cy="104" r="60" fill="#fff" />
      {/* 五官与虎纹 */}
      <g fill="#007AFF">
        <circle cx="68" cy="96" r="7" />
        <circle cx="112" cy="96" r="7" />
        <rect x="76" y="60" width="6" height="16" rx="3" />
        <rect x="87" y="60" width="6" height="16" rx="3" />
        <rect x="98" y="60" width="6" height="16" rx="3" />
        <rect x="34" y="108" width="20" height="6" rx="3" />
        <rect x="30" y="122" width="20" height="6" rx="3" />
        <rect x="126" y="108" width="20" height="6" rx="3" />
        <rect x="130" y="122" width="20" height="6" rx="3" />
        <ellipse cx="90" cy="120" rx="11" ry="8" />
      </g>
    </svg>
  )
}

export default function HomePage({ user, onLogin, onLogout, onStart }: Props) {
  const [queue, setQueue] = useState<TodayQueue | null>(null)

  // 登录后才需要拉今日任务
  useEffect(() => {
    if (!user) return
    api.today().then(setQueue).catch(() => setQueue(null))
  }, [user])

  const newCount = queue?.new.length ?? 0
  const reviewCount = queue?.review.length ?? 0

  return (
    <div className="home">
      {/* 背景光斑：整个页面"活着"的来源 */}
      <div className="home-glow" aria-hidden="true" />

      <div className="home-center">
        <div className="reveal" style={{ animationDelay: '0ms' }}>
          <LogoMark size={user ? 64 : 88} />
        </div>

        {user ? (
          <>
            <h2 className="home-title reveal" style={{ animationDelay: '90ms' }}>
              欢迎回来
            </h2>
            <p className="home-sub reveal" style={{ animationDelay: '150ms' }}>
              今天的任务已经排好了
            </p>

            <div className="home-chips reveal" style={{ animationDelay: '210ms' }}>
              <span className="chip">连续打卡 {user.streakDays} 天</span>
              <span className="chip">已背 {user.learnedWords} 词</span>
            </div>

            <div className="home-card reveal" style={{ animationDelay: '270ms' }}>
              <div className="row">
                <span className="row-label">待复习</span>
                <span className="row-value strong">{reviewCount} 个</span>
              </div>
              <div className="row">
                <span className="row-label">新词</span>
                <span className="row-value strong">{newCount} 个</span>
              </div>
            </div>

            <button
              className="btn btn-primary btn-breathe"
              onClick={onStart}
            >
              开始背单词
            </button>
            <button className="link-btn reveal" style={{ animationDelay: '390ms' }} onClick={onLogout}>
              退出登录
            </button>
          </>
        ) : (
          <>
            <h2 className="home-title reveal" style={{ animationDelay: '90ms' }}>
              欢迎使用 TigerWord
            </h2>
            <p className="home-sub reveal" style={{ animationDelay: '150ms' }}>
              把每天摘下来的生词，变成一份背得掉的清单
            </p>
            <button
              className="btn btn-primary btn-breathe"
              style={{ marginTop: 32 }}
              onClick={onLogin}
            >
              登录 / 注册
            </button>
            <p className="home-foot reveal" style={{ animationDelay: '320ms' }}>
              登录后才能开始背单词
            </p>
          </>
        )}
      </div>
    </div>
  )
}
