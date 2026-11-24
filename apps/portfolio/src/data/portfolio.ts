export type PublicUrl = { label: string; href: string }

export type PublicProject = {
  slug: string
  title: string
  summary: string
  description: string
  status: 'active' | 'completed' | 'planned'
  featured: boolean
  technologies: string[]
  startedAt: string
  finishedAt?: string
  repository?: PublicUrl
  demo?: PublicUrl
}

export type SkillCategory = {
  name: string
  skills: string[]
  description: string
}

export type Education = {
  institution: string
  program: string
  period: string
  description: string
}

export type Certificate = {
  name: string
  issuer: string
  issuedAt: string
  credentialUrl?: string
  description: string
}

export type TimelineItem = {
  title: string
  organization: string
  period: string
  status: 'completed' | 'active' | 'planned'
  summary: string
}

export const profile = {
  name: 'MYCMD',
  heading: 'An offline-first personal command centre',
  introduction:
    'MYCMD is a typed Python portfolio project spanning shared domain models, SQLite storage, a native CLI, a real local terminal engine, a PySide6 desktop GUI and a restricted public portfolio website.',
  github: 'https://github.com/Yousif-Sahito/MYCMD',
  contactLabel: 'GitHub',
  contactUrl: 'https://github.com/Yousif-Sahito/MYCMD',
  resumeUrl: null as string | null,
  linkedinUrl: null as string | null,
  source: 'Checked-in curated public data',
  freshness: 'Static content - no remote synchronization',
}

export const projects: PublicProject[] = [
  {
    slug: 'mycmd-cli',
    title: 'MYCMD CLI',
    summary: 'A native command interface for validated personal portfolio data.',
    description:
      'A Typer and Rich CLI that shares domain validation and SQLite persistence with the desktop application.',
    status: 'completed',
    featured: true,
    technologies: ['Python', 'Typer', 'Rich', 'SQLite'],
    startedAt: '2026-11-14',
    finishedAt: '2026-11-14',
    repository: { label: 'Source repository', href: 'https://github.com/Yousif-Sahito/MYCMD' },
  },
  {
    slug: 'mycmd-terminal',
    title: 'MYCMD Terminal Engine',
    summary: 'Real Windows ConPTY and POSIX PTY lifecycle management.',
    description:
      'A typed terminal session layer with bounded output, resize, interrupt and child-process cleanup for trusted local use.',
    status: 'completed',
    featured: true,
    technologies: ['Python', 'ConPTY', 'POSIX PTY', 'PyWinpty'],
    startedAt: '2026-11-14',
    finishedAt: '2026-11-14',
    repository: { label: 'Source repository', href: 'https://github.com/Yousif-Sahito/MYCMD' },
  },
  {
    slug: 'mycmd-desktop',
    title: 'MYCMD Desktop',
    summary: 'A PySide6 desktop interface for offline portfolio management.',
    description:
      'A desktop workspace with CRUD pages, settings, SQLite-backed status and a bundled xterm.js terminal renderer.',
    status: 'completed',
    featured: true,
    technologies: ['Python', 'PySide6', 'Qt WebEngine', 'xterm.js', 'SQLite'],
    startedAt: '2026-11-14',
    finishedAt: '2026-11-14',
    repository: { label: 'Source repository', href: 'https://github.com/Yousif-Sahito/MYCMD' },
  },
  {
    slug: 'mycmd-portfolio',
    title: 'MYCMD Public Portfolio',
    summary: 'An accessible static portfolio with a restricted browser terminal.',
    description:
      'A React and TypeScript public surface for curated project, skill and timeline information, backed only by reviewed checked-in data.',
    status: 'active',
    featured: true,
    technologies: ['React', 'TypeScript', 'Vite', 'xterm.js'],
    startedAt: '2026-11-24',
  },
]

export const skillCategories: SkillCategory[] = [
  {
    name: 'Languages',
    skills: ['Python', 'TypeScript', 'JavaScript'],
    description: 'Typed application code for desktop, CLI and browser surfaces.',
  },
  {
    name: 'Desktop and terminal',
    skills: ['PySide6', 'Qt WebEngine', 'xterm.js', 'ConPTY', 'POSIX PTY'],
    description: 'Local interactive interfaces and native process lifecycle work.',
  },
  {
    name: 'Data',
    skills: ['SQLite', 'Domain validation', 'Atomic migrations'],
    description: 'Offline persistence and transactional domain operations.',
  },
  {
    name: 'Quality',
    skills: ['pytest', 'Vitest', 'Playwright', 'Ruff', 'mypy', 'ESLint'],
    description: 'Executable unit, integration, browser and static quality gates.',
  },
]

export const education: Education[] = []
export const certificates: Certificate[] = []
export const milestones: TimelineItem[] = [
  {
    title: 'Foundation through desktop GUI',
    organization: 'MYCMD',
    period: 'November 2026',
    status: 'completed',
    summary: 'Completed the shared domain, SQLite, CLI, real terminal engine and desktop application milestones.',
  },
  {
    title: 'Public portfolio website',
    organization: 'MYCMD',
    period: 'November 2026',
    status: 'active',
    summary: 'Building the restricted public browser terminal and responsive portfolio pages.',
  },
]
