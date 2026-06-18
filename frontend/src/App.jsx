import React, { useState } from 'react'
import ChatPage from './pages/ChatPage'
import IngestPage from './pages/IngestPage'

const NAV = [
  { id: 'chat', label: '고증 채팅' },
  { id: 'ingest', label: '자료 입력' },
]

function LogoIcon() {
  return (
    <div style={{
      width: 32, height: 32, borderRadius: 11,
      background: 'linear-gradient(135deg,#F3C3D0,#E79DB0)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      boxShadow: '0 4px 12px rgba(224,150,170,.30)',
      flexShrink: 0,
    }}>
      <div style={{
        width: 13, height: 13, background: '#fff',
        clipPath: 'polygon(50% 0%,61% 39%,100% 50%,61% 61%,50% 100%,39% 61%,0% 50%,39% 39%)',
        opacity: 0.92,
      }} />
    </div>
  )
}

export default function App() {
  const [tab, setTab] = useState('chat')

  return (
    <div style={{ minHeight: '100vh', background: '#FAF5F1', display: 'flex', flexDirection: 'column' }}>
      <header style={{
        flexShrink: 0,
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '0 44px', height: 65,
        borderBottom: '1px solid #EFE2DF',
        background: 'rgba(250,245,241,.85)',
        backdropFilter: 'blur(8px)',
        WebkitBackdropFilter: 'blur(8px)',
        position: 'sticky', top: 0, zIndex: 10,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <LogoIcon />
          <span style={{ fontSize: 18, fontWeight: 700, color: '#C16A82', letterSpacing: '-0.01em' }}>
            근현대사 고증 AI
          </span>
        </div>
        <nav style={{ display: 'flex', gap: 4, alignItems: 'center' }}>
          {NAV.map(n => (
            <button
              key={n.id}
              onClick={() => setTab(n.id)}
              style={{
                background: tab === n.id ? '#FBE7EC' : 'transparent',
                border: 'none',
                color: tab === n.id ? '#C16A82' : '#A99B9E',
                fontWeight: tab === n.id ? 700 : 500,
                fontSize: 14,
                padding: '8px 18px',
                borderRadius: 999,
                cursor: 'pointer',
                fontFamily: 'inherit',
                transition: 'all 0.15s',
                lineHeight: 1,
                display: 'inline-flex',
                alignItems: 'center',
              }}
            >
              {n.label}
            </button>
          ))}
        </nav>
      </header>

      <div style={{
        maxWidth: 880, margin: '0 auto',
        padding: tab === 'chat' ? '0 44px' : '2rem 44px',
        width: '100%', flex: 1,
        display: 'flex', flexDirection: 'column',
        boxSizing: 'border-box',
      }}>
        {tab === 'chat' && <ChatPage />}
        {tab === 'ingest' && <IngestPage />}
      </div>
    </div>
  )
}
