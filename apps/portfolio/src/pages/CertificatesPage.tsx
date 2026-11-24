import { certificates } from '../data/portfolio'
import { safeUrl } from '../data/publicDataSchema'

export default function CertificatesPage() {
  return (
    <section className="page" aria-labelledby="certificates-heading">
      <div className="page-heading">
        <div><p className="eyebrow">Credentials</p><h1 id="certificates-heading" tabIndex={-1}>Certificates</h1></div>
      </div>
      {certificates.length ? (
        <div className="card-grid">
          {certificates.map((certificate) => {
            const url = safeUrl(certificate.credentialUrl)
            return (
              <article className="card" key={`${certificate.name}-${certificate.issuer}`}>
                <h2>{certificate.name}</h2>
                <p>{certificate.issuer}</p>
                <p>{certificate.description}</p>
                {url && <a className="card-link" href={url} rel="noreferrer">View credential</a>}
              </article>
            )
          })}
        </div>
      ) : (
        <div className="empty-state">
          <h2>No public certificates configured</h2>
          <p>Credential links are displayed only when reviewed public information is available.</p>
        </div>
      )}
    </section>
  )
}
