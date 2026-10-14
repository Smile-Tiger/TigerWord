// 登录态（占位实现）。
//
// 说明清楚：这是**临时的本地登录态**，还没有真正的账号系统。
// 现在只是把"已登录"这个标记存在浏览器里，用来把界面流程跑通：
//   未登录 -> 首页显示欢迎和登录按钮，"背单词"进不去
//   已登录 -> 首页显示欢迎回来和今日任务，可以开始背
//
// 以后接真账号时，只需要把这个文件换成调后端接口，
// 其它页面的代码一行都不用改（它们只认 isLoading / user 这两个东西）。

import { useCallback, useEffect, useState } from 'react'

const STORAGE_KEY = 'tigerword.user'

export interface User {
  name: string
  /** 连续打卡天数。真账号上线后由后端给，现在先写死演示 */
  streakDays: number
  /** 累计背过的词数。同上 */
  learnedWords: number
}

function readUser(): User | null {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as User) : null
  } catch {
    // 存的东西坏了就当作没登录，不要让整个应用崩掉
    return null
  }
}

export function useAuth() {
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // 首屏读一次本地存的登录态
  useEffect(() => {
    setUser(readUser())
    setLoading(false)
  }, [])

  const login = useCallback(() => {
    const next: User = { name: 'Davies', streakDays: 12, learnedWords: 173 }
    localStorage.setItem(STORAGE_KEY, JSON.stringify(next))
    setUser(next)
    return next
  }, [])

  const logout = useCallback(() => {
    localStorage.removeItem(STORAGE_KEY)
    setUser(null)
  }, [])

  return { user, loading, login, logout }
}
