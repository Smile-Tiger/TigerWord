// 导入页面：把导出的生词文件传上来，跑完整条导入管线，并显示导入报告。
// 版式沿用 iOS 的"白色分组卡片"：上传区一张卡，报告一张卡。

import { useRef, useState } from 'react'

import { api } from '../api/client'
import type { ImportReport } from '../types'

/** 上传图标：一个托盘加向下的箭头 */
function IconUpload() {
  return (
    <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8"
      strokeLinecap="round" strokeLinejoin="round">
      <path d="M12 16V4" />
      <path d="M8 8l4-4 4 4" />
      <path d="M4 16v2a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2v-2" />
    </svg>
  )
}

export default function ImportPage() {
  const [report, setReport] = useState<ImportReport | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [fileName, setFileName] = useState('')
  const inputRef = useRef<HTMLInputElement>(null)

  async function handleUpload() {
    const file = inputRef.current?.files?.[0]
    if (!file) {
      setError('先选一个文件')
      return
    }
    setBusy(true)
    setError(null)
    setReport(null)
    try {
      setReport(await api.upload(file))
    } catch (err) {
      setError((err as Error).message)
    } finally {
      setBusy(false)
    }
  }

  const notes = report
    ? [...(report.warnings ?? []), ...(report.enrich?.notes ?? [])]
    : []

  return (
    <>
      <div className="dropzone">
        <div className="dropzone-icon">
          <IconUpload />
        </div>
        <div style={{ fontSize: 17, fontWeight: 600, marginTop: 4 }}>选择生词文件</div>
        <div className="note" style={{ margin: 0 }}>
          支持每日英语听力导出的 PDF，也支持一行一个词的 txt
        </div>
        <input
          ref={inputRef}
          type="file"
          accept=".pdf,.txt,.md"
          onChange={(event) => setFileName(event.target.files?.[0]?.name ?? '')}
        />
      </div>

      <button className="btn btn-primary" disabled={busy || !fileName} onClick={() => void handleUpload()}>
        {busy ? '导入中…（AI 补全可能要等十几秒）' : '开始导入'}
      </button>

      {error && <p className="error">导入失败：{error}</p>}

      {report && (
        <>
          <div className="report-head">导入完成</div>
          <div className="group">
            <div className="row">
              <span className="row-label">文件里解析出</span>
              <span className="row-value">{report.parsed} 条</span>
            </div>
            <div className="row">
              <span className="row-label">实际入库</span>
              <span className="row-value">{report.imported} 条</span>
            </div>
            <div className="row">
              <span className="row-label">新增</span>
              <span className="row-value">{report.added}</span>
            </div>
            <div className="row">
              <span className="row-label">更新 / 本来就有的</span>
              <span className="row-value">
                {report.updated} / {report.unchanged}
              </span>
            </div>
            <div className="row">
              <span className="row-label">补上音标 / 释义</span>
              <span className="row-value">
                {report.enrich?.filled_phonetic ?? 0} / {report.enrich?.filled_definition ?? 0}
              </span>
            </div>
            <div className="row">
              <span className="row-label">词库总量</span>
              <span className="row-value">{report.entries_in_db} 条</span>
            </div>
          </div>
        </>
      )}

      {notes.map((text) => (
        <p className="note" key={text}>· {text}</p>
      ))}

      <p className="note">
        同一个文件重复导入不会产生重复词条；文件里已经有的音标和释义不会被 AI 覆盖。
      </p>
    </>
  )
}
