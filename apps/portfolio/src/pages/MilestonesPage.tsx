import { milestones } from '../data/portfolio'

export default function MilestonesPage() {
  return (
    <section className="page" aria-labelledby="milestones-heading">
      <div className="page-heading">
        <div><p className="eyebrow">Progress and experience</p><h1 id="milestones-heading" tabIndex={-1}>Milestones</h1></div>
      </div>
      <ol className="timeline">
        {milestones.map((item) => (
          <li key={`${item.title}-${item.period}`}>
            <p className="timeline-period">{item.period}</p>
            <span className={`status status-${item.status}`}>{item.status}</span>
            <h2>{item.title}</h2>
            <h3>{item.organization}</h3>
            <p>{item.summary}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
