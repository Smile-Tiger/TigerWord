// 前端入口：把 App 挂到 index.html 的 #root 上。
import React from 'react'
import ReactDOM from 'react-dom/client'

import App from './App'
import './styles.css'

ReactDOM.createRoot(document.getElementById('root')!).render(
  <React.StrictMode>
    <App />
  </React.StrictMode>,
)
