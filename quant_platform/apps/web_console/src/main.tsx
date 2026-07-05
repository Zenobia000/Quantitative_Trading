import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import '@/i18n' // i18n init (side-effect) before render
import App from './App'
import './styles/index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
