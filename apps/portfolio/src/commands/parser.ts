export type ParsedCommand = {
  name: string
  args: string[]
  flags: Record<string, string | boolean>
}

export type ParseResult =
  | { ok: true; command: ParsedCommand }
  | { ok: false; error: string }

const forbiddenOperators = /([;&|<>`]|\$\(|\$\{|\n|\r)/

export function parseCommand(input: string): ParseResult {
  const trimmed = input.trim()
  if (!trimmed) return { ok: true, command: { name: '', args: [], flags: {} } }
  if (forbiddenOperators.test(trimmed)) {
    return { ok: false, error: 'Shell syntax is not supported in portfolio mode.' }
  }

  const tokens: string[] = []
  let current = ''
  let quote: '"' | "'" | null = null
  for (let index = 0; index < trimmed.length; index += 1) {
    const char = trimmed[index] ?? ''
    if (quote) {
      if (char === quote) quote = null
      else current += char
      continue
    }
    if (char === '"' || char === "'") {
      quote = char
    } else if (/\s/.test(char)) {
      if (current) {
        tokens.push(current)
        current = ''
      }
    } else {
      current += char
    }
  }
  if (quote) return { ok: false, error: 'Malformed quote: close the quoted argument.' }
  if (current) tokens.push(current)
  if (!tokens.length) return { ok: true, command: { name: '', args: [], flags: {} } }

  const [name = '', ...rest] = tokens
  const args: string[] = []
  const flags: Record<string, string | boolean> = {}
  for (let index = 0; index < rest.length; index += 1) {
    const token = rest[index] ?? ''
    if (!token.startsWith('--')) {
      args.push(token)
      continue
    }
    const flag = token.slice(2)
    if (!flag) return { ok: false, error: 'Unknown empty flag.' }
    const equals = flag.indexOf('=')
    if (equals >= 0) {
      flags[flag.slice(0, equals)] = flag.slice(equals + 1)
    } else {
      const next = rest[index + 1]
      if (next && !next.startsWith('--')) {
        flags[flag] = next
        index += 1
      } else {
        flags[flag] = true
      }
    }
  }
  return { ok: true, command: { name: name.toLowerCase(), args, flags } }
}
