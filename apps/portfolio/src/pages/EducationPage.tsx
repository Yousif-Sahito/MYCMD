import { education } from '../data/portfolio'

export default function EducationPage() {
  return (
    <section className="page" aria-labelledby="education-heading">
      <div className="page-heading">
        <div><p className="eyebrow">Academic timeline</p><h1 id="education-heading" tabIndex={-1}>Education</h1></div>
      </div>
      {education.length ? (
        <ol className="timeline">
          {education.map((item) => (
            <li key={`${item.institution}-${item.program}`}>
              <p className="timeline-period">{item.period}</p>
              <h2>{item.institution}</h2>
              <h3>{item.program}</h3>
              <p>{item.description}</p>
            </li>
          ))}
        </ol>
      ) : (
        <div className="empty-state">
          <h2>No public education information configured</h2>
          <p>This portfolio does not publish an academic timeline until reviewed public information is available.</p>
        </div>
      )}
    </section>
  )
}
