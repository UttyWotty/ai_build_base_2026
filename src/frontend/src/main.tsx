// Entry point of the frontend: mounts the App into the page's root element with React's strict mode.
// Global styles (Tailwind and the theme tokens) load here once.
// Nothing else belongs in this file.
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import App from './App.tsx'
import './index.css'

createRoot(document.getElementById('root')!).render(
  <StrictMode>
    <App />
  </StrictMode>,
)
