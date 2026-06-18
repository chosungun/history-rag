import React, { useState } from 'react'

const S = {
  hero: { textAlign: 'center', padding: '3rem 0 2rem' },
  title: { fontSize: '2rem', fontWeight: '300', color: '#e8e2d9', letterSpacing: '0.1em', marginBottom: '0.5rem' },
  sub: { color: '#6b6456', fontSize: '0.875rem' },
  searchBox: {
    display: 'flex', gap: '0.75rem', maxWidth: '680px',
    margin: '2rem auto 0', background: '#1a1915',
    border: '1px solid #2a2820', borderRadius: '8px', padding: '0.5rem',
  },
  input: {
    flex: 1, background: 'none', border: 'none', outline: 'none',
    color: '#e8e2d9', fontSize: '0.95rem', padding: '0.5rem 0.75rem',
  },
  btn: (loading) => ({
    background: loading ? '#2a2820' : '#c9a96e', color: loading ? '#6b6456' : '#0f0e0c',
    border: 'none', borderRadius: '6px', padding: '0.5rem 1.25rem',
    cursor: loading ? 'not-allowed' : 'pointer', fontWeight: '600',
    fontSize: '0.875rem', whiteSpace: 'nowrap', transition: 'background 0.15s',
  }),
  examples: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap', justifyContent: 'center', marginTop: '1rem' },
  exBtn: {
    background: 'none', border: '1px solid #2a2820', color: '#6b6456',
    borderRadius: '20px', padding: '0.3rem 0.85rem', cursor: 'pointer',
    fontSize: '0.8rem', transition: 'all 0.15s',
  },
  result: { marginTop: '2.5rem' },
  answerBox: {
    background: '#1a1915', border: '1px solid #2a2820',
    borderRadius: '10px', padding: '1.5rem', marginBottom: '1.5rem',
  },
  answerLabel: { color: '#c9a96e', fontSize: '0.75rem', fontWeight: '600', letterSpacing: '0.08em', marginBottom: '1rem' },
  answerText: { color: '#e8e2d9', lineHeight: '1.9', fontSize: '0.95rem', whiteSpace: 'pre-wrap' },
  // 탭
  tabBar: { display: 'flex', gap: '0', borderBottom: '1px solid #2a2820', marginBottom: '1rem' },
  tab: (active) => ({
    background: 'none', border: 'none',
    borderBottom: active ? '2px solid #c9a96e' : '2px solid transparent',
    color: active ? '#c9a96e' : '#6b6456',
    cursor: 'pointer', padding: '0.5rem 1rem',
    fontSize: '0.8rem', fontWeight: active ? '600' : '400',
    letterSpacing: '0.05em', marginBottom: '-1px', transition: 'all 0.15s',
  }),
  badge: {
    display: 'inline-block', background: '#2a2820', color: '#6b6456',
    borderRadius: '10px', fontSize: '0.7rem', padding: '0 0.4rem',
    marginLeft: '0.35rem', verticalAlign: 'middle',
  },
  sourceGrid: { display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '0.75rem' },
  sourceCard: {
    background: '#161511', border: '1px solid #2a2820',
    borderRadius: '8px', padding: '1rem',
  },
  newsCard: {
    background: '#161511', border: '1px solid #2a2820',
    borderRadius: '8px', padding: '1rem',
  },
  sourceTitle: { color: '#c9a96e', fontSize: '0.8rem', fontWeight: '600', marginBottom: '0.35rem' },
  newsTitle: { color: '#c9a96e', fontSize: '0.8rem', fontWeight: '600', marginBottom: '0.25rem' },
  newsMeta: { color: '#6b6456', fontSize: '0.72rem', marginBottom: '0.4rem' },
  sourceExcerpt: { color: '#6b6456', fontSize: '0.8rem', lineHeight: '1.6' },
  relevance: { color: '#3d3830', fontSize: '0.75rem', marginTop: '0.5rem' },
  sourceLink: { color: '#4a7c8a', fontSize: '0.75rem', marginTop: '0.5rem', display: 'block' },
  error: { color: '#e05c5c', background: '#1a1110', border: '1px solid #3a2020', borderRadius: '8px', padding: '1rem', marginTop: '2rem' },
  empty: { color: '#3d3830', fontSize: '0.85rem', padding: '1.5rem 0', textAlign: 'center' },
}

const EXAMPLES = [
  '1922년 경성 거리 풍경은?',
  '독립운동 조직 의열단 활동 방식',
  '일제강점기 여성 복식 고증',
  '1920년대 경성 약국에서 구할 수 있는 약',
  '3·1운동 당시 민중의 생활상',
]

function SourceCard({ s, showPhotos }) {
  if (s.category === '신문') {
    const articleTitle = s.excerpt?.includes(' — ')
      ? s.excerpt.split(' — ').slice(1).join(' — ')
      : s.excerpt
    return (
      <div style={S.newsCard}>
        {articleTitle && <div style={{ ...S.sourceExcerpt, color: '#c9a96e', fontWeight: 600, marginBottom: 5 }}>{articleTitle}</div>}
        <div style={S.newsTitle}>{s.title}</div>
        <div style={S.newsMeta}>{s.year && `${s.year}년`}</div>
        {s.url && (
          <a href={s.url} target="_blank" rel="noreferrer" style={S.sourceLink}>
            원문 보기 →
          </a>
        )}
      </div>
    )
  }
  return (
    <div style={S.sourceCard}>
      {showPhotos && s.image_url && (
        <img src={s.image_url} alt={s.title}
          style={{ width: '100%', height: '120px', objectFit: 'cover', borderRadius: '4px', marginBottom: '0.75rem' }}
          onError={e => e.target.style.display = 'none'}
        />
      )}
      <div style={S.sourceTitle}>{s.title} {s.year && `(${s.year})`}</div>
      <div style={S.sourceExcerpt}>{s.excerpt}</div>
      <div style={S.relevance}>관련도 {Math.round(s.relevance * 100)}%</div>
      {s.url && (
        <a href={s.url} target="_blank" rel="noreferrer" style={S.sourceLink}>
          원문 보기 →
        </a>
      )}
    </div>
  )
}

export default function SearchPage() {
  const [query, setQuery] = useState('')
  const [result, setResult] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState('사료')
  const [showPhotos, setShowPhotos] = useState(false)

  const search = async (q = query) => {
    if (!q.trim()) return
    setLoading(true)
    setError('')
    setResult(null)
    setActiveTab('사료')
    try {
      const res = await fetch('/api/search', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: q, top_k: 5 }),
      })
      const data = await res.json()
      setResult(data)
    } catch {
      setError('서버 연결 실패. 백엔드가 실행 중인지 확인하세요.')
    } finally {
      setLoading(false)
    }
  }

  const sources = result ? result.sources ?? [] : []
  const sourcesNews = result ? result.sources_news ?? [] : []

  const tabs = [
    { label: '사료', count: sources.length },
    sourcesNews.length > 0 && { label: '신문', count: sourcesNews.length },
  ].filter(Boolean)

  const displaySources = activeTab === '신문' ? sourcesNews : sources

  return (
    <div>
      <div style={S.hero}>
        <h1 style={S.title}>역사 고증 검색</h1>
        <p style={S.sub}>사료 기반 AI 답변 — 일제강점기 1910~1945</p>
      </div>

      <div style={{ display: 'flex', justifyContent: 'center', marginBottom: '0.5rem' }}>
        <button
          onClick={() => setShowPhotos(v => !v)}
          style={{ background: showPhotos ? '#c9a96e' : '#2a2520', color: showPhotos ? '#1a1510' : '#a09070', border: '1px solid #4a4030', borderRadius: '20px', padding: '0.3rem 1rem', fontSize: '0.8rem', cursor: 'pointer' }}
        >
          사진 포함
        </button>
      </div>

      <div style={S.searchBox}>
        <input
          style={S.input}
          placeholder="고증이 필요한 내용을 질문하세요..."
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
        />
        <button style={S.btn(loading)} onClick={() => search()} disabled={loading}>
          {loading ? '검색 중...' : '검색'}
        </button>
      </div>

      <div style={S.examples}>
        {EXAMPLES.map(ex => (
          <button key={ex} style={S.exBtn} onClick={() => { setQuery(ex); search(ex) }}>
            {ex}
          </button>
        ))}
      </div>

      {error && <div style={S.error}>{error}</div>}

      {result && (
        <div style={S.result}>
          <div style={S.answerBox}>
            <div style={S.answerLabel}>AI 고증 답변</div>
            <div style={S.answerText}>{result.answer}</div>
          </div>

          {(sources.length > 0 || sourcesNews.length > 0) && (
            <div>
              {/* 탭 바 */}
              <div style={S.tabBar}>
                {tabs.map(({ label, count }) => (
                  <button key={label} style={S.tab(activeTab === label)} onClick={() => setActiveTab(label)}>
                    {label}
                    <span style={S.badge}>{count}</span>
                  </button>
                ))}
              </div>

              {/* 소스 그리드 */}
              {displaySources.length === 0
                ? <div style={S.empty}>해당 카테고리 결과 없음</div>
                : (
                  <div style={S.sourceGrid}>
                    {displaySources.map((s, i) => <SourceCard key={i} s={s} showPhotos={showPhotos} />)}
                  </div>
                )
              }
            </div>
          )}
        </div>
      )}
    </div>
  )
}
