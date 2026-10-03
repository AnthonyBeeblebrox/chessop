# Letting people find chessop

Type: grilling
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

With no embedded build (ADR 0007), is a link-only itch.io page pointing at `chessop.fr` worth making, and are other listings or announcements (Lichess forum or blog, Reddit r/chess, a README badge) part of this effort or out of scope? If kept: what the listing says, which screenshots, and who maintains it.

## Answer

Grilled 2026-10-02. No ADR (all of it is easy to reverse). Glossary: **Drill** added to `CONTEXT.md`, with "grind" as the pitch-only word.

- **Scope**: the spec covers only what the site and the repo must contain to be findable. Announcing (Lichess forum or blog, Reddit, anywhere else) is out of scope: the owner posts when they like, and a quiet start suits a box budgeted for 30 learners playing and capped at 300 sessions.
- **itch.io**: no page. A link-out page with no playable build gets little traffic and is one more listing to keep in step. Out of scope.
- **The pitch**, one wording everywhere a stranger first meets chessop:
  - Title on `/`: `chessop: grind chess openings`
  - Description (meta description, link preview, README lead): "Grind chess openings against the moves people at your rating really play, drawn from Lichess games. Free, no sign-up."
  - `/help` keeps its own title, "How chessop works", with the same description.
  - "Grind" is used in the pitch only. The app, the CLI, `/help` body copy, the glossary and the code keep "drill".
- **Search engines**: `/` and `/help` are indexable; every other page (`/data`, `/privacy`, `/legal`, settings, progress, sign-in and account routes) carries `noindex`. A `robots.txt` at `chessop.fr` allows crawling; no sitemap. `stats.chessop.fr` serves a `robots.txt` disallowing everything.
- **One address**: Caddy redirects `www.chessop.fr` and plain http to `https://chessop.fr`. The two indexed pages carry `rel=canonical`, built from the configured base URL, never from `Host` (Switching chessop serve into hosted mode).
- **Link previews**: Open Graph tags (title, description, URL, type `website`, image) plus `twitter:card` `summary_large_image`, hosted mode only, emitted through the base template's `site` value. One static 1200×630 PNG, the same on every page, shipped with the static files: a board in an opening position with the name "chessop" and the pitch beside it, made once by hand, not generated and not a screenshot.
- **Language**: English only, `lang="en"`. A French version is out of scope.
- **README of the public repo** (shipped by `publish.sh`): the pitch, the `https://chessop.fr` link, one real desktop screenshot of the play page kept in the repo; then "Run it yourself" (the existing local install and use, unchanged, still offline); then a short "Hosting your own" pointing at `serve --hosted` and the deploy scripts, promising no support; licence last. No badges.
- **GitHub repo**: topics `chess`, `openings`, `spaced-repetition`, and the description set to the pitch, when the repo is created (a human-only step, listed with the others in Operating the hosted site).
- **Local mode**: unchanged. No Open Graph tags, no canonical link, no `robots.txt`; its title stays as it is.
