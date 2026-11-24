import { useMemo, useState } from 'react'
import { Link } from 'react-router-dom'
import { projects } from '../data/portfolio'

export default function ProjectsPage() {
  const [search, setSearch] = useState('')
  const [status, setStatus] = useState('all')
  const [technology, setTechnology] = useState('all')
  const technologies = useMemo(
    () => [...new Set(projects.flatMap((project) => project.technologies))].sort(),
    [],
  )
  const visible = projects.filter((project) => {
    const matchesSearch = `${project.title} ${project.summary} ${project.description}`
      .toLowerCase().includes(search.toLowerCase())
    const matchesStatus = status === 'all' || project.status === status
    const matchesTechnology = technology === 'all' || project.technologies.includes(technology)
    return matchesSearch && matchesStatus && matchesTechnology
  })

  return (
    <section className="page" aria-labelledby="projects-heading">
      <div className="page-heading">
        <div>
          <p className="eyebrow">Selected work</p>
          <h1 id="projects-heading" tabIndex={-1}>Projects</h1>
        </div>
      </div>
      <div className="filters" aria-label="Project filters">
        <label>
          Search
          <input value={search} onChange={(event) => setSearch(event.target.value)} placeholder="Search projects" />
        </label>
        <label>
          Status
          <select value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="all">All</option>
            <option value="active">Active</option>
            <option value="completed">Completed</option>
            <option value="planned">Planned</option>
          </select>
        </label>
        <label>
          Technology
          <select value={technology} onChange={(event) => setTechnology(event.target.value)}>
            <option value="all">All</option>
            {technologies.map((item) => <option key={item} value={item}>{item}</option>)}
          </select>
        </label>
      </div>
      {visible.length ? (
        <div className="card-grid">
          {visible.map((project) => (
            <article className="card" key={project.slug}>
              <span className={`status status-${project.status}`}>{project.status}</span>
              <h2>{project.title}</h2>
              <p>{project.summary}</p>
              <div className="tag-list">{project.technologies.map((item) => <span key={item}>{item}</span>)}</div>
              <Link className="card-link" to={`/projects/${project.slug}`}>View details</Link>
            </article>
          ))}
        </div>
      ) : (
        <div className="empty-state"><h2>No matching projects</h2><p>Try clearing one or more filters.</p></div>
      )}
    </section>
  )
}
