# Map: chessop in public

Labels: wayfinder:map
Source idea: [prompt1.md](../../prompt1.md)

## Destination

A **build-ready spec for a public hosted chessop** (`.scratch/chessop-public/spec.md`), with the ADRs it amends (0002 persistence, 0003 rating bands, 0004 web stack) and the glossary updated: anyone opens a URL, drills anonymously, may sign in to keep their progress, on desktop or phone. Done when a coding agent could build and deploy it with no design decision left open.

## Notes

- **Domain**: the chessop opening trainer (see `CONTEXT.md`, `docs/adr/`, and the v1 map `.scratch/chessop/map.md`). This effort reverses v1's *single learner, local-first, no hosting* (ADR 0002, ADR 0004) for a hosted mode.
- **Settled at charting (2026-09-29)**:
  - **Both modes, one codebase**: `chessop` still runs local and offline for one learner; a hosted mode adds many learners.
  - **Anonymous first**: a visitor drills with no sign-up; an optional account adopts the anonymous history.
  - **Sign-in**: Log in with Lichess (OAuth) first, email magic link as fallback; never passwords.
  - **Open-ended rating bands** are selectable (e.g. "1500+"), and **1500+ is the new default**.
  - **Hobby scale** to start: tens of concurrent learners, one cheap host, about €10/month or less; donations cover the bill, not growth.
  - **Mobile**: responsive web pages plus installable PWA. No native store apps.
  - **Donations**: a **Ko-fi** link (footer and progress page); no payment code in chessop.
  - **Monitoring**, light on three fronts: visitor analytics (cookieless), server health (uptime, errors), learning usage (from the round log).
  - **Domain name**: bought (about €10/year), independent of host.
  - **Source**: public repository on the owner's GitHub, linked from the site; licence stays GPL-3.0-or-later.
  - **Owner is in France**: GDPR and French law (CNIL, LCEN) apply.
- **Skills**: grilling + domain-modeling for decision tickets; prototype for UI tickets; research for fact tickets.

## Decisions so far

<!-- one line per closed ticket -->

- [Hosting options for a hobby-scale chessop](issues/01-hosting-options.md): the app idles at about 78 MB. OVH VPS-1 (France, €4.49 HT/month) is the best fit. PaaS costs as much and charges for disks; the one always-on free tier (Oracle) reclaims idle machines. Running the logic in the browser is possible (about 7.8 MB first load) but reverses ADR 0002/0004. itch.io is the only portal that fits, as a listing.
- [What French and EU law require of the site](issues/06-french-legal.md): no cookie banner needed if analytics meet the CNIL exemption and the learner cookie only holds progress. A legal notice (can be anonymous via the host) plus a GDPR privacy notice naming the controller. Export, deletion, and about 2-year inactivity purge. EU hosting avoids transfer questions. Ko-fi tips are likely taxable income.
- [Open-ended rating bands](issues/02-open-ended-bands.md): eight bands, the five closed plus open 1200+, 1500+, 1800+ (both players ≥ the bound). The learner picks the band directly, and the declared rating is gone. Default 1500+ in both modes. Natural rating mix and 150k cap kept. ADR 0003 amended.
- [Where and how chessop is hosted](issues/03-hosting-decision.md): the existing server unchanged on an OVH VPS-1 in Gravelines (€4.49 HT/month), `chessop.fr` at OVH, Caddy for HTTPS, Debian 13 + systemd, no Docker. PaaS, Oracle free and Pyodide rejected; no embedded itch.io build. ADR 0007, amends 0002 and 0004.
- [From one learner to many](issues/04-many-learners.md): anonymous learners are server-side records behind a cookie token, in one SQLite file keyed by learner. Signing in adopts by merging (later last pass wins per position). Settings go per learner (plus timezone); model parameters stay global. Band graphs are kept once loaded, repertoires are shared by settings, and learner sessions drop after 30 minutes idle. The one round-end lock stays. A learner's round log is deleted with them. ADR 0002 and 0004 amended.
- [Sign-in with Lichess and email](issues/05-sign-in.md): an account is one identity, Lichess id (no scope, token revoked at once) or email, never linked. Magic email = link + 6-digit code, 15 min, single-use, sent by Scaleway TEM. One rotated session cookie, signed-in for a year sliding; sign-out leaves no learner; account deletion is immediate. Local mode has no sign-in. ADR 0008.
- [Mobile layout and installable app](issues/07-mobile-and-pwa.md): on phones the play page is Stacked (compact header with sound/progress/settings icons, full-width board, verdict, a big Next round button, Explanation below; board beside the rest in landscape), progress is a condensed table (name, Score, White, Black). Installable PWA with a manifest, any orientation, and a service worker caching only the static shell plus an offline page; no offline play. Prototype on branch `prototype/mobile`.
- ["?" explanations for Score and progress](issues/08-help-explanations.md): one `/help` page ("How chessop works"), one anchored section per figure. The progress labels link to their sections; play gains a help link and "what does this mean?" under the verdict. No popovers, no first-visit walkthrough (band stays default 1500+, set in settings). Both modes. Prototype on branch `prototype/help`.
- [Monitoring traffic, health and usage](issues/09-monitoring.md): self-hosted GoatCounter (page views only, opt-out toggle, DNT/GPC honoured); UptimeRobot free on `/healthz`; errors in journald with a daily TEM email digest and `OnFailure=` alert; learning figures (active/new learners, rounds, pass rate, sign-ins/adoptions, retention) from a `chessop stats` CLI over SSH, with a daily counts-only aggregate table so history survives deletions.
- [Legal pages and data rights](issues/10-legal-pages-and-data-rights.md): an anonymous `/legal` via OVH plus a `/privacy` notice naming the owner, with `contact@chessop.fr`, no consent needed anywhere, and round-log refitting declared as legitimate interest. `/data` gives a JSON export and deletion for anonymous and signed-in learners. Retention: anonymous 12 months, accounts 24 months (email warning), journald 6 months with no access logs, GoatCounter 25 months, backups 30 days. The Ko-fi line says tips aren't tax-deductible.
- [Switching chessop serve into hosted mode](issues/11-hosted-mode-seam.md): `chessop serve --hosted` plus `CHESSOP_*` environment variables from a 0640 systemd env file. The TEM key is the only secret, since tokens are random and stored hashed. The code branches at three seams only: `current_learner`, a hosted-only router, and the base template's `site`. Hosted mode runs on http localhost for development, with email printed to the console. Manifest, service worker, `/help` and `/healthz` are served in both modes; local mode has no footer. The port is fixed on 127.0.0.1 behind Caddy, and the base URL comes from configuration, never from `Host`. `chessop notify-owner` sends the owner's alerts.
- [Abuse and limits on the hosted site](issues/12-abuse-and-limits.md): protect the box, not fairness. In-process counters under `--hosted`, keyed by IPv4 or IPv6 /64. At most 300 live sessions; 30 new anonymous learners per IP per hour, then a throwaway learner that plays but saves nothing. Anonymous learners with under 5 rounds purged after 30 idle days. WebSocket 5 msg/s (burst 20, 1 KB), 10 sockets per learner and 40 per IP. HTTP 120/min per IP, 10 settings saves/min, 5 exports/hour, 429 with `Retry-After`.
- [Deploying chessop to the VPS](issues/13-deploying.md): develop in the private repo (token dropped from its history); the public GitHub repo has no history, one squashed commit per release via `publish.sh`, leaving out third-party `refs/` copies. CI runs tests only. `deploy.sh` by hand over SSH: tag checkout + `uv sync --frozen` (uv-managed 3.12) under `/opt/chessop/releases`, pre-deploy SQLite backup, plain restart (a round in progress is lost), `/healthz` check with symlink rollback. Hardened systemd unit, `provision.sh`, no staging. Snapshot built locally, shipped with releases; `snapshot_version` per learner. ADR 0007 amended.
- [Latency over the internet](issues/15-latency.md): one learner already missed the 10 ms budget (fsync at round end). SQLite goes WAL + `synchronous=NORMAL`, giving about 5 ms p95 at 300 clients; the one round-end lock stays on the event loop. Budget: all moves under 10 ms p95 with 30 learners playing, 250 ms end to end on 4G. Slow builds go to a worker thread, default key warmed at startup. 300 sessions kept by sharing repertoire-only caches (about 0.5 GB). A dropped socket abandons the round; the page auto-reconnects to a fresh one. Kept `scripts/loadtest.py` as a pre-launch gate. ADR 0002 and 0004 amended.
- [Letting people find chessop](issues/16-discovery.md): the spec covers only what the site and repo contain. One pitch ("Grind chess openings against the moves people at your rating really play…", "grind" in the pitch only, "drill" everywhere else). `/` and `/help` indexable, the rest `noindex`; `www` and http redirect to `https://chessop.fr` with canonical links. Open Graph tags and one hand-made static preview image, hosted only. English only. README leads with the site, then local install, then hosting your own.
- [Operating the hosted site](issues/14-operating.md): one `chessop maintain` timer at 03:30 UTC (aggregate, account warnings, purges, backup). Nightly SQLite backup, 14 days on the VPS plus an `age`-encrypted copy in a Scaleway Paris bucket that expires after 30 days, uploaded with a write-only key. Accounts are deleted only 30 days after a warning that was sent. `chessop-notify@` template for `OnFailure=`, alerts to the owner's own address. GoatCounter from a pinned binary. No contact form, a mail link instead. Runbook `docs/operating.md` with the first-time setup checklist; no wizard.

## Not yet specified

<!-- all fog graduated 2026-09-30 into Deploying chessop to the VPS, Operating the hosted site, Latency over the internet, Letting people find chessop -->

## Out of scope

- **Native App Store / Play Store apps**: store fees and review for nothing a PWA does not give (charting).
- **Ads or paid tiers**: donations only (charting).
- **Announcing and listings** (Lichess forum or blog, Reddit, an itch.io link-only page): nothing a coding agent builds, and a quiet start suits the box ([Letting people find chessop](issues/16-discovery.md)).
- **A French version**: a translation of every page, explanation and email is its own effort ([Letting people find chessop](issues/16-discovery.md)).
