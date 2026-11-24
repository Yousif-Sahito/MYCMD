import { profile } from '../data/portfolio'

export default function AboutPage() {
  return (
    <section className="page" aria-labelledby="about-heading">
      <p className="eyebrow">About MYCMD</p>
      <h1 id="about-heading" tabIndex={-1}>Portfolio identity</h1>
      <div className="prose">
        <h2>{profile.heading}</h2>
        <p>{profile.introduction}</p>
        <p>
          The public site is separate from the trusted local desktop terminal. It uses only reviewed,
          checked-in public content and cannot execute operating-system commands.
        </p>
      </div>
    </section>
  )
}
