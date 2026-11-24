import { skillCategories } from '../data/portfolio'

export default function SkillsPage() {
  return (
    <section className="page" aria-labelledby="skills-heading">
      <div className="page-heading">
        <div><p className="eyebrow">Technical capabilities</p><h1 id="skills-heading" tabIndex={-1}>Skills</h1></div>
      </div>
      <div className="skill-grid">
        {skillCategories.map((category) => (
          <article className="skill-card" key={category.name}>
            <h2>{category.name}</h2>
            <p>{category.description}</p>
            <ul>{category.skills.map((skill) => <li key={skill}>{skill}</li>)}</ul>
          </article>
        ))}
      </div>
    </section>
  )
}
