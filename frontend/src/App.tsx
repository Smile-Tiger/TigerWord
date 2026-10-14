// 应用外壳：顶部大标题 + 底部标签栏，外面套一层手机宽度的居中容器。
//
// 为什么做成"手机宽度 + 底部标签栏"：
//   背单词是一屏一件事的场景，内容铺满宽屏反而分散注意力。
//   收窄成 480px 之后视觉重心集中，也更贴近参考的 iOS 界面。
//
// 图标是手写的极简线条图标（描边风格），和苹果的图标语言一致。
// 没有引图标库 —— 四个图标不值得为它加一个依赖。

import { useState, type FC } from 'react'

import { useAuth } from './auth'
import HomePage from './pages/HomePage'
import ImportPage from './pages/ImportPage'
import SettingsPage from './pages/SettingsPage'
import StatsPage from './pages/StatsPage'
import StudyPage from './pages/StudyPage'

type Tab = 'home' | 'study' | 'import' | 'stats' | 'settings'

// 每个标签页的标题和副标题
const TABS: Record<Tab, { label: string; title: string; subtitle: string }> = {
  home: { label: '首页', title: '', subtitle: '' },
  study: { label: '背单词', title: '背单词', subtitle: '到期的先复习，再学新词' },
  import: { label: '导入', title: '导入生词', subtitle: '支持导出的 PDF 和 txt 列表' },
  stats: { label: '统计', title: '统计', subtitle: '词库进度和答题情况' },
  settings: { label: '设置', title: '设置', subtitle: '模型、Key 和每日任务量' },
}

const TAB_ORDER: Tab[] = ['home', 'study', 'import', 'stats', 'settings']

// ---------- 图标（描边风格，24x24 视口）----------

const IconStudy: FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round">
    <rect x="3" y="4" width="18" height="13" rx="3" />
    <path d="M8 20h8" />
  </svg>
)

const IconImport: FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M12 3v11" />
    <path d="M8 10l4 4 4-4" />
    <path d="M4 16v3a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-3" />
  </svg>
)

const IconStats: FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M6 20v-8" />
    <path d="M12 20V5" />
    <path d="M18 20v-5" />
  </svg>
)

const IconSettings: FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 7h4" />
    <circle cx="11" cy="7" r="2.5" />
    <path d="M13.5 7H20" />
    <path d="M4 17h6.5" />
    <circle cx="13" cy="17" r="2.5" />
    <path d="M15.5 17H20" />
  </svg>
)

const IconHome: FC = () => (
  <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
    strokeLinecap="round" strokeLinejoin="round">
    <path d="M4 10.5 12 4l8 6.5" />
    <path d="M6 9.8V19a1 1 0 0 0 1 1h10a1 1 0 0 0 1-1V9.8" />
  </svg>
)

const ICONS: Record<Tab, FC> = {
  home: IconHome,
  study: IconStudy,
  import: IconImport,
  stats: IconStats,
  settings: IconSettings,
}

export default function App() {
  // 打开应用先落在首页：未登录看到欢迎和登录，已登录看到今天的任务
  const [tab, setTab] = useState<Tab>('home')
  const { user, login, logout } = useAuth()
  const meta = TABS[tab]

  return (
    <div className="app-shell">
      <header className="app-header">
        {/* 首页自己排版品牌区，不用外壳的大标题 */}
        {tab !== 'home' && (
          <>
            <h1>{meta.title}</h1>
            <p>{meta.subtitle}</p>
          </>
        )}
      </header>

      <main className="app-content">
        {tab === 'home' && (
          <HomePage
            user={user}
            onLogin={login}
            onLogout={logout}
            onStart={() => setTab('study')}
          />
        )}
        {/* 登录后才让背单词：学习记录要挂在账号上，没账号没地方存 */}
        {tab === 'study' &&
          (user ? (
            <StudyPage />
          ) : (
            <>
              <div className="group">
                <div className="row">
                  <span className="row-label">需要先登录</span>
                </div>
                <div className="row">
                  <span className="row-sub">登录后才会记录你的学习进度和复习计划</span>
                </div>
              </div>
              <button className="btn btn-primary" onClick={() => setTab('home')}>
                去登录
              </button>
            </>
          ))}
        {tab === 'import' && <ImportPage />}
        {tab === 'stats' && <StatsPage />}
        {tab === 'settings' && <SettingsPage />}
      </main>

      <nav className="tabbar">
        {TAB_ORDER.map((key) => {
          const Icon = ICONS[key]
          return (
            <button
              key={key}
              className={tab === key ? 'tabbar-item active' : 'tabbar-item'}
              onClick={() => setTab(key)}
            >
              <Icon />
              <span>{TABS[key].label}</span>
            </button>
          )
        })}
      </nav>
    </div>
  )
}
