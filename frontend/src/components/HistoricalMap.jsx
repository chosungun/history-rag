import React, { useEffect } from 'react'
import { MapContainer, TileLayer, Marker, Popup, useMap } from 'react-leaflet'
import L from 'leaflet'

// Leaflet 기본 마커 아이콘 경로 수동 설정 (Vite 번들러 호환)
delete L.Icon.Default.prototype._getIconUrl
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon-2x.png',
  iconUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-icon.png',
  shadowUrl: 'https://unpkg.com/leaflet@1.9.4/dist/images/marker-shadow.png',
})

function Recenter({ lat, lng }) {
  const map = useMap()
  useEffect(() => { map.setView([lat, lng]) }, [lat, lng, map])
  return null
}

export default function HistoricalMap({ lat, lng, label }) {
  return (
    <div style={{ marginTop: 16, border: '1px solid #ECDDDF', borderRadius: 14, overflow: 'hidden' }}>
      <div style={{
        display: 'flex', alignItems: 'center', justifyContent: 'space-between',
        padding: '12px 16px', borderBottom: '1px solid #F1E4E1',
      }}>
        <span style={{ fontSize: 13, fontWeight: 700, color: '#574349' }}>경성 역사지도</span>
        <a
          href="https://hgis.history.go.kr/"
          target="_blank" rel="noreferrer"
          style={{ fontSize: 12, color: '#C16A82', fontWeight: 600, textDecoration: 'none' }}
        >
          국사편찬위원회 역사지리정보 ↗
        </a>
      </div>
      <MapContainer
        center={[lat, lng]}
        zoom={16}
        style={{ height: '280px' }}
        zoomControl={true}
        attributionControl={false}
      >
        <TileLayer
          url="/api/map/tile/map1919/{z}/{x}/{y}"
          attribution="국사편찬위원회 역사지리정보"
          maxZoom={19}
          errorTileUrl=""
        />
        <Marker position={[lat, lng]}>
          {label && <Popup>{label}</Popup>}
        </Marker>
        <Recenter lat={lat} lng={lng} />
      </MapContainer>
    </div>
  )
}
