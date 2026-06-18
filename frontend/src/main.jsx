import React from 'react'
import ReactDOM from 'react-dom/client'
import 'leaflet/dist/leaflet.css'

const style = document.createElement('style')
style.textContent = `
  * { box-sizing: border-box; margin: 0; padding: 0; }
  body { background: #FAF5F1; color: #4c4145; font-family: 'Pretendard', -apple-system, sans-serif; }
  * { scrollbar-width: none; }
  *::-webkit-scrollbar { display: none; }
`
document.head.appendChild(style)
import { BrowserRouter, Routes, Route } from 'react-router-dom'
import App from './App'

ReactDOM.createRoot(document.getElementById('root')).render(
  <BrowserRouter>
    <Routes>
      <Route path="/*" element={<App />} />
    </Routes>
  </BrowserRouter>
)
