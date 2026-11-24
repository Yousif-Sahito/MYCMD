import type { ParsedCommand } from './parser'
import { certificates, education, milestones, profile, projects, skillCategories } from '../data/portfolio'
import { safeUrl } from '../data/publicDataSchema'

export type CommandResult = {
  lines: string[]
  links?: { label: string; href: string }[]
  action?: 'clear' | 'theme-dark' | 'theme-light' | 'open'
  openUrl?: string
}

export type CommandDefinition = {
  name: string
  description: string
  usage: string
  execute: (command: ParsedCommand) => CommandResult
}

const unsupported = (): CommandResult => ({
  lines: ['Command not supported in portfolio mode. Type help to see available commands.'],
})

const projectStatus = (status: string): string => status[0]?.toUpperCase() + status.slice(1)

export const commandRegistry: Record<string, CommandDefinition> = {
  help: {
    name: 'help',
    description: 'Show available portfolio commands',
    usage: 'help',
    execute: () => ({
      lines: [
        'MYCMD Portfolio Terminal',
        ...Object.values(commandRegistry).map((command) => `  ${command.usage.padEnd(24)} ${command.description}`),
      ],
    }),
  },
  about: {
    name: 'about',
    description: 'Display the public profile',
    usage: 'about',
    execute: () => ({ lines: [profile.name, profile.heading, '', profile.introduction] }),
  },
  projects: {
    name: 'projects',
    description: 'List public projects',
    usage: 'projects [--status active|completed|planned]',
    execute: (command) => {
      if (command.args.length) {
        return { lines: ['Unknown positional argument. Usage: projects [--status active|completed|planned]'] }
      }
      const status = command.flags.status
      if (Object.keys(command.flags).some((flag) => flag !== 'status')) {
        return { lines: ['Unknown flag. Usage: projects [--status active|completed|planned]'] }
      }
      if (typeof status !== 'string' && status !== undefined) return unsupported()
      const allowed = ['active', 'completed', 'planned']
      if (status && !allowed.includes(status)) return { lines: ['Invalid project status. Use active, completed or planned.'] }
      const list = status ? projects.filter((project) => project.status === status) : projects
      return {
        lines: list.length
          ? list.flatMap((project) => [`${project.title} (${projectStatus(project.status)})`, `  /projects/${project.slug}`, `  ${project.summary}`])
          : ['No public projects match that status.'],
      }
    },
  },
  project: {
    name: 'project',
    description: 'Show a public project detail',
    usage: 'project <slug>',
    execute: (command) => {
      if (!command.args[0]) return { lines: ['Usage: project <slug>'] }
      if (command.args.length !== 1) return { lines: ['Usage: project <slug>'] }
      const project = projects.find((item) => item.slug === command.args[0])
      if (!project) return { lines: ['Project not found. Use projects to list available slugs.'] }
      return {
        lines: [
          project.title,
          `${projectStatus(project.status)} | ${project.technologies.join(', ')}`,
          project.description,
          `Route: /projects/${project.slug}`,
        ],
      }
    },
  },
  skills: {
    name: 'skills',
    description: 'Display public skill categories',
    usage: 'skills',
    execute: () => ({
      lines: skillCategories.flatMap((category) => [
        category.name,
        `  ${category.skills.join(', ')}`,
        `  ${category.description}`,
      ]),
    }),
  },
  education: {
    name: 'education',
    description: 'Display approved education',
    usage: 'education',
    execute: () => ({
      lines: education.length
        ? education.flatMap((item) => [`${item.institution} - ${item.program}`, `  ${item.period}`, `  ${item.description}`])
        : ['No public education information is currently configured.'],
    }),
  },
  certificates: {
    name: 'certificates',
    description: 'Display approved certificates',
    usage: 'certificates',
    execute: () => ({
      lines: certificates.length
        ? certificates.flatMap((item) => [`${item.name} - ${item.issuer}`, `  ${item.issuedAt}`, `  ${item.description}`])
        : ['No public certificates are currently configured.'],
    }),
  },
  milestones: {
    name: 'milestones',
    description: 'Display public milestones',
    usage: 'milestones',
    execute: () => ({
      lines: milestones.flatMap((item) => [
        `${item.title} (${projectStatus(item.status)})`,
        `  ${item.organization} | ${item.period}`,
        `  ${item.summary}`,
      ]),
    }),
  },
  experience: {
    name: 'experience',
    description: 'Display public experience',
    usage: 'experience',
    execute: () => ({
      lines: ['No public employment experience is currently configured.', 'Verified MYCMD milestones are available through the milestones command.'],
    }),
  },
  contact: {
    name: 'contact',
    description: 'Display approved contact methods',
    usage: 'contact',
    execute: () => ({
      lines: [profile.contactLabel, profile.contactUrl],
      links: [{ label: profile.contactLabel, href: profile.contactUrl }],
    }),
  },
  resume: {
    name: 'resume',
    description: 'Open the configured resume',
    usage: 'resume',
    execute: () => {
      const url = safeUrl(profile.resumeUrl ?? undefined)
      return url
        ? { lines: ['Opening the configured resume.'], action: 'open', openUrl: url }
        : { lines: ['No approved resume is currently configured.'] }
    },
  },
  github: {
    name: 'github',
    description: 'Open the approved GitHub profile',
    usage: 'github',
    execute: () => {
      const url = safeUrl(profile.github)
      return url
        ? { lines: ['Opening MYCMD GitHub.'], action: 'open', openUrl: url }
        : { lines: ['No approved GitHub URL is currently configured.'] }
    },
  },
  linkedin: {
    name: 'linkedin',
    description: 'Open approved LinkedIn profile',
    usage: 'linkedin',
    execute: () => {
      const url = safeUrl(profile.linkedinUrl ?? undefined)
      return url
        ? { lines: ['Opening LinkedIn.'], action: 'open', openUrl: url }
        : { lines: ['No approved LinkedIn URL is currently configured.'] }
    },
  },
  theme: {
    name: 'theme',
    description: 'Switch dark or light theme',
    usage: 'theme [dark|light]',
    execute: (command) => {
      if (command.args.length !== (command.args[0] ? 1 : 0) || command.args.length > 1) {
        return { lines: ['Usage: theme dark | theme light'] }
      }
      const theme = command.args[0]
      if (!theme) return { lines: ['Usage: theme dark | theme light'] }
      if (theme !== 'dark' && theme !== 'light') return { lines: ['Theme must be dark or light.'] }
      return { lines: [`Switched to ${theme} theme.`], action: theme === 'dark' ? 'theme-dark' : 'theme-light' }
    },
  },
  clear: {
    name: 'clear',
    description: 'Clear terminal view',
    usage: 'clear',
    execute: () => ({ lines: [], action: 'clear' }),
  },
  history: {
    name: 'history',
    description: 'Show current browser-session history',
    usage: 'history',
    execute: () => unsupported(),
  },
  whoami: {
    name: 'whoami',
    description: 'Explain the public portfolio identity',
    usage: 'whoami',
    execute: () => ({ lines: ['MYCMD public portfolio - a curated software portfolio interface. No operating-system identity is available here.'] }),
  },
  date: {
    name: 'date',
    description: 'Show browser-local date and time',
    usage: 'date',
    execute: () => ({ lines: [new Date().toLocaleString()] }),
  },
  status: {
    name: 'status',
    description: 'Show public content source status',
    usage: 'status',
    execute: () => ({
      lines: [`Source: ${profile.source}`, `Freshness: ${profile.freshness}`, 'Portfolio mode: local allowlisted commands'],
    }),
  },
}

export function executeCommand(command: ParsedCommand): CommandResult {
  if (!command.name) return { lines: [] }
  const definition = commandRegistry[command.name]
  if (!definition) return unsupported()
  const noArgumentCommands = new Set([
    'help', 'about', 'skills', 'education', 'certificates', 'milestones', 'experience',
    'contact', 'resume', 'github', 'linkedin', 'clear', 'history', 'whoami', 'date', 'status',
  ])
  if (noArgumentCommands.has(command.name) && command.args.length) {
    return { lines: [`Usage: ${definition.usage}`] }
  }
  if (command.args.length && command.name === 'help') return { lines: ['Usage: help'] }
  if (Object.keys(command.flags).length) {
    if (command.name !== 'projects') return unsupported()
  }
  return definition.execute(command)
}
