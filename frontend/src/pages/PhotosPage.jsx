import React, { useState } from 'react'

const S = {
  header: { marginBottom: '1.5rem' },
  title: { fontSize: '1.25rem', fontWeight: '500', color: '#e8e2d9', marginBottom: '0.35rem' },
  sub: { color: '#6b6456', fontSize: '0.8rem' },
  searchRow: { display: 'flex', gap: '0.75rem', marginBottom: '1.5rem' },
  input: {
    flex: 1, background: '#1a1915', border: '1px solid #2a2820',
    borderRadius: '6px', outline: 'none', color: '#e8e2d9',
    fontSize: '0.9rem', padding: '0.6rem 1rem',
  },
  btn: {
    background: '#c9a96e', color: '#0f0e0c', border: 'none',
    borderRadius: '6px', padding: '0.6rem 1.25rem',
    cursor: 'pointer', fontWeight: '600', fontSize: '0.875rem',
  },
  tags: { display: 'flex', gap: '0.5rem', flexWrap: 'wrap', marginBottom: '1.5rem' },
  tag: {
    background: 'none', border: '1px solid #2a2820', color: '#6b6456',
    borderRadius: '20px', padding: '0.25rem 0.75rem',
    cursor: 'pointer', fontSize: '0.8rem',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
    gap: '1rem',
  },
  card: {
    background: '#1a1915', border: '1px solid #2a2820',
    borderRadius: '8px', overflow: 'hidden', cursor: 'pointer',
    transition: 'border-color 0.15s',
  },
  imgWrap: { width: '100%', height: '160px', background: '#111', overflow: 'hidden' },
  img: { width: '100%', height: '100%', objectFit: 'cover' },
  cardBody: { padding: '0.75rem' },
  cardTitle: { color: '#e8e2d9', fontSize: '0.8rem', fontWeight: '500', marginBottom: '0.25rem', lineHeight: '1.4' },
  cardMeta: { color: '#4a4540', fontSize: '0.75rem' },
  license: { color: '#4a7c4a', fontSize: '0.7rem', marginTop: '0.25rem' },
  empty: { color: '#4a4540', textAlign: 'center', padding: '4rem 0', fontSize: '0.9rem' },
  modal: {
    position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.85)',
    display: 'flex', alignItems: 'center', justifyContent: 'center',
    zIndex: 100, padding: '2rem',
  },
  modalInner: {
    background: '#1a1915', border: '1px solid #2a2820',
    borderRadius: '12px', maxWidth: '700px', width: '100%',
    overflow: 'hidden',
  },
  modalImg: { width: '100%', maxHeight: '450px', objectFit: 'contain', background: '#111' },
  modalBody: { padding: '1.25rem' },
  modalTitle: { color: '#e8e2d9', fontWeight: '600', marginBottom: '0.5rem' },
  modalMeta: { color: '#6b6456', fontSize: '0.85rem', lineHeight: '1.8' },
  closeBtn: {
    background: 'none', border: '1px solid #2a2820', color: '#6b6456',
    borderRadius: '6px', padding: '0.5rem 1rem', cursor: 'pointer',
    marginTop: '1rem', fontSize: '0.85rem',
  },
  linkBtn: {
    display: 'inline-block', color: '#c9a96e', fontSize: '0.85rem',
    marginTop: '0.5rem',
  },
}

const QUICK_TAGS = ['경성', '조선풍속', '1920년대', '농촌', '기차', '시장', '의복']

export default function PhotosPage() {
  const [keyword, setKeyword] = useState('경성')
  const [photos, setPhotos] = useState([])
  const [loading, setLoading] = useState(false)
  const [selected, setSelected] = useState(null)

  const search = async (kw = keyword) => {
    setLoading(true)
    try {
      const res = await fetch(`/api/photos?keyword=${encodeURIComponent(kw)}&page=1`)
      const data = await res.json()
      setPhotos(data.photos || [])
    } catch {
      setPhotos([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <div>
      <div style={S.header}>
        <h2 style={S.title}>사진 자료 검색</h2>
        <p style={S.sub}>공유마당(한국저작권위원회) — CC 라이선스 무료 사진</p>
      </div>

      <div style={S.searchRow}>
        <input
          style={S.input} value={keyword}
          onChange={e => setKeyword(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && search()}
          placeholder="검색어 입력 (예: 경성, 조선풍속)"
        />
        <button style={S.btn} onClick={() => search()}>{loading ? '검색 중...' : '검색'}</button>
      </div>

      <div style={S.tags}>
        {QUICK_TAGS.map(t => (
          <button key={t} style={S.tag} onClick={() => { setKeyword(t); search(t) }}>{t}</button>
        ))}
      </div>

      {photos.length === 0 && !loading && (
        <div style={S.empty}>검색어를 입력하고 사진을 찾아보세요</div>
      )}

      <div style={S.grid}>
        {photos.map(p => (
          <div key={p.id} style={S.card} onClick={() => setSelected(p)}>
            <div style={S.imgWrap}>
              {p.thumbnail
                ? <img src={p.thumbnail} alt={p.title} style={S.img} onError={e => e.target.style.display='none'} />
                : <div style={{...S.img, display:'flex', alignItems:'center', justifyContent:'center', color:'#2a2820', fontSize:'2rem'}}>📷</div>
              }
            </div>
            <div style={S.cardBody}>
              <div style={S.cardTitle}>{p.title || '제목 없음'}</div>
              <div style={S.cardMeta}>{p.source} {p.year && `· ${p.year}`}</div>
              <div style={S.license}>{p.license}</div>
            </div>
          </div>
        ))}
      </div>

      {selected && (
        <div style={S.modal} onClick={() => setSelected(null)}>
          <div style={S.modalInner} onClick={e => e.stopPropagation()}>
            {selected.original && (
              <img src={selected.original || selected.thumbnail} alt={selected.title} style={S.modalImg} />
            )}
            <div style={S.modalBody}>
              <div style={S.modalTitle}>{selected.title}</div>
              <div style={S.modalMeta}>
                출처: {selected.source}<br />
                연도: {selected.year || '미상'}<br />
                라이선스: {selected.license}
              </div>
              {selected.url && (
                <a href={selected.url} target="_blank" rel="noreferrer" style={S.linkBtn}>
                  원본 페이지에서 다운로드 →
                </a>
              )}
              <br />
              <button style={S.closeBtn} onClick={() => setSelected(null)}>닫기</button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
