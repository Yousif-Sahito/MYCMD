import type { Certificate, Education, PublicProject, SkillCategory, TimelineItem } from './portfolio'

export type PublicPortfolioData = {
  profile: typeof import('./portfolio').profile
  projects: PublicProject[]
  skills: SkillCategory[]
  education: Education[]
  certificates: Certificate[]
  milestones: TimelineItem[]
}

export function safeUrl(value: string | undefined): string | null {
  if (!value) return null
  try {
    const url = new URL(value)
    if (url.protocol !== 'https:' || url.username || url.password) return null
    const host = url.hostname.toLowerCase()
    if (
      host === 'localhost'
      || host.endsWith('.localhost')
      || host === '127.0.0.1'
      || host === '::1'
      || /^(10\.|192\.168\.|169\.254\.|172\.(1[6-9]|2\d|3[0-1])\.)/.test(host)
    ) return null
    return url.href
  } catch {
    return null
  }
}

export function validatePublicPortfolioData(data: PublicPortfolioData): string[] {
  const errors: string[] = []
  for (const value of [
    data.profile.github,
    data.profile.contactUrl,
    data.profile.resumeUrl ?? undefined,
    data.profile.linkedinUrl ?? undefined,
  ]) {
    if (value && !safeUrl(value)) errors.push(`Unsafe profile URL: ${value}`)
  }
  const slugs = new Set<string>()
  for (const project of data.projects) {
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(project.slug)) {
      errors.push(`Invalid project slug: ${project.slug}`)
    }
    if (slugs.has(project.slug)) errors.push(`Duplicate project slug: ${project.slug}`)
    slugs.add(project.slug)
    if (project.repository && !safeUrl(project.repository.href)) {
      errors.push(`Unsafe repository URL: ${project.slug}`)
    }
    if (project.demo && !safeUrl(project.demo.href)) {
      errors.push(`Unsafe demo URL: ${project.slug}`)
    }
  }
  return errors
}
