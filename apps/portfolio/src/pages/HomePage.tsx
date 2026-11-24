import { Link } from 'react-router-dom'
import { profile, projects, skillCategories } from '../data/portfolio'
import { safeUrl } from '../data/publicDataSchema'

export default function HomePage() {
  const resumeUrl = safeUrl(profile.resumeUrl ?? undefined)
  return (
    <div>
      <section className="hero">
        <p className="eyebrow">Public portfolio</p>
        <h1 tabIndex={-1}>Build. Operate. Explore.</h1>
        <p className="hero-lead">{profile.heading}. {profile.introduction}</p>
        <div className="hero-actions">
          <Link className="button primary" to="/projects">Explore projects</Link>
          <Link className="button" to="/terminal">Open terminal</Link>
          {resumeUrl && <a className="button" href={resumeUrl}>View resume</a>}
        </div>
      </section>
      <section className="section" aria-labelledby="featured-heading">
        <div className="section-heading">
          <div>
            <p className="eyebrow">Selected work</p>
            <h2 id="featured-heading">Featured projects</h2>
          </div>
          <Link to="/projects">View all projects</Link>
        </div>
        <div className="card-grid">
          {projects.filter((project) => project.featured).map((project) => (
            <article className="card" key={project.slug}>
              <span className={`status status-${project.status}`}>{project.status}</span>
              <h3>{project.title}</h3>
              <p>{project.summary}</p>
              <div className="tag-list" aria-label="Technologies">
                {project.technologies.map((technology) => <span key={technology}>{technology}</span>)}
              </div>
              <Link className="card-link" to={`/projects/${project.slug}`}>View project</Link>
            </article>
          ))}
        </div>
      </section>
      <section className="section" aria-labelledby="skills-heading">
        <p className="eyebrow">Capabilities</p>
        <h2 id="skills-heading">Technical areas</h2>
        <div className="skill-grid">
          {skillCategories.map((category) => (
            <article className="skill-card" key={category.name}>
              <h3>{category.name}</h3>
              <p>{category.description}</p>
              <ul>{category.skills.map((skill) => <li key={skill}>{skill}</li>)}</ul>
            </article>
          ))}
        </div>
      </section>
      <section className="cta">
        <div>
          <p className="eyebrow">Portfolio terminal</p>
          <h2>Explore MYCMD without a remote shell</h2>
        </div>
        <Link className="button primary" to="/terminal">Try help</Link>
      </section>
    </div>
  )
}
