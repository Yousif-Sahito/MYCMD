import { describe, expect, it } from 'vitest'
import { parseCommand } from './parser'

describe('portfolio command parser', () => {
  it('parses commands and simple flags', () => {
    expect(parseCommand('projects --status completed')).toEqual({
      ok: true,
      command: { name: 'projects', args: [], flags: { status: 'completed' } },
    })
  })
  it('parses quoted arguments', () => {
    expect(parseCommand('project "mycmd portfolio"')).toMatchObject({
      ok: true,
      command: { name: 'project', args: ['mycmd portfolio'], flags: {} },
    })
  })
  it('rejects malformed quotes', () => {
    expect(parseCommand('project "open')).toEqual({
      ok: false,
      error: 'Malformed quote: close the quoted argument.',
    })
  })
  it('rejects shell operators', () => {
    expect(parseCommand('ls | cat')).toMatchObject({ ok: false })
    expect(parseCommand('echo $(whoami)')).toMatchObject({ ok: false })
  })
  it('returns empty input safely', () => {
    expect(parseCommand('   ').toString()).not.toContain('ls')
  })
})
