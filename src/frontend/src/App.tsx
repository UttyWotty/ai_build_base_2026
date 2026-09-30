// Root component: the router, the demo clock, and the shell around the five pages.
// Routes are plain paths so a page can be linked and reloaded directly; Firebase Hosting serves index.html for all of them.
// Data loading happens inside each page, never here.
import { BrowserRouter, Route, Routes } from 'react-router-dom'
import { Layout } from './components/Layout'
import { Approvals } from './pages/Approvals'
import { Copilot } from './pages/Copilot'
import { ControlRoom } from './pages/ControlRoom'
import { HowItWorks } from './pages/HowItWorks'
import { TrackRecord } from './pages/TrackRecord'
import { ClockProvider } from './state/clock'

export default function App() {
  return (
    <BrowserRouter>
      <ClockProvider>
        <Layout>
          <Routes>
            <Route path="/" element={<ControlRoom />} />
            <Route path="/copilot" element={<Copilot />} />
            <Route path="/approvals" element={<Approvals />} />
            <Route path="/track-record" element={<TrackRecord />} />
            <Route path="/how-it-works" element={<HowItWorks />} />
          </Routes>
        </Layout>
      </ClockProvider>
    </BrowserRouter>
  )
}
