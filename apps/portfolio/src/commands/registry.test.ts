import { describe, expect, it } from 'vitest'
import { executeCommand } from './registry'
import { parseCommand } from './parser'

function run(input: string) {
  const parsed = parseCommand(input)
  if (!parsed.ok) return { lines: [parsed.error] }
  return executeCommand(parsed.command)
}

describe('allowlisted portfolio registry', () => {
  it('rejects operating-system commands', () => {
    expect(run('ls')).toEqual({
      lines: ['Command not supported in portfolio mode. Type help to see available commands.'],
    })
  })
  it('returns project detail for a valid public slug', () => {
    expect(run('project mycmd-cli').lines.join('\n')).toContain('MYCMD CLI')
  })
  it('rejects unknown project flags', () => {
    expect(run('projects --status=unknown').lines.join(' ')).toContain('Invalid project status')
  })
  it('does not configure a resume', () => {
    expect(run('resume').lines.join(' ')).toContain('No approved resume')
  })
  it('does not expose shell identities', () => {
    expect(run('whoami').lines.join(' ')).toContain('No operating-system identity')
  })
  it('rejects extra positional arguments', () => {
    expect(run('about extra').lines.join(' ')).toContain('Usage:')
    expect(run('projects unexpected').lines.join(' ')).toContain('Unknown positional')
    expect(run('theme dark extra').lines.join(' ')).toContain('Usage:')
  })
})
