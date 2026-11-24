# MYCMD Public Portfolio

This Vite/React/TypeScript application is the public Phase 5 surface for MYCMD.

## Development

```powershell
npm ci
npm run dev
```

The public terminal is an allowlisted portfolio command interface. It never imports or
connects to the Phase 3 local terminal engine, any SQL layer or a remote shell endpoint.

## Checks

```powershell
npm run typecheck
npm run lint
npm test
npm run build
npm run e2e:install
npm run e2e
```

Playwright runs against the production preview for desktop and mobile Chromium projects.
Static deep-link support includes a Netlify-style `public/_redirects` rule; no live hosting
provider or deployment domain is claimed.
