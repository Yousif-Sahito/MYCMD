import { profile } from '../data/portfolio'
import { safeUrl } from '../data/publicDataSchema'

export default function ContactPage() {
  const url = safeUrl(profile.contactUrl)
  return (
    <section className="page" aria-labelledby="contact-heading">
      <p className="eyebrow">Contact</p>
      <h1 id="contact-heading" tabIndex={-1}>Public contact</h1>
      {url ? (
        <div className="card">
          <h2>{profile.contactLabel}</h2>
          <p>Visit the reviewed public source repository.</p>
          <a className="button primary" href={url} rel="noreferrer">Open GitHub</a>
        </div>
      ) : (
        <div className="empty-state">
          <h2>No public contact method configured</h2>
          <p>No private address or unapproved social link is published.</p>
        </div>
      )}
    </section>
  )
}
