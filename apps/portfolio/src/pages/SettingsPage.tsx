import { useEffect, useState } from 'react'

type SettingsProps = {
  theme: 'dark' | 'light'
  setTheme: (theme: 'dark' | 'light') => void
}

export default function SettingsPage({ theme, setTheme }: SettingsProps) {
  const [fontSize, setFontSize] = useState(() => localStorage.getItem('mycmd-terminal-font') ?? '14')
  const [reducedMotion, setReducedMotion] = useState(() => localStorage.getItem('mycmd-reduced-motion') === 'true')

  useEffect(() => {
    localStorage.setItem('mycmd-terminal-font', fontSize)
  }, [fontSize])
  useEffect(() => {
    localStorage.setItem('mycmd-reduced-motion', String(reducedMotion))
    document.documentElement.dataset.motion = reducedMotion ? 'reduce' : 'no-preference'
  }, [reducedMotion])

  return (
    <section className="page" aria-labelledby="settings-heading">
      <p className="eyebrow">Preferences</p>
      <h1 id="settings-heading" tabIndex={-1}>Settings</h1>
      <form className="settings-form" onSubmit={(event) => event.preventDefault()}>
        <fieldset>
          <legend>Theme</legend>
          <label><input type="radio" name="theme" checked={theme === 'dark'} onChange={() => setTheme('dark')} /> Dark</label>
          <label><input type="radio" name="theme" checked={theme === 'light'} onChange={() => setTheme('light')} /> Light</label>
        </fieldset>
        <label>
          Terminal font size
          <input type="range" min="12" max="20" value={fontSize} onChange={(event) => setFontSize(event.target.value)} />
          <span>{fontSize}px</span>
        </label>
        <label>
          <input type="checkbox" checked={reducedMotion} onChange={(event) => setReducedMotion(event.target.checked)} />
          Reduce motion
        </label>
      </form>
    </section>
  )
}
