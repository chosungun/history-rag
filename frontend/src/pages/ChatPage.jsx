import React, { useState, useRef, useEffect } from 'react'

const EXAMPLES = [
  '1922년 조선호텔 외관과 내부 분위기는?',
  '1930년대 경성 명동(혼마치) 거리 풍경',
  '일제강점기 기생들의 복식과 생활',
  '독립운동가들이 쓰던 암호와 연락 방법',
  '1920년대 경성 카페와 술집 풍경',
  '경성 북촌 한옥 골목 감각 묘사',
]

/* ─── 사진 그리드 ─── */
function PhotoGrid({ photos }) {
  const [expanded, setExpanded] = useState(false)
  const valid = (photos || []).filter(p => p.thumbnail || p.original)
  if (valid.length === 0) return null

  const INITIAL = 3
  const shown = expanded ? valid : valid.slice(0, INITIAL)
  const hiddenCount = valid.length - INITIAL

  return (
    <div style={{ marginTop: '0.875rem' }}>
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(3, 1fr)',
        gap: '0.4rem',
      }}>
        {shown.map((photo, i) => (
          <a
            key={photo.id || i}
            href={photo.url || photo.original}
            target="_blank"
            rel="noreferrer"
            title={photo.title}
            style={{ display: 'block', borderRadius: '5px', overflow: 'hidden', aspectRatio: '4/3', background: '#111' }}
          >
            <img
              src={photo.thumbnail || photo.original}
              alt={photo.title || ''}
              loading="lazy"
              style={{ width: '100%', height: '100%', objectFit: 'cover', display: 'block' }}
              onError={e => { e.target.closest('a').style.display = 'none' }}
            />
          </a>
        ))}
      </div>

      {!expanded && hiddenCount > 0 && (
        <button
          onClick={() => setExpanded(true)}
          style={{
            marginTop: '0.4rem', width: '100%',
            background: 'none', border: '1px solid #2a2820',
            color: '#6b6456', borderRadius: '5px',
            padding: '0.35rem 0', cursor: 'pointer',
            fontSize: '0.78rem', transition: 'color 0.15s',
          }}
        >
          사진 {hiddenCount}장 더보기
        </button>
      )}

      {valid.length > 0 && (
        <div style={{ color: '#2a2820', fontSize: '0.7rem', marginTop: '0.3rem' }}>
          {valid.map(p => p.source).filter((v, i, a) => a.indexOf(v) === i).join(' · ')}
        </div>
      )}
    </div>
  )
}

/* ─── 출처 섹션 ─── */
function Sources({ sources }) {
  const [open, setOpen] = useState(false)
  if (!sources || sources.length === 0) return null

  return (
    <div style={{ marginTop: '0.5rem' }}>
      <button
        onClick={() => setOpen(v => !v)}
        style={{
          background: 'none', border: 'none',
          color: '#3d3830', fontSize: '0.75rem',
          cursor: 'pointer', padding: '0.2rem 0',
          transition: 'color 0.15s',
        }}
      >
        {open ? '출처 접기 ▴' : `참고 사료 ${sources.length}건 ▾`}
      </button>
      {open && (
        <div style={{ marginTop: '0.4rem', display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
          {sources.map((s, i) => (
            <div key={i} style={{
              background: '#111', border: '1px solid #222',
              borderRadius: '5px', padding: '0.5rem 0.75rem',
              fontSize: '0.77rem',
            }}>
              <span style={{ color: '#c9a96e' }}>{s.title}</span>
              {s.year && <span style={{ color: '#3d3830' }}> ({s.year})</span>}
              <div style={{ color: '#6b6456', marginTop: '0.2rem', lineHeight: '1.5' }}>{s.excerpt}</div>
              {s.url && (
                <a href={s.url} target="_blank" rel="noreferrer"
                  style={{ color: '#4a7c8a', fontSize: '0.72rem', display: 'block', marginTop: '0.2rem' }}>
                  원문 보기 →
                </a>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

/* ─── 유저 말풍선 ─── */
function UserBubble({ content }) {
  return (
    <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1.25rem', paddingLeft: '15%' }}>
      <div style={{
        background: '#1e1d19',
        border: '1px solid #2e2c26',
        borderRadius: '14px 14px 3px 14px',
        padding: '0.75rem 1rem',
        color: '#e8e2d9',
        fontSize: '0.9rem',
        lineHeight: '1.65',
        whiteSpace: 'pre-wrap',
      }}>
        {content}
      </div>
    </div>
  )
}

/* ─── AI 말풍선 ─── */
function AiBubble({ content, photos, sources }) {
  return (
    <div style={{ display: 'flex', gap: '0.625rem', marginBottom: '1.5rem', alignItems: 'flex-start', paddingRight: '8%' }}>
      <div style={{
        width: '26px', height: '26px', borderRadius: '50%',
        background: 'rgba(201,169,110,0.1)', border: '1px solid rgba(201,169,110,0.3)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, fontSize: '0.65rem', color: '#c9a96e', marginTop: '2px',
        letterSpacing: '-0.02em',
      }}>AI</div>

      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          background: '#161511',
          border: '1px solid #2a2820',
          borderRadius: '3px 14px 14px 14px',
          padding: '0.875rem 1rem',
          color: '#e8e2d9',
          fontSize: '0.9rem',
          lineHeight: '1.85',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}>
          {content}
        </div>

        <PhotoGrid photos={photos} />
        <Sources sources={sources} />
      </div>
    </div>
  )
}

/* ─── 로딩 말풍선 ─── */
function LoadingBubble() {
  return (
    <div style={{ display: 'flex', gap: '0.625rem', marginBottom: '1.25rem', alignItems: 'flex-start' }}>
      <div style={{
        width: '26px', height: '26px', borderRadius: '50%',
        background: 'rgba(201,169,110,0.1)', border: '1px solid rgba(201,169,110,0.3)',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
        flexShrink: 0, fontSize: '0.65rem', color: '#c9a96e',
      }}>AI</div>
      <div style={{
        background: '#161511', border: '1px solid #2a2820',
        borderRadius: '3px 14px 14px 14px',
        padding: '0.875rem 1rem', color: '#6b6456', fontSize: '0.85rem',
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
    <div style={{ textAlign: 'center', padding: '5rem 1rem 2rem' }}>
      <h1 style={{
        fontSize: '1.6rem', fontWeight: '300', color: '#e8e2d9',
        letterSpacing: '0.12em', marginBottom: '0.5rem',
      }}>
        역사 고증 AI
      </h1>
      <p style={{ color: '#6b6456', fontSize: '0.82rem', marginBottom: '2.5rem' }}>
        일제강점기 (1910~1945) · 소설 집필 고증 채팅
      </p>
      <div style={{
        display: 'flex', gap: '0.5rem', flexWrap: 'wrap',
        justifyContent: 'center', maxWidth: '640px', margin: '0 auto',
      }}>
        {EXAMPLES.map(ex => (
          <button
            key={ex}
            onClick={() => onSend(ex)}
            style={{
              background: 'none', border: '1px solid #2a2820',
              color: '#6b6456', borderRadius: '20px',
              padding: '0.4rem 0.875rem', cursor: 'pointer',
              fontSize: '0.8rem', transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.target.style.color = '#c9a96e'; e.target.style.borderColor = '#4a3e2a' }}
            onMouseLeave={e => { e.target.style.color = '#6b6456'; e.target.style.borderColor = '#2a2820' }}
          >
            {ex}
          </button>
        ))}
      </div>
    </div>
  )
}

/* ─── 메인 ChatPage ─── */
export default function ChatPage() {
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const bottomRef = useRef(null)
  const textareaRef = useRef(null)

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages, loading])

  const send = async (text = input) => {
    const trimmed = text.trim()
    if (!trimmed || loading) return

    setInput('')
    if (textareaRef.current) {
      textareaRef.current.style.height = '44px'
    }

    const userMsg = { role: 'user', content: trimmed }
    const updated = [...messages, userMsg]
    setMessages(updated)
    setLoading(true)

    try {
      const apiMessages = updated.map(m => ({ role: m.role, content: m.content }))
      const res = await fetch('/api/chat', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ messages: apiMessages }),
      })
      if (!res.ok) throw new Error(`HTTP ${res.status}`)
      const data = await res.json()

      setMessages(prev => [...prev, {
        role: 'assistant',
        content: data.answer || '답변을 생성하지 못했습니다.',
        photos: data.photos || [],
        sources: data.sources || [],
      }])
    } catch (e) {
      setMessages(prev => [...prev, {
        role: 'assistant',
        content: '서버 연결 실패. Docker가 실행 중인지 확인하세요.\n\n` docker-compose up `',
        photos: [],
        sources: [],
      }])
    } finally {
      setLoading(false)
      textareaRef.current?.focus()
    }
  }

  const handleKeyDown = e => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      send()
    }
  }

  const handleTextareaChange = e => {
    setInput(e.target.value)
    e.target.style.height = '44px'
    e.target.style.height = Math.min(e.target.scrollHeight, 140) + 'px'
  }

  const isEmpty = messages.length === 0

  return (
    <div style={{
      display: 'flex', flexDirection: 'column',
      height: 'calc(100vh - 61px)',
    }}>
      {/* 메시지 영역 */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '0.5rem 0 1rem' }}>
        {isEmpty
          ? <EmptyState onSend={send} />
          : messages.map((msg, i) =>
              msg.role === 'user'
                ? <UserBubble key={i} content={msg.content} />
                : <AiBubble key={i} content={msg.content} photos={msg.photos} sources={msg.sources} />
            )
        }
        {loading && <LoadingBubble />}
        <div ref={bottomRef} />
      </div>

      {/* 입력 영역 */}
      <div style={{
        borderTop: '1px solid #1e1d19',
        paddingTop: '0.75rem',
        background: '#0f0e0c',
        flexShrink: 0,
      }}>
        {/* 이어서 물어볼 만한 예시 (대화 중일 때) */}
        {!isEmpty && !loading && (
          <div style={{ display: 'flex', gap: '0.4rem', flexWrap: 'wrap', marginBottom: '0.6rem' }}>
            {EXAMPLES.slice(0, 3).map(ex => (
              <button
                key={ex}
                onClick={() => send(ex)}
                style={{
                  background: 'none', border: '1px solid #222',
                  color: '#3d3830', borderRadius: '20px',
                  padding: '0.25rem 0.65rem', cursor: 'pointer',
                  fontSize: '0.75rem', transition: 'all 0.15s',
                }}
                onMouseEnter={e => { e.target.style.color = '#6b6456'; e.target.style.borderColor = '#2a2820' }}
                onMouseLeave={e => { e.target.style.color = '#3d3830'; e.target.style.borderColor = '#222' }}
              >
                {ex}
              </button>
            ))}
          </div>
        )}

        <div style={{
          display: 'flex', gap: '0.6rem',
          background: '#1a1915', border: '1px solid #2a2820',
          borderRadius: '10px', padding: '0.4rem 0.5rem',
        }}>
          <textarea
            ref={textareaRef}
            value={input}
            onChange={handleTextareaChange}
            onKeyDown={handleKeyDown}
            placeholder="고증이 필요한 장면이나 내용을 질문하세요…"
            rows={1}
            style={{
              flex: 1, background: 'none', border: 'none', outline: 'none',
              color: '#e8e2d9', fontSize: '0.9rem',
              padding: '0.5rem 0.625rem', resize: 'none',
              height: '44px', maxHeight: '140px',
              fontFamily: 'inherit', lineHeight: '1.55',
              overflowY: 'auto',
            }}
          />
          <button
            onClick={() => send()}
            disabled={loading || !input.trim()}
            style={{
              background: loading || !input.trim() ? '#2a2820' : '#c9a96e',
              color: loading || !input.trim() ? '#6b6456' : '#0f0e0c',
              border: 'none', borderRadius: '7px',
              padding: '0 1.125rem', cursor: loading || !input.trim() ? 'not-allowed' : 'pointer',
              fontWeight: '600', fontSize: '0.875rem',
              alignSelf: 'flex-end', height: '36px', marginBottom: '2px',
              transition: 'background 0.15s',
              flexShrink: 0,
            }}
          >
            전송
          </button>
        </div>
        <div style={{ color: '#252320', fontSize: '0.7rem', textAlign: 'center', marginTop: '0.4rem' }}>
          Enter 전송 · Shift+Enter 줄바꿈
        </div>
      </div>
    </div>
  )
}
