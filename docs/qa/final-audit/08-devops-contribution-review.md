# 8. DevOps, Release and GitHub Contribution Review

## Scope

The pass reviewed Git identity, branches, remotes, commit count, exact-SHA CI,
tags/releases and repository presentation.

## Repository facts

- Canonical repository: `Yousif-Sahito/MYCMD`
- Default branch: `main`
- Remote: public origin
- No tags or GitHub releases were found
- 80 reachable commits inspected: 72 by the local human identity and 8 by Copilot
- 36 commits contain a Copilot co-author trailer
- No signed commits were detected
- GitHub CLI authentication is active for `Yousif-Sahito`

## CI facts

The repository has exact-SHA Windows, Ubuntu, portfolio and MySQL CI evidence.
The final Phase 10 implementation report is linked to run `45698439710`.
The documentation commits may require their own exact-SHA rerun after this audit.

## Attribution findings

| ID | Severity | Finding | Evidence | Recommendation |
| --- | --- | --- | --- | --- |
| DEV-1 | MEDIUM | Human Git author email has not been proven linked to the GitHub account | Local config and GitHub CLI account differ in identity metadata | Verify and associate an approved email through GitHub account settings |
| DEV-2 | LOW | No tags/releases exist | `git tag --list` empty | Create releases only after a verified packaged release milestone |
| DEV-3 | LOW | README had outdated Phase 1 status | Updated in this audit | Keep README synchronized with phase reports |

## Safe future configuration

Use the repository owner-approved GitHub noreply address for future commits.
Do not rewrite public history solely to improve contribution counts.
Keep Copilot co-author trailers only for commits where Copilot work contributed.
