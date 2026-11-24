import { lazy, Suspense, useEffect, useState } from 'react'
import { BrowserRouter, NavLink, Route, Routes, useLocation } from 'react-router-dom'
import HomePage from './pages/HomePage'
import ProjectsPage from './pages/ProjectsPage'
import ProjectDetailPage from './pages/ProjectDetailPage'
import SkillsPage from './pages/SkillsPage'
import EducationPage from './pages/EducationPage'
import CertificatesPage from './pages/CertificatesPage'
import MilestonesPage from './pages/MilestonesPage'
import AboutPage from './pages/AboutPage'
import ContactPage from './pages/ContactPage'
import SettingsPage from './pages/SettingsPage'
import NotFoundPage from './pages/NotFoundPage'

const TerminalPage = lazy(() => import('./pages/TerminalPage'))

const navItems = [
  ['/', 'Home'],
  ['/terminal', 'Terminal'],
  ['/projects', 'Projects'],
  ['/skills', 'Skills'],
  ['/education', 'Education'],
  ['/certificates', 'Certificates'],
  ['/milestones', 'Milestones'],
  ['/about', 'About'],
  ['/contact', 'Contact'],
  ['/settings', 'Settings'],
] as const

function RouteFocus() {
  const location = useLocation()
  useEffect(() => {
    document.querySelector<HTMLElement>('main h1')?.focus()
  }, [location.pathname])
  return null
}

export default function App() {
  const [theme, setTheme] = useState<'dark' | 'light'>(() => {
    const saved = localStorage.getItem('mycmd-theme')
    if (saved === 'dark' || saved === 'light') return saved
    return window.matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'
  })

  useEffect(() => {
    document.documentElement.dataset.theme = theme
    localStorage.setItem('mycmd-theme', theme)
  }, [theme])
  const [offline, setOffline] = useState(() => !navigator.onLine)
  useEffect(() => {
    const handleOnline = () => setOffline(false)
    const handleOffline = () => setOffline(true)
    window.addEventListener('online', handleOnline)
    window.addEventListener('offline', handleOffline)
    return () => {
      window.removeEventListener('online', handleOnline)
      window.removeEventListener('offline', handleOffline)
    }
  }, [])

  return (
    <BrowserRouter>
      <RouteFocus />
      <a className="skip-link" href="#main-content">Skip to main content</a>
      {offline && <div className="offline-banner" role="status">Offline: bundled public content remains available.</div>}
      <header className="site-header">
        <NavLink className="brand" to="/">
          <span className="brand-mark">M</span>
          <span>MYCMD</span>
        </NavLink>
        <nav aria-label="Main navigation" className="main-nav">
          {navItems.map(([href, label]) => (
            <NavLink key={href} to={href} end={href === '/'} className={({ isActive }) => isActive ? 'active' : ''}>
              {label}
            </NavLink>
          ))}
        </nav>
        <button className="theme-toggle" type="button" onClick={() => setTheme(theme === 'dark' ? 'light' : 'dark')}>
          {theme === 'dark' ? 'Light theme' : 'Dark theme'}
        </button>
      </header>
      <main id="main-content">
        <Routes>
          <Route path="/" element={<HomePage />} />
          <Route path="/terminal" element={<Suspense fallback={<p role="status">Loading terminal…</p>}><TerminalPage theme={theme} setTheme={setTheme} /></Suspense>} />
          <Route path="/projects" element={<ProjectsPage />} />
          <Route path="/projects/:slug" element={<ProjectDetailPage />} />
          <Route path="/skills" element={<SkillsPage />} />
          <Route path="/education" element={<EducationPage />} />
          <Route path="/certificates" element={<CertificatesPage />} />
          <Route path="/milestones" element={<MilestonesPage />} />
          <Route path="/experience" element={<MilestonesPage />} />
          <Route path="/about" element={<AboutPage />} />
          <Route path="/contact" element={<ContactPage />} />
          <Route path="/settings" element={<SettingsPage theme={theme} setTheme={setTheme} />} />
          <Route path="*" element={<NotFoundPage />} />
        </Routes>
      </main>
      <footer>
        <span>MYCMD Public Portfolio</span>
        <a href="https://github.com/Yousif-Sahito/MYCMD" rel="noreferrer">Source</a>
      </footer>
    </BrowserRouter>
  )
}
