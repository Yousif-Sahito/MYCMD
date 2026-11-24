import { describe, expect, it } from 'vitest'
import { projects, profile, skillCategories, education, certificates, milestones } from './portfolio'
import { safeUrl, validatePublicPortfolioData } from './publicDataSchema'

describe('public portfolio data', () => {
  it('uses only safe public project URLs', () => {
    expect(safeUrl('javascript:alert(1)')).toBeNull()
    expect(safeUrl('http://example.com')).toBeNull()
    expect(safeUrl('https://user:pass@example.com')).toBeNull()
    expect(safeUrl('https://127.0.0.1/private')).toBeNull()
    expect(safeUrl('https://example.com')).not.toBeNull()
  })
  it('validates checked-in public data', () => {
    const errors = validatePublicPortfolioData({
      profile,
      projects,
      skills: skillCategories,
      education,
      certificates,
      milestones,
    })
    expect(errors).toEqual([])
  })
  it('rejects duplicate or malformed slugs and unsafe profile URLs', () => {
    const duplicate = {
      profile: { ...profile, github: 'javascript:alert(1)' },
      projects: [projects[0]!, { ...projects[0]! }],
      skills: skillCategories,
      education,
      certificates,
      milestones,
    }
    duplicate.projects[0]!.slug = 'Not A Slug'
    duplicate.projects[1]!.slug = 'Not A Slug'
    const errors = validatePublicPortfolioData(duplicate)
    expect(errors.some((error) => error.includes('Invalid project slug'))).toBe(true)
    expect(errors.some((error) => error.includes('Duplicate project slug'))).toBe(true)
    expect(errors.some((error) => error.includes('Unsafe profile URL'))).toBe(true)
  })
})
