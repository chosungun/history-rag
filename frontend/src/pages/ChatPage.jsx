import React, { useState, useRef, useEffect, Suspense, lazy, useMemo } from 'react'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

const HistoricalMap = lazy(() => import('../components/HistoricalMap'))

const EXAMPLES = [
  '1922년 조선호텔 외관과 내부 분위기는?',
  '1930년대 경성 명동(혼마치) 거리 풍경',
  '일제강점기 기생들의 복식과 생활',
  '독립운동가들이 쓰던 암호와 연락 방법',
  '1920년대 경성 카페와 술집 풍경',
  '경성 북촌 한옥 골목 감각 묘사',
]

/* ─── AI 아바타 ─── */
function AiAvatar() {
  return (
    <div style={{
      flexShrink: 0, width: 38, height: 38, borderRadius: '50%',
      background: 'linear-gradient(140deg,#F7CBD7,#EC9BB0)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 4px 14px rgba(224,150,170,.36), inset 0 1px 2px rgba(255,255,255,.5)',
      position: 'relative', marginTop: 2,
    }}>
      <div style={{
        width: 17, height: 17, background: '#fff',
        clipPath: 'polygon(50% 0%,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0% 50%,39% 39%)',
        opacity: 0.96,
      }} />
      <div style={{
        position: 'absolute', top: 7, right: 8,
        width: 5, height: 5, background: '#fff',
        clipPath: 'polygon(50% 0%,62% 38%,100% 50%,62% 62%,50% 100%,38% 62%,0% 50%,38% 38%)',
        opacity: 0.85,
      }} />
    </div>
  )
}

/* ─── rehype 플러그인: HAST 텍스트 노드 내 [ref:N] → <cite>N</cite> ─── */
const rehypeCitations = () => (tree) => {
  const walk = (node) => {
    if (!node.children) return
    let i = 0
    while (i < node.children.length) {
      const child = node.children[i]
      if (child.type === 'text' && /\[ref:\s*\d+\]/.test(child.value)) {
        const parts = []
        const pat = /\[ref:\s*(\d+)\]/g
        let last = 0, m
        while ((m = pat.exec(child.value)) !== null) {
          if (m.index > last) parts.push({ type: 'text', value: child.value.slice(last, m.index) })
          parts.push({ type: 'element', tagName: 'cite', properties: {}, children: [{ type: 'text', value: m[1] }] })
          last = m.index + m[0].length
        }
        if (last < child.value.length) parts.push({ type: 'text', value: child.value.slice(last) })
        node.children.splice(i, 1, ...parts)
        i += parts.length
      } else {
        walk(child)
        i++
      }
    }
  }
  walk(tree)
}

const REMARK_PLUGINS = [remarkGfm]
const REHYPE_PLUGINS = [rehypeCitations]

/* ─── 인용 뱃지 ─── */
function CitationBadge({ source }) {
  const [hovered, setHovered] = useState(false)
  const labelRaw = source.title || ''
  const label = labelRaw.length > 16 ? labelRaw.slice(0, 16) + '…' : labelRaw

  return (
    <span style={{ position: 'relative', display: 'inline-block', margin: '0 2px', verticalAlign: 'middle' }}>
      <span
        onMouseEnter={() => setHovered(true)}
        onMouseLeave={() => setHovered(false)}
        onClick={() => source.url && window.open(source.url, '_blank', 'noreferrer')}
        style={{
          display: 'inline-block',
          background: '#fce8ef',
          color: '#c94470',
          borderRadius: 999,
          fontSize: 11,
          fontWeight: 600,
          padding: '2px 8px',
          cursor: 'pointer',
          lineHeight: 1.5,
          border: '1px solid #f0c4d4',
          whiteSpace: 'nowrap',
          userSelect: 'none',
          margin: '0 2px',
        }}
      >
        {label}
      </span>
      {hovered && (
        <div style={{
          position: 'absolute',
          bottom: 'calc(100% + 8px)',
          left: '50%',
          transform: 'translateX(-50%)',
          background: '#28181e',
          color: '#f0e2ea',
          borderRadius: 10,
          padding: '10px 14px',
          fontSize: 12,
          lineHeight: 1.6,
          width: 240,
          boxShadow: '0 6px 24px rgba(0,0,0,.32)',
          zIndex: 1000,
          pointerEvents: 'none',
        }}>
          <div style={{ fontWeight: 700, color: '#f4a8c4', marginBottom: 2 }}>{source.title}</div>
          {source.year && <div style={{ color: '#b09cb0', fontSize: 11 }}>{source.year}년</div>}
          {source.excerpt && (
            <div style={{ color: '#b8a8b8', marginTop: 6, fontSize: 11, lineHeight: 1.5 }}>
              {source.excerpt.length > 90 ? source.excerpt.slice(0, 90) + '…' : source.excerpt}
            </div>
          )}
          <div style={{
            position: 'absolute', bottom: -5, left: '50%', transform: 'translateX(-50%)',
            width: 0, height: 0,
            borderLeft: '6px solid transparent', borderRight: '6px solid transparent',
            borderTop: '6px solid #28181e',
          }} />
        </div>
      )}
    </span>
  )
}

/* ─── 신뢰도 범례 ─── */
function TrustLegend() {
  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 16,
      paddingBottom: 16, marginBottom: 18,
      borderBottom: '1px solid #F4E9E6', flexWrap: 'wrap',
    }}>
      <span style={{ fontSize: 11, color: '#B6A8AB', fontWeight: 600 }}>정보 신뢰도</span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#9a8b8e' }}>
        <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#E089A0', display: 'inline-block', flexShrink: 0 }} />
        사료 근거
      </span>
      <span style={{ display: 'inline-flex', alignItems: 'center', gap: 6, fontSize: 12, color: '#A9A1A4' }}>
        <span style={{ width: 9, height: 9, borderRadius: '50%', background: '#CCC5C4', display: 'inline-block', flexShrink: 0 }} />
        보완·추정
        <span style={{ color: '#B5ADB0' }}>(참고용)</span>
      </span>
    </div>
  )
}

/* ─── 라이트박스 ─── */
function Lightbox({ photos, index, onClose, onNav }) {
  const photo = photos[index]

  useEffect(() => {
    const onKey = e => {
      if (e.key === 'Escape') onClose()
      if (e.key === 'ArrowLeft') onNav(-1)
      if (e.key === 'ArrowRight') onNav(1)
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [onClose, onNav])

  return (
    <div
      onClick={onClose}
      style={{
        position: 'fixed', inset: 0, zIndex: 9999,
        background: 'rgba(20,8,14,0.93)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}
    >
      {photos.length > 1 && (
        <button
          onClick={e => { e.stopPropagation(); onNav(-1) }}
          style={{
            position: 'absolute', left: '1rem',
            background: 'rgba(255,255,255,0.1)', border: 'none',
            color: '#fff', fontSize: '1.5rem', borderRadius: '50%',
            width: 44, height: 44, cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}
        >‹</button>
      )}

      <div
        onClick={e => e.stopPropagation()}
        style={{ maxWidth: '90vw', maxHeight: '90vh', display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '0.75rem' }}
      >
        <img
          src={photo.original || photo.thumbnail}
          alt={photo.title || ''}
          style={{ maxWidth: '100%', maxHeight: '82vh', objectFit: 'contain', borderRadius: 6 }}
        />
        <div style={{ textAlign: 'center' }}>
          {photo.title && <div style={{ color: '#fff', fontSize: '0.85rem' }}>{photo.title}</div>}
          <div style={{ color: 'rgba(255,255,255,0.5)', fontSize: '0.75rem', marginTop: '0.2rem', display: 'flex', gap: '0.75rem', justifyContent: 'center' }}>
            {photo.year && <span>{photo.year}년</span>}
            {photo.source && <span>{photo.source}</span>}
            {photo.url && (
              <a href={photo.url} target="_blank" rel="noreferrer" style={{ color: '#f4a0bc' }}>원본 →</a>
            )}
          </div>
          <div style={{ color: 'rgba(255,255,255,0.25)', fontSize: '0.7rem', marginTop: '0.3rem' }}>
            {index + 1} / {photos.length} · ESC 닫기 · ← → 탐색
          </div>
        </div>
      </div>

      {photos.length > 1 && (
        <button
          onClick={e => { e.stopPropagation(); onNav(1) }}
          style={{
            position: 'absolute', right: '1rem',
            background: 'rgba(255,255,255,0.1)', border: 'none',
            color: '#fff', fontSize: '1.5rem', borderRadius: '50%',
            width: 44, height: 44, cursor: 'pointer', display: 'flex',
            alignItems: 'center', justifyContent: 'center',
          }}
        >›</button>
      )}

      <button
        onClick={onClose}
        style={{
          position: 'absolute', top: '1rem', right: '1rem',
          background: 'none', border: 'none',
          color: 'rgba(255,255,255,0.5)', fontSize: '1.4rem', cursor: 'pointer',
        }}
      >✕</button>
    </div>
  )
}

/* ─── 사진 그리드 ─── */
function PhotoGrid({ photos }) {
  const [expanded, setExpanded] = useState(false)
  const [lbIndex, setLbIndex] = useState(null)
  const valid = (photos || []).filter(p => p.thumbnail || p.original)
  if (valid.length === 0) return null

  const INITIAL = 3
  const shown = expanded ? valid : valid.slice(0, INITIAL)
  const sources = valid.map(p => p.source).filter((v, i, a) => v && a.indexOf(v) === i).join(' · ')

  const closeLb = () => setLbIndex(null)
  const navLb = dir => setLbIndex(i => (i + dir + valid.length) % valid.length)

  return (
    <div style={{ marginTop: 22 }}>
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: 8 }}>
        {shown.map((photo, i) => (
          <div
            key={photo.id || i}
            onClick={() => setLbIndex(i)}
            title={photo.title}
            style={{
              borderRadius: 11, overflow: 'hidden', aspectRatio: '4/3',
              cursor: 'zoom-in', background: '#E8DDD4',
              position: 'relative', display: 'flex', alignItems: 'flex-end', padding: 9,
            }}
          >
            <img
              src={photo.thumbnail || photo.original}
              alt={photo.title || ''}
              loading="lazy"
              style={{ position: 'absolute', inset: 0, width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              onError={e => { e.target.closest('div').style.display = 'none' }}
            />
            {photo.title && (
              <span style={{
                position: 'relative', fontFamily: 'ui-monospace,monospace',
                fontSize: 10, color: '#6f5f4d',
                background: 'rgba(255,255,255,.72)', padding: '2px 7px',
                borderRadius: 5, maxWidth: '100%', overflow: 'hidden',
                textOverflow: 'ellipsis', whiteSpace: 'nowrap',
              }}>
                {photo.title}
              </span>
            )}
          </div>
        ))}
      </div>

      {valid.length > INITIAL && (
        <button
          onClick={() => setExpanded(v => !v)}
          style={{
            marginTop: 8, width: '100%',
            background: '#FCF1F4', border: '1px solid #F3E0E5',
            color: '#C16A82', borderRadius: 10,
            padding: 9, cursor: 'pointer',
            fontSize: 13, fontWeight: 600, fontFamily: 'inherit',
            textAlign: 'center',
          }}
        >
          {expanded ? '접기 ▴' : `전체 보기 (${valid.length}장) ▾`}
        </button>
      )}

      {sources && (
        <div style={{ fontSize: 11, color: '#B6A8AB', marginTop: 7 }}>{sources}</div>
      )}

      {lbIndex !== null && (
        <Lightbox photos={valid} index={lbIndex} onClose={closeLb} onNav={navLb} />
      )}
    </div>
  )
}

/* ─── 유저 말풍선 ─── */
function UserBubble({ content }) {
  return (
    <div style={{ alignSelf: 'flex-end', maxWidth: '64%' }}>
      <div style={{
        background: '#F6DCE3', color: '#5b4a50',
        padding: '14px 21px',
        borderRadius: '22px 22px 6px 22px',
        fontSize: 15, lineHeight: 1.5,
        boxShadow: '0 2px 10px rgba(200,120,140,.10)',
        wordBreak: 'break-word',
      }}>
        {content}
      </div>
    </div>
  )
}

/* ─── AI 말풍선 ─── */
const AiBubble = React.memo(function AiBubble({ content, photos, sources, coords, showMap, query }) {
  const mdComponents = useMemo(() => ({
    p: ({ children }) => <p style={{ margin: '0 0 0.75em' }}>{children}</p>,
    strong: ({ children }) => <strong style={{ color: '#C16A82', fontWeight: 700 }}>{children}</strong>,
    del: ({ children }) => <span style={{ color: '#ABA4A6', fontStyle: 'normal', textDecoration: 'none' }}>{children}</span>,
    h1: ({ children }) => <h1 style={{ color: '#574349', fontSize: '1.1rem', margin: '0.75em 0 0.4em', fontWeight: 700 }}>{children}</h1>,
    h2: ({ children }) => <h2 style={{ color: '#574349', fontSize: '1rem', margin: '0.75em 0 0.4em', fontWeight: 700 }}>{children}</h2>,
    h3: ({ children }) => <h3 style={{ color: '#C16A82', fontSize: '0.95rem', margin: '0.5em 0 0.3em', fontWeight: 700 }}>{children}</h3>,
    ul: ({ children }) => <ul style={{ paddingLeft: '1.25em', margin: '0.4em 0' }}>{children}</ul>,
    ol: ({ children }) => <ol style={{ paddingLeft: '1.25em', margin: '0.4em 0' }}>{children}</ol>,
    li: ({ children }) => <li style={{ marginBottom: '0.2em' }}>{children}</li>,
    code: ({ children }) => <code style={{ background: '#FFF5F8', color: '#C16A82', padding: '0.1em 0.3em', borderRadius: 3, fontSize: '0.85em' }}>{children}</code>,
    table: ({ children }) => <table style={{ borderCollapse: 'collapse', width: '100%', margin: '0.5em 0', fontSize: '0.85rem' }}>{children}</table>,
    th: ({ children }) => <th style={{ border: '1px solid #F0E3E0', padding: '0.4em 0.75em', background: '#FFF5F8', color: '#C16A82', textAlign: 'left' }}>{children}</th>,
    td: ({ children }) => <td style={{ border: '1px solid #F0E3E0', padding: '0.4em 0.75em', color: '#4c4145' }}>{children}</td>,
    hr: () => (
      <div style={{
        height: 2, margin: '18px 0',
        background: 'radial-gradient(circle, #E7CFD5 1px, transparent 1.4px) repeat-x',
        backgroundSize: '9px 2px',
        WebkitMask: 'linear-gradient(90deg,transparent,#000 20%,#000 80%,transparent)',
        mask: 'linear-gradient(90deg,transparent,#000 20%,#000 80%,transparent)',
      }} />
    ),
    a: ({ href, children }) => (
      <a href={href} target="_blank" rel="noreferrer" style={{ color: '#a060c8' }}>{children}</a>
    ),
    cite: ({ children }) => {
      const text = Array.isArray(children) ? children.join('') : String(children ?? '')
      const n = parseInt(text, 10) - 1
      const src = sources?.[n]
      return src ? <CitationBadge source={src} /> : null
    },
  }), [sources])

  return (
    <div style={{ display: 'flex', gap: 13, alignItems: 'flex-start' }}>
      <AiAvatar />
      <div style={{
        flex: 1, minWidth: 0,
        background: '#FFFFFF',
        border: '1px solid #F0E3E0',
        borderRadius: '8px 22px 22px 22px',
        padding: '24px 26px',
        boxShadow: '0 4px 18px rgba(150,110,115,.07)',
        overflow: 'visible',
      }}>
        <TrustLegend />

        <div style={{ color: '#4c4145', fontSize: 15, lineHeight: 1.75, wordBreak: 'break-word' }}>
          <ReactMarkdown
            remarkPlugins={REMARK_PLUGINS}
            rehypePlugins={REHYPE_PLUGINS}
            components={mdComponents}
          >
            {content}
          </ReactMarkdown>
        </div>

        <PhotoGrid photos={photos} />

        {coords && showMap !== false && (
          <Suspense fallback={<div style={{ height: 240, background: '#F5EEF0', borderRadius: 14, marginTop: 16 }} />}>
            <HistoricalMap lat={coords.lat} lng={coords.lng} label={query} />
          </Suspense>
        )}
      </div>
    </div>
  )
})

/* ─── 로딩 말풍선 ─── */
function LoadingBubble() {
  return (
    <div style={{ display: 'flex', gap: 13, alignItems: 'flex-start' }}>
      <AiAvatar />
      <div style={{
        background: '#FFFFFF', border: '1px solid #F0E3E0',
        borderRadius: '8px 22px 22px 22px',
        padding: '20px 26px',
        color: '#9a8b8e', fontSize: 14,
        boxShadow: '0 4px 18px rgba(150,110,115,.07)',
      }}>
        사료 검색 중<LoadingDots />
      </div>
    </div>
  )
}

function LoadingDots() {
  const [dots, setDots] = useState('.')
  useEffect(() => {
    const t = setInterval(() => setDots(d => d.length >= 3 ? '.' : d + '.'), 400)
    return () => clearInterval(t)
  }, [])
  return <span>{dots}</span>
}

/* ─── 빈 화면 예시 질문 ─── */
function EmptyState({ onSend }) {
  return (
    <div style={{ textAlign: 'center', padding: '5rem 0 2rem' }}>
      <h1 style={{
        fontSize: '1.6rem', fontWeight: 700, color: '#C16A82',
        letterSpacing: '-0.01em', marginBottom: '0.5rem',
      }}>
        근현대사 고증 AI
      </h1>
      <p style={{ color: '#9a8b8e', fontSize: '0.85rem', marginBottom: '2.5rem' }}>
        일제강점기 (1910~1945) · 소설 집필 고증 채팅
      </p>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap', justifyContent: 'center' }}>
        {EXAMPLES.map(ex => (
          <button
            key={ex}
            onClick={() => onSend(ex)}
            style={{
              background: '#fff', border: '1px solid #EAD8DC',
              color: '#A88E94', borderRadius: 999,
              padding: '7px 15px', cursor: 'pointer',
              fontSize: 13, fontFamily: 'inherit',
              transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = '#C16A82'; e.currentTarget.style.borderColor = '#EBAFC0' }}
            onMouseLeave={e => { e.currentTarget.style.color = '#A88E94'; e.currentTarget.style.borderColor = '#EAD8DC' }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ─── 옵션 칩 ─── */
function OptionChip({ label, active, onClick }) {
  return (
    <button
      onClick={onClick}
      style={{
        display: 'inline-flex', alignItems: 'center', gap: 5,
        background: active ? '#FFF0F4' : '#fff',
        border: `1px solid ${active ? '#E08AA0' : '#EAD8DC'}`,
        color: active ? '#C16A82' : '#A88E94',
        borderRadius: 999, padding: '5px 13px',
        cursor: 'pointer', fontSize: 13, fontFamily: 'inherit',
        fontWeight: active ? 600 : 400,
        transition: 'all 0.15s',
      }}
    >
      <span style={{
        width: 14, height: 14, borderRadius: '50%',
        border: `1.5px solid ${active ? '#E08AA0' : '#CFC4C7'}`,
        background: active ? '#E08AA0' : 'transparent',
        display: 'inline-flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, transition: 'all 0.15s',
      }}>
        {active && <span style={{ width: 5, height: 5, background: '#fff', borderRadius: '50%' }} />}
      </span>
      {label}
    </button>
  )
}

/* ─── 메인 ChatPage ─── */
export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [plusOpen, setPlusOpen] = useState(false)
  const [opts, setOpts] = useState({ photos: true, news: true, map: true })
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  const toggleOpt = key => setOpts(o => ({ ...o, [key]: !o[key] }))

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text = input) => {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setInput('')
    if (textareaRef.current) textareaRef.current.style.height = '52px'

    const userMsg = { role: 'user', content: trimmed }
    const updated = [...messages, userMsg]
    setMessages(updated)
    setLoading(true)

    try {
      const apiMessages = updated.map(m => ({ role: m.role, content: m.content }))
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          messages: apiMessages,
          include_photos: opts.photos,
          include_news: opts.news,
        }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      const sourcePhotos = opts.photos
        ? (data.sources || [])
            .filter(s => s.image_url)
            .map(s => ({
              id: `src_${s.url}`,
              title: s.title, year: s.year,
              thumbnail: s.image_url, original: s.image_url,
              source: s.category || s.title, url: s.url,
            }))
        : []
      const _SOURCE_ORDER = { '서울역사아카이브': 0, '공유마당': 1, 'Wikimedia Commons': 2 }
      const allPhotos = [...(data.photos || []), ...sourcePhotos]
        .sort((a, b) => (_SOURCE_ORDER[a.source] ?? 1) - (_SOURCE_ORDER[b.source] ?? 1))

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || '답변을 생성하지 못했습니다.',
        photos: allPhotos,
        sources: data.sources || [],
        sourcesNews: data.sources_news || [],
        coords: data.coords || null,
        showMap: opts.map,
        query: trimmed,
      }])
    } catch {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '서버 연결 실패. Docker가 실행 중인지 확인하세요.\n\n`docker compose up`',
        photos: [], sources: [],
      }])
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); send() }
  }

  const handleTextareaChange = e => {
    setInput(e.target.value)
    e.target.style.height = '52px'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  const isEmpty = messages.length === 0

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: 'calc(100vh - 65px)' }}>
      {/* 메시지 영역 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '36px 0 1rem' }}>
        {isEmpty
          ? <EmptyState onSend={send} />
          : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 24 }}>
              {messages.map((msg, i) =>
                msg.role === 'user'
                  ? <UserBubble key={i} content={msg.content} />
                  : <AiBubble key={i} content={msg.content} photos={msg.photos} sources={msg.sources} coords={msg.coords} showMap={msg.showMap} query={msg.query} />
              )}
              {loading && <LoadingBubble />}
            </div>
          )
        }
        <div ref={bottomRef} />
      </div>

      {/* 푸터 */}
      <div style={{
        flexShrink: 0,
        borderTop: '1px solid #EFE2DF',
        padding: '18px 0 26px',
      }}>
        {/* 옵션 패널 */}
        {plusOpen && (
          <div style={{
            display: 'flex', alignItems: 'center', gap: 8,
            marginBottom: 10, padding: '8px 4px',
            borderBottom: '1px solid #F0E3E0',
          }}>
            <span style={{ fontSize: 12, color: '#C2B4B7', marginRight: 4 }}>옵션</span>
            <OptionChip label="사진 포함" active={opts.photos} onClick={() => toggleOpt('photos')} />
            <OptionChip label="신문 검색" active={opts.news} onClick={() => toggleOpt('news')} />
            <OptionChip label="지도 표시" active={opts.map} onClick={() => toggleOpt('map')} />
          </div>
        )}

        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          {/* 플러스 버튼 */}
          <button
            onClick={() => setPlusOpen(o => !o)}
            title="검색 옵션"
            style={{
              flexShrink: 0, width: 40, height: 40,
              borderRadius: '50%',
              background: plusOpen ? '#FFF0F4' : '#fff',
              border: `1.5px solid ${plusOpen ? '#E08AA0' : '#EAD8DC'}`,
              color: plusOpen ? '#C16A82' : '#C2B4B7',
              fontSize: 22, lineHeight: 1,
              cursor: 'pointer', display: 'flex',
              alignItems: 'center', justifyContent: 'center',
              transition: 'all 0.15s', marginBottom: 6,
              fontWeight: 300,
            }}
          >
            {plusOpen ? '×' : '+'}
          </button>

          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="고증이 필요한 장면이나 내용을 질문하세요…"
            rows={1}
            style={{
              flex: 1,
              background: '#fff', border: '1px solid #ECDDDF',
              borderRadius: 16, padding: '15px 18px',
              fontSize: 14, color: '#4c4145',
              outline: 'none', resize: 'none',
              height: 52, maxHeight: 140,
              fontFamily: 'inherit', lineHeight: 1.5,
              overflowY: 'auto',
            }}
          />
          <button
            onClick={() => send()}
            disabled={loading || !input.trim()}
            style={{
              flexShrink: 0,
              background: loading || !input.trim()
                ? '#E8D8DC'
                : 'linear-gradient(135deg,#EFA6B8,#E08AA0)',
              color: '#fff',
              border: 'none', borderRadius: 16,
              padding: '0 28px',
              fontWeight: 700, fontSize: 14,
              cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              boxShadow: loading || !input.trim() ? 'none' : '0 4px 14px rgba(224,138,160,.35)',
              fontFamily: 'inherit',
              transition: 'all 0.15s',
              height: 52,
            }}
          >
            전송
          </button>
        </div>

        <div style={{ textAlign: 'center', fontSize: 12, color: '#C2B4B7', marginTop: 12 }}>
          Enter 전송 · Shift+Enter 줄바꿈
        </div>
      </div>
    </div>
  )
}
