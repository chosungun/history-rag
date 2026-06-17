import React, { useState } from 'react'

const S = {
  title: { fontSize: '1.2rem', fontWeight: '500', color: '#e8e2d9', marginBottom: '0.3rem' },
  sub: { color: '#6b6456', fontSize: '0.8rem', marginBottom: '2rem' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' },
  card: { background: '#1a1915', border: '1px solid #2a2820', borderRadius: '10px', padding: '1.5rem' },
  cardTitle: { color: '#c9a96e', fontSize: '0.78rem', fontWeight: '600', letterSpacing: '0.08em', marginBottom: '1rem' },
  label: { color: '#6b6456', fontSize: '0.8rem', marginBottom: '0.3rem', display: 'block' },
  input: {
    width: '100%', background: '#111', border: '1px solid #2a2820',
    borderRadius: '6px', color: '#e8e2d9', fontSize: '0.875rem',
    padding: '0.6rem 0.875rem', outline: 'none', marginBottom: '1rem',
    boxSizing: 'border-box',
  },
  btn: color => ({
    width: '100%', background: color || '#c9a96e', color: '#0f0e0c',
    border: 'none', borderRadius: '6px', padding: '0.65rem',
    cursor: 'pointer', fontWeight: '600', fontSize: '0.875rem',
  }),
  status: type => ({
    marginTop: '0.875rem', padding: '0.75rem', borderRadius: '6px', fontSize: '0.83rem',
    background: type === 'success' ? '#0f1f0f' : type === 'error' ? '#1f0f0f' : '#1a1915',
    color: type === 'success' ? '#5cb85c' : type === 'error' ? '#e05c5c' : '#6b6456',
    border: `1px solid ${type === 'success' ? '#1a3a1a' : type === 'error' ? '#3a1a1a' : '#2a2820'}`,
  }),
  textarea: {
    width: '100%', background: '#111', border: '1px solid #2a2820',
    borderRadius: '6px', color: '#e8e2d9', fontSize: '0.78rem',
    padding: '0.75rem', outline: 'none', resize: 'vertical', minHeight: '130px',
    fontFamily: 'monospace', marginBottom: '0.875rem', boxSizing: 'border-box',
  },
  tip: { color: '#3d3830', fontSize: '0.74rem', lineHeight: '1.9', marginTop: '1rem' },
}

export default function IngestPage() {
  const [keyword, setKeyword] = useState('')
  const [apiStatus, setApiStatus] = useState(null)
  const [manualJson, setManualJson] = useState('')
  const [manualStatus, setManualStatus] = useState(null)

  const fetchFromWiki = async () => {
    if (!keyword.trim()) return
    setApiStatus({ type: 'loading', msg: '위키백과에서 데이터 수집 중...' })
    try {
      const res = await fetch('/api/ingest/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword, sources: ['wikipedia'] }),
      })
      const data = await res.json()
      setApiStatus({ type: 'success', msg: data.message })
    } catch {
      setApiStatus({ type: 'error', msg: '수집 실패. 백엔드 연결을 확인하세요.' })
    }
  }

  const ingestManual = async () => {
    try {
      const docs = JSON.parse(manualJson)
      const res = await fetch('/api/ingest/manual', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(docs),
      })
      const data = await res.json()
      setManualStatus({ type: 'success', msg: `${data.ingested}개 문서 저장 완료!` })
      setManualJson('')
    } catch (e) {
      setManualStatus({ type: 'error', msg: 'JSON 오류 또는 서버 오류: ' + e.message })
    }
  }

  return (
    <div>
      <h2 style={S.title}>자료 입력</h2>
      <p style={S.sub}>사료를 AI 검색 DB에 저장합니다 — 저장한 내용이 채팅 답변의 근거가 됩니다</p>

      <div style={S.grid}>
        {/* 위키백과 자동 수집 */}
        <div style={S.card}>
          <div style={S.cardTitle}>위키백과 자동 수집</div>
          <label style={S.label}>검색 키워드</label>
          <input
            style={S.input}
            value={keyword}
            onChange={e => setKeyword(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && fetchFromWiki()}
            placeholder="예: 조선호텔, 의열단, 경성"
          />
          <button style={S.btn()} onClick={fetchFromWiki}>수집 시작</button>
          {apiStatus && <div style={S.status(apiStatus.type)}>{apiStatus.msg}</div>}
          <div style={S.tip}>
            💡 API 키 없이 바로 사용 가능<br />
            한국어 위키백과에서 관련 문서를 자동으로<br />
            가져와 ChromaDB에 저장합니다
          </div>
        </div>

        {/* 직접 텍스트 입력 */}
        <div style={S.card}>
          <div style={S.cardTitle}>직접 텍스트 입력</div>
          <label style={S.label}>JSON 형식으로 붙여넣기</label>
          <textarea
            style={S.textarea}
            value={manualJson}
            onChange={e => setManualJson(e.target.value)}
            placeholder={`[\n  {\n    "id": "doc001",\n    "text": "사료 내용...",\n    "source": "출처명",\n    "year": "1922",\n    "url": "https://..."\n  }\n]`}
          />
          <button style={S.btn('#4a7c8a')} onClick={ingestManual}>DB에 저장</button>
          {manualStatus && <div style={S.status(manualStatus.type)}>{manualStatus.msg}</div>}
          <div style={S.tip}>
            💡 추천 출처<br />
            우리역사넷 (contents.history.go.kr)<br />
            서울역사아카이브 (museum.seoul.go.kr)<br />
            한국민족문화대백과사전 (encykorea.aks.ac.kr)
          </div>
        </div>
      </div>
    </div>
  )
}
