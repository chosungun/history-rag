import React, { useState } from 'react'
import SearchPage from './pages/SearchPage'
import PhotosPage from './pages/PhotosPage'
import IngestPage from './pages/IngestPage'

const NAV = [
  { id: 'search', label: '🔍 고증 검색' },
  { id: 'photos', label: '📸 사진 자료' },
  { id: 'ingest', label: '📥 자료 수집' },
]

const styles = {
  wrap: { minHeight: '100vh', background: '#0f0e0c' },
  header: {
    borderBottom: '1px solid #2a2820',
    padding: '0 2rem',
    display: 'flex',
    alignItems: 'center',
    gap: '2rem',
    background: '#0f0e0c',
    position: 'sticky',
    top: 0,
    zIndex: 10,
  },
  logo: {
    fontSize: '1rem',
    fontWeight: '600',
    color: '#c9a96e',
    letterSpacing: '0.05em',
    padding: '1.2rem 0',
    whiteSpace: 'nowrap',
  },
  nav: { display: 'flex', gap: '0', marginLeft: 'auto' },
  navBtn: (active) => ({
    background: 'none',
    border: 'none',
    color: active ? '#c9a96e' : '#6b6456',
    cursor: 'pointer',
    padding: '1.2rem 1rem',
    fontSize: '0.875rem',
    fontWeight: active ? '600' : '400',
    borderBottom: active ? '2px solid #c9a96e' : '2px solid transparent',
    transition: 'color 0.15s',
    whiteSpace: 'nowrap',
  }),
  main: { maxWidth: '1100px', margin: '0 auto', padding: '2rem' },
}

export default function App() {
  const [tab, setTab] = useState('search')

  return (
    <div style={styles.wrap}>
      <header style={styles.header}>
        <span style={styles.logo}>근현대사 고증 AI</span>
        <nav style={styles.nav}>
          {NAV.map(n => (
            <button key={n.id} style={styles.navBtn(tab === n.id)} onClick={() => setTab(n.id)}>
              {n.label}
            </button>
          ))}
        </nav>
      </header>
      <main style={styles.main}>
        {tab === 'search' && <SearchPage />}
        {tab === 'photos' && <PhotosPage />}
        {tab === 'ingest' && <IngestPage />}
      </main>
    </div>
  )
}
