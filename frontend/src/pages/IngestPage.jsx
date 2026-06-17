import React, { useState } from 'react'

const S = {
  title: { fontSize: '1.25rem', fontWeight: '500', color: '#e8e2d9', marginBottom: '0.35rem' },
  sub: { color: '#6b6456', fontSize: '0.8rem', marginBottom: '2rem' },
  grid: { display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '1.5rem' },
  card: { background: '#1a1915', border: '1px solid #2a2820', borderRadius: '10px', padding: '1.5rem' },
  cardTitle: { color: '#c9a96e', fontSize: '0.8rem', fontWeight: '600', letterSpacing: '0.08em', marginBottom: '1rem' },
  label: { color: '#6b6456', fontSize: '0.8rem', marginBottom: '0.35rem', display: 'block' },
  input: {
    width: '100%', background: '#111', border: '1px solid #2a2820',
    borderRadius: '6px', color: '#e8e2d9', fontSize: '0.875rem',
    padding: '0.6rem 0.875rem', outline: 'none', marginBottom: '0.75rem',
  },
  checkRow: { display: 'flex', gap: '1rem', marginBottom: '1rem' },
  checkLabel: { color: '#6b6456', fontSize: '0.85rem', display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer' },
  btn: (color) => ({
    width: '100%', background: color || '#c9a96e', color: '#0f0e0c',
    border: 'none', borderRadius: '6px', padding: '0.65rem',
    cursor: 'pointer', fontWeight: '600', fontSize: '0.875rem',
  }),
  status: (type) => ({
    marginTop: '1rem', padding: '0.75rem', borderRadius: '6px', fontSize: '0.85rem',
    background: type === 'success' ? '#0f1f0f' : type === 'error' ? '#1f0f0f' : '#1a1915',
    color: type === 'success' ? '#5cb85c' : type === 'error' ? '#e05c5c' : '#6b6456',
    border: `1px solid ${type === 'success' ? '#1a3a1a' : type === 'error' ? '#3a1a1a' : '#2a2820'}`,
  }),
  textarea: {
    width: '100%', background: '#111', border: '1px solid #2a2820',
    borderRadius: '6px', color: '#e8e2d9', fontSize: '0.8rem',
    padding: '0.75rem', outline: 'none', resize: 'vertical', minHeight: '120px',
    fontFamily: 'monospace', marginBottom: '0.75rem',
  },
  tip: { color: '#3d3830', fontSize: '0.75rem', lineHeight: '1.8', marginTop: '1rem' },
}

export default function IngestPage() {
  const [keyword, setKeyword] = useState('')
  const [sources, setSources] = useState(['history_db', 'independence'])
  const [apiStatus, setApiStatus] = useState(null)
  const [manualJson, setManualJson] = useState('')
  const [manualStatus, setManualStatus] = useState(null)

  const toggleSource = (s) => {
    setSources(prev => prev.includes(s) ? prev.filter(x => x !== s) : [...prev, s])
  }

  const fetchFromApi = async () => {
    if (!keyword.trim()) return
    setApiStatus({ type: 'loading', msg: '데이터 수집 시작...' })
    try {
      const res = await fetch('/api/ingest/fetch', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ keyword, sources }),
      })
      const data = await res.json()
      setApiStatus({ type: 'success', msg: data.message })
    } catch {
      setApiStatus({ type: 'error', msg: '수집 실패. 백엔드 연결 및 API 키를 확인하세요.' })
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
    } catch (e) {
      setManualStatus({ type: 'error', msg: 'JSON 파싱 오류 또는 서버 오류: ' + e.message })
    }
  }

  return (
    <div>
      <h2 style={S.title}>자료 수집</h2>
      <p style={S.sub}>공공 API에서 사료를 가져와 AI 검색 DB에 저장합니다</p>

      <div style={S.grid}>
        {/* 공공API 수집 */}
        <div style={S.card}>
          <div style={S.cardTitle}>공공 API 수집</div>
          <label style={S.label}>검색 키워드</label>
          <input
            style={S.input} value={keyword}
            onChange={e => setKeyword(e.target.value)}
            placeholder="예: 의열단, 경성, 토지조사"
          />
          <label style={S.label}>수집 소스</label>
          <div style={S.checkRow}>
            {[
              { id: 'history_db', label: '한국사DB' },
              { id: 'independence', label: '독립기념관' },
            ].map(s => (
              <label key={s.id} style={S.checkLabel}>
                <input type="checkbox" checked={sources.includes(s.id)}
                  onChange={() => toggleSource(s.id)} />
                {s.label}
              </label>
            ))}
          </div>
          <button style={S.btn()} onClick={fetchFromApi}>수집 시작</button>
          {apiStatus && <div style={S.status(apiStatus.type)}>{apiStatus.msg}</div>}
          <div style={S.tip}>
            ⚠ API 키는 .env 파일에 설정 필요<br />
            • 국사편찬위원회: data.go.kr → "한국사데이터베이스" 검색<br />
            • 독립기념관: data.go.kr → "독립기념관" 검색<br />
            수집 후 백그라운드에서 임베딩 처리됩니다 (30초~2분)
          </div>
        </div>

        {/* 수동 JSON 입력 */}
        <div style={S.card}>
          <div style={S.cardTitle}>직접 텍스트 입력</div>
          <label style={S.label}>JSON 형식으로 붙여넣기</label>
          <textarea
            style={S.textarea}
            value={manualJson}
            onChange={e => setManualJson(e.target.value)}
            placeholder={`[\n  {\n    "id": "doc001",\n    "text": "사료 내용...",\n    "source": "출처명",\n    "year": "1922",\n    "url": ""\n  }\n]`}
          />
          <button style={S.btn('#4a7c8a')} onClick={ingestManual}>DB에 저장</button>
          {manualStatus && <div style={S.status(manualStatus.type)}>{manualStatus.msg}</div>}
          <div style={S.tip}>
            💡 API 없이도 사용 가능<br />
            우리역사넷, 서울역사아카이브 텍스트를<br />
            복사해서 JSON으로 붙여넣으면 바로 검색 가능
          </div>
        </div>
      </div>
    </div>
  )
}
