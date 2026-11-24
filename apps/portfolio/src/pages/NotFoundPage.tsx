import { Link } from 'react-router-dom'

export default function NotFoundPage() {
  return (
    <section className="page not-found" aria-labelledby="not-found-heading">
      <p className="eyebrow">404</p>
      <h1 id="not-found-heading" tabIndex={-1}>Page not found</h1>
      <p>The requested route does not exist in this portfolio.</p>
      <Link className="button primary" to="/">Return home</Link>
    </section>
  )
}
