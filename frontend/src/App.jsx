import React, { useState } from 'react'
import ChatPage from './pages/ChatPage'
import IngestPage from './pages/IngestPage'

const NAV = [
  { id: 'chat', label: '고증 채팅' },
  { id: 'ingest', label: '자료 입력' },
]

const S = {
  wrap: { minHeight: '100vh', background: '#0f0e0c', display: 'flex', flexDirection: 'column' },
  header: {
    borderBottom: '1px solid #1e1d19',
    padding: '0 2rem',
    display: 'flex',
    alignItems: 'center',
    gap: '2rem',
    background: '#0f0e0c',
    position: 'sticky',
    top: 0,
    zIndex: 10,
    flexShrink: 0,
  },
  logo: {
    fontSize: '0.9rem',
    fontWeight: '600',
    color: '#c9a96e',
    letterSpacing: '0.08em',
    padding: '1.1rem 0',
    whiteSpace: 'nowrap',
  },
  nav: { display: 'flex', gap: '0', marginLeft: 'auto' },
  navBtn: active => ({
    background: 'none',
    border: 'none',
    color: active ? '#c9a96e' : '#6b6456',
    cursor: 'pointer',
    padding: '1.1rem 0.875rem',
    fontSize: '0.82rem',
    fontWeight: active ? '600' : '400',
    borderBottom: active ? '2px solid #c9a96e' : '2px solid transparent',
    transition: 'color 0.15s',
    whiteSpace: 'nowrap',
  }),
  main: { maxWidth: '820px', margin: '0 auto', padding: '0 2rem', width: '100%', flex: 1 },
  mainIngest: { maxWidth: '820px', margin: '0 auto', padding: '2rem', width: '100%', flex: 1 },
}

export default function App() {
  const [tab, setTab] = useState('chat')

  return (
    <div style={S.wrap}>
      <header style={S.header}>
        <span style={S.logo}>근현대사 고증 AI</span>
        <nav style={S.nav}>
          {NAV.map(n => (
            <button key={n.id} style={S.navBtn(tab === n.id)} onClick={() => setTab(n.id)}>
              {n.label}
            </button>
          ))}
        </nav>
      </header>

      <div style={tab === 'chat' ? S.main : S.mainIngest}>
        {tab === 'chat' && <ChatPage />}
        {tab === 'ingest' && <IngestPage />}
      </div>
    </div>
  )
}
