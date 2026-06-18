import React, { useState, useEffect, useRef } from 'react'

function elapsed(startedAt) {
  const sec = Math.floor(Date.now() / 1000 - startedAt)
  if (sec < 60) return `${sec}초`
  return `${Math.floor(sec / 60)}분 ${sec % 60}초`
}

function JobsPanel({ jobs }) {
  const [, setNow] = useState(Date.now())
  useEffect(() => {
    if (!jobs.some(j => j.status === 'running')) return
    const t = setInterval(() => setNow(Date.now()), 1000)
    return () => clearInterval(t)
  }, [jobs])

  if (!jobs.length) return null

  const total = jobs.length
  const done = jobs.filter(j => j.status === 'done').length
  const errors = jobs.filter(j => j.status === 'error').length
  const current = jobs.find(j => j.status === 'running')
  const isAllDone = done + errors === total
  const totalSaved = jobs.reduce((s, j) => s + (j.saved || 0), 0)
  const pct = Math.round((done + errors) / total * 100)
  const firstJob = jobs[jobs.length - 1]

  return (
    <div style={{ marginBottom: '2rem' }}>
      <style>{`@keyframes pulse { 0%,100%{opacity:1} 50%{opacity:0.3} }`}</style>
      <div style={{
        padding: '1rem 1.25rem',
        borderRadius: 10,
        background: isAllDone ? (errors ? '#fff8f2' : '#f4fff4') : '#fff8fa',
        border: `1px solid ${isAllDone ? (errors ? '#f0d8c8' : '#c8e8c8') : '#f4dce8'}`,
      }}>
        {/* 상태 헤더 */}
        <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 10 }}>
          {!isAllDone
            ? <span style={{ width: 8, height: 8, borderRadius: '50%', background: '#C16A82', flexShrink: 0, display: 'inline-block', animation: 'pulse 1.2s infinite' }} />
            : <span style={{ fontSize: 14, color: errors ? '#c44040' : '#2a8a2a' }}>{errors ? '⚠' : '✓'}</span>
          }
          <span style={{ fontSize: 13, fontWeight: 600, color: '#4c4145', flex: 1 }}>
            {isAllDone
              ? `수집 완료 — 총 ${totalSaved.toLocaleString()}건 저장`
              : `수집 중 · ${done}/${total} 완료`
            }
          </span>
          <span style={{ fontSize: 12, color: '#9a8b8e' }}>
            {elapsed(firstJob.started_at)} 경과
          </span>
        </div>

        {/* 현재 작업 */}
        {current && (
          <div style={{ fontSize: 12, color: '#9a8b8e', marginBottom: 8 }}>
            {current.phase} · {current.label}
          </div>
        )}

        {/* 전체 진행 바 */}
        <div style={{ height: 4, borderRadius: 2, background: '#F0E3E0', overflow: 'hidden' }}>
          <div style={{
            height: '100%', borderRadius: 2,
            background: isAllDone ? (errors ? '#e89040' : '#40a840') : 'linear-gradient(90deg,#EFA6B8,#E08AA0)',
            width: `${pct}%`,
            transition: 'width 0.5s ease',
          }} />
        </div>

        {/* 오류 요약 */}
        {errors > 0 && (
          <div style={{ fontSize: 11, color: '#c44040', marginTop: 6 }}>
            {errors}건 오류 — {jobs.filter(j => j.status === 'error').map(j => j.label).join(', ')}
          </div>
        )}
      </div>
    </div>
  )
}

export default function IngestPage() {
  const [jobs, setJobs] = useState([])
  const pollRef = useRef(null)

  const startPolling = () => {
    if (pollRef.current) return
    pollRef.current = setInterval(async () => {
      try {
        const res = await fetch('/api/ingest/jobs')
        const data = await res.json()
        setJobs(data)
        if (!data.some(j => j.status === 'running')) {
          clearInterval(pollRef.current)
          pollRef.current = null
        }
      } catch {}
    }, 2000)
  }

  useEffect(() => {
    fetch('/api/ingest/jobs').then(r => r.json()).then(setJobs).catch(() => {})
    return () => { if (pollRef.current) clearInterval(pollRef.current) }
  }, [])

  const fetchAll = async () => {
    if (!window.confirm('신문 제외 전체 일괄 수집을 시작합니다.\n잡지 13종 + 관보 + 민족운동·문서류 22종 (순번형)\nhad·haf·ju는 대용량 cap 적용, 나머지 무제한\n순차 실행으로 수 시간~하루 소요될 수 있습니다.\n시작하시겠습니까?')) return
    try {
      const res = await fetch('/api/ingest/fetch-all', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const data = await res.json()
      if (data.job_ids) {
        const r = await fetch('/api/ingest/jobs')
        setJobs(await r.json())
        startPolling()
      }
    } catch (e) {
      console.error(e)
    }
  }

  const fetchLiterature = async () => {
    if (!window.confirm('위키문헌 근대문학을 수집합니다.\n소설 32편 + 시 34편 (총 66작품)\n약 2~3분 소요됩니다.\n시작하시겠습니까?')) return
    try {
      const res = await fetch('/api/ingest/fetch-literature', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' })
      const data = await res.json()
      if (data.job_id) {
        const r = await fetch('/api/ingest/jobs')
        setJobs(await r.json())
        startPolling()
      }
    } catch (e) {
      console.error(e)
    }
  }

  return (
    <div>
      <h2 style={{ fontSize: '1.2rem', fontWeight: '500', color: '#2a1820', marginBottom: '0.3rem' }}>자료 입력</h2>
      <p style={{ color: '#8a7080', fontSize: '0.8rem', marginBottom: '2rem' }}>사료를 AI 검색 DB에 저장합니다 — 저장한 내용이 채팅 답변의 근거가 됩니다</p>

      <JobsPanel jobs={jobs} />

      <div style={{ display: 'flex', flexDirection: 'column', gap: '0.75rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={fetchAll}
            style={{
              background: 'transparent', border: '1px solid #c94470', color: '#c94470',
              borderRadius: '7px', padding: '0.6rem 1.4rem', cursor: 'pointer',
              fontSize: '0.85rem', fontWeight: '600', letterSpacing: '0.04em',
            }}
          >
            전체 일괄 수집 시작
          </button>
          <span style={{ color: '#8a7080', fontSize: '0.75rem' }}>
            신문 제외 전체 — 잡지 13종 + 관보 + 민족운동·문서류 22종 · 순차 실행 · 수 시간 소요
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
          <button
            onClick={fetchLiterature}
            style={{
              background: 'transparent', border: '1px solid #7a6aa0', color: '#7a6aa0',
              borderRadius: '7px', padding: '0.6rem 1.4rem', cursor: 'pointer',
              fontSize: '0.85rem', fontWeight: '600', letterSpacing: '0.04em',
            }}
          >
            근대문학 수집
          </button>
          <span style={{ color: '#8a7080', fontSize: '0.75rem' }}>
            위키문헌 — 소설 32편 + 시 34편 · 약 2~3분 소요
          </span>
        </div>
      </div>
    </div>
  )
}
