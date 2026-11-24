import { Link, useParams } from 'react-router-dom'
import { projects } from '../data/portfolio'
import { safeUrl } from '../data/publicDataSchema'

export default function ProjectDetailPage() {
  const { slug } = useParams()
  const project = projects.find((item) => item.slug === slug)
  if (!project) {
    return (
      <section className="page" aria-labelledby="missing-project">
        <p className="eyebrow">Unknown project</p>
        <h1 id="missing-project" tabIndex={-1}>Project not found</h1>
        <p>This public project slug is not available.</p>
        <Link className="button" to="/projects">Back to projects</Link>
      </section>
    )
  }
  const repository = safeUrl(project.repository?.href)
  const demo = safeUrl(project.demo?.href)

  return (
    <article className="page project-detail" aria-labelledby="project-title">
      <Link className="back-link" to="/projects">Back to projects</Link>
      <p className="eyebrow">{project.status}</p>
      <h1 id="project-title" tabIndex={-1}>{project.title}</h1>
      <p className="detail-lead">{project.summary}</p>
      <div className="detail-grid">
        <section>
          <h2>Overview</h2>
          <p>{project.description}</p>
          <h2>Technology</h2>
          <div className="tag-list">{project.technologies.map((item) => <span key={item}>{item}</span>)}</div>
        </section>
        <aside>
          <h2>Project details</h2>
          <dl>
            <dt>Status</dt><dd>{project.status}</dd>
            <dt>Started</dt><dd>{project.startedAt}</dd>
            {project.finishedAt && <><dt>Finished</dt><dd>{project.finishedAt}</dd></>}
          </dl>
          {repository && <a className="button" href={repository} rel="noreferrer">Repository</a>}
          {demo && <a className="button" href={demo} rel="noreferrer">Live demo</a>}
          {!repository && !demo && <p className="muted">No public external links are configured.</p>}
        </aside>
      </div>
    </article>
  )
}
