import { useEffect, useRef, useState } from 'react'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import { executeCommand, commandRegistry } from '../commands/registry'
import { parseCommand } from '../commands/parser'
import { safeUrl } from '../data/publicDataSchema'

type TerminalPageProps = {
  theme: 'dark' | 'light'
  setTheme: (theme: 'dark' | 'light') => void
}

export default function TerminalPage({ theme, setTheme }: TerminalPageProps) {
  const hostRef = useRef<HTMLDivElement>(null)
  const terminalRef = useRef<Terminal | null>(null)
  const inputRef = useRef('')
  const historyIndexRef = useRef(-1)
  const historyRef = useRef<string[]>([])
  const [fallbackOutput, setFallbackOutput] = useState<string[]>([
    'MYCMD Portfolio Terminal',
    'This is a restricted public portfolio interface, not an operating-system shell.',
  ])
  const [fallbackInput, setFallbackInput] = useState('')

  const execute = (raw: string): boolean => {
    const parsed = parseCommand(raw)
    if (!parsed.ok) {
      writeLines([parsed.error])
      setFallbackOutput((output) => [...output, `$ ${raw}`, parsed.error].slice(-1000))
      return true
    }
    if (!parsed.command.name) return true
    const next = [...historyRef.current.filter((item) => item !== raw), raw].slice(-100)
    historyRef.current = next
    if (parsed.command.name === 'history') {
      const lines = historyRef.current.length ? historyRef.current : ['No commands in this browser session.']
      writeLines(lines)
      setFallbackOutput((output) => [...output, `$ ${raw}`, ...lines].slice(-1000))
      return true
    }
    const result = executeCommand(parsed.command)
    if (result.action === 'clear') {
      terminalRef.current?.clear()
      setFallbackOutput([])
      return true
    }
    if (result.action === 'theme-dark') setTheme('dark')
    if (result.action === 'theme-light') setTheme('light')
    if (result.action === 'open' && result.openUrl) {
      const url = safeUrl(result.openUrl)
      if (url) window.open(url, '_blank', 'noopener,noreferrer')
    }
    writeLines(result.lines)
    setFallbackOutput((output) => [...output, `$ ${raw}`, ...result.lines].slice(-1000))
    return true
  }

  const writePrompt = () => {
    terminalRef.current?.write('\r\nmycmd> ')
  }

  const writeLines = (lines: string[]) => {
    const terminal = terminalRef.current
    if (!terminal) return
    for (const line of lines) terminal.writeln(`\r\n${line}`)
  }

  useEffect(() => {
    if (!hostRef.current) return
    const terminal = new Terminal({
      cursorBlink: true,
      convertEol: true,
      fontSize: Number(localStorage.getItem('mycmd-terminal-font') ?? '14'),
      scrollback: 1000,
      theme: theme === 'dark'
        ? { background: '#0b1324', foreground: '#e8edf7', cursor: '#7dd3fc' }
        : { background: '#f7f9fc', foreground: '#172033', cursor: '#1d4ed8' },
    })
    const fit = new FitAddon()
    terminal.loadAddon(fit)
    terminal.open(hostRef.current)
    fit.fit()
    terminalRef.current = terminal
    terminal.writeln('MYCMD Portfolio Terminal')
    terminal.writeln('Restricted browser commands only. Type help.')
    terminal.write('mycmd> ')

    const onData = (data: string) => {
      if (data === '\r') {
        const raw = inputRef.current
        terminal.write('\r')
        execute(raw)
        inputRef.current = ''
        historyIndexRef.current = -1
        writePrompt()
      } else if (data === '\u007f') {
        if (inputRef.current) {
          inputRef.current = inputRef.current.slice(0, -1)
          terminal.write('\b \b')
        }
      } else if (data === '\u001b[A') {
        if (historyRef.current.length) {
          historyIndexRef.current = Math.min(historyIndexRef.current + 1, historyRef.current.length - 1)
          replaceInput(historyRef.current[historyRef.current.length - 1 - historyIndexRef.current] ?? '')
        }
      } else if (data === '\u001b[B') {
        if (historyIndexRef.current > 0) {
          historyIndexRef.current -= 1
          replaceInput(historyRef.current[historyRef.current.length - 1 - historyIndexRef.current] ?? '')
        } else {
          historyIndexRef.current = -1
          replaceInput('')
        }
      } else if (data === '\t') {
        const prefix = inputRef.current
        const suggestion = Object.keys(commandRegistry).find((name) => name.startsWith(prefix))
        if (suggestion) replaceInput(suggestion)
      } else if (data === '\u0003') {
        terminal.write('^C')
        inputRef.current = ''
        writePrompt()
      } else if (data === '\u000c') {
        terminal.clear()
      } else if (data.length === 1 && data >= ' ') {
        inputRef.current += data
        terminal.write(data)
      } else if (data.length > 1 && !data.startsWith('\u001b')) {
        inputRef.current += data
        terminal.write(data)
      }
    }

    const replaceInput = (value: string) => {
      while (inputRef.current.length) {
        terminal.write('\b \b')
        inputRef.current = inputRef.current.slice(0, -1)
      }
      inputRef.current = value
      terminal.write(value)
    }

    const disposable = terminal.onData(onData)
    const resize = () => fit.fit()
    window.addEventListener('resize', resize)
    return () => {
      window.removeEventListener('resize', resize)
      disposable.dispose()
      terminal.dispose()
      terminalRef.current = null
    }
    // The terminal is intentionally recreated only when theme changes.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [theme])

  const runFallback = () => {
    const raw = fallbackInput.trim()
    if (!raw) return
    execute(raw)
    setFallbackInput('')
  }

  return (
    <section className="page terminal-page" aria-labelledby="terminal-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Restricted browser interface</p>
          <h1 id="terminal-heading" tabIndex={-1}>MYCMD Portfolio Terminal</h1>
        </div>
      </div>
      <p className="terminal-notice" id="terminal-instructions">
        This terminal displays public portfolio data only. It does not execute operating-system commands.
      </p>
      <div ref={hostRef} className="xterm-host" role="application" aria-label="Interactive portfolio terminal" aria-describedby="terminal-instructions" />
      <div className="mobile-terminal" aria-label="Accessible terminal fallback">
        <label htmlFor="terminal-command">Enter a portfolio command</label>
        <div className="mobile-terminal-row">
          <input
            id="terminal-command"
            value={fallbackInput}
            onChange={(event) => setFallbackInput(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === 'Enter') runFallback()
            }}
            placeholder="help"
            list="command-suggestions"
          />
          <datalist id="command-suggestions">
            {Object.keys(commandRegistry).map((name) => <option key={name} value={name} />)}
          </datalist>
          <button type="button" onClick={runFallback}>Execute</button>
        </div>
        <div className="terminal-output" aria-live="polite" aria-label="Terminal output">
          {fallbackOutput.map((line, index) => <div key={`${line}-${index}`}>{line}</div>)}
        </div>
        <button type="button" onClick={() => setFallbackOutput([])}>Clear output</button>
      </div>
    </section>
  )
}
