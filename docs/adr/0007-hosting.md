# Hosting: the existing server on one OVH VPS behind Caddy

Status: accepted (chessop-public ticket 03, 2026-09-29)

ADR 0002 and ADR 0004 ruled out hosting for v1. The chessop-public effort adds a hosted mode alongside the local one, for tens of concurrent learners, on about €10 a month or less, run by an owner in France. This ADR decides where it runs and how it is reached. Figures come from `docs/research/hosting-options.md` (chessop-public ticket 01, branch `research/hosting-options`).

## Decision

- **One VPS runs the existing server, unchanged in shape**: one FastAPI + uvicorn process, all state in memory, SQLite on local disk, one WebSocket per tab (ADR 0004). The server stays authoritative (ADR 0002). Local and hosted modes stay one codebase.
- **OVH VPS-1** (2 vCore, 4 GB, 40 GB NVMe, unlimited traffic, daily backup included) in **Gravelines, France**. Billed monthly without commitment at €4.49 HT at first; moved to the 12-month commitment (€3.81 HT) once the site has proved worth keeping. The app idles at about 78 MB, so the smallest plan is ample.
- **Domain `chessop.fr`**, registered at **OVH** (€4.99 HT the first year, €7.79 HT renewal), auto-renew on, two-factor authentication on the OVH account. `www.chessop.fr` redirects to `chessop.fr`.
- **Caddy** is the reverse proxy and terminates TLS, with automatic Let's Encrypt certificates. It redirects HTTP to HTTPS, sends HSTS, and passes WebSockets through to uvicorn on `127.0.0.1`.
- **Debian 13**, chessop installed with `uv tool install` under its own unprivileged user and run by a **systemd** unit; Caddy from the Debian package. No Docker. Unattended security upgrades on; firewall open on 22, 80 and 443 only; SSH by key only.
- **No game-portal build.** An itch.io page, if any, only links to the site (a discovery question, not a hosting one).

## Considered options

- **PaaS** (Render, Fly.io, Railway): no cheaper than the VPS once a disk is added; Render drops WebSockets on deploy and caps Hobby bandwidth at 5 GB.
- **Free tiers**: Oracle Always Free is the only always-on one with a disk and WebSockets, but it reclaims idle instances and a quiet hobby site matches its idle rule. The others sleep or have no disk.
- **Static site with the chess logic in the browser** (Pyodide, progress in IndexedDB, accounts on Supabase or Turso): €0 hosting and about 7.8 MB first load, but a redesign that reverses ADR 0004's logic-free browser and ADR 0002's authoritative server, needs a self-built python-chess wheel, and would split the hosted app from the local one.
- **Hetzner CX23**: comparable, but about €6.60 with VAT plus IPv4 after its June 2026 rise, and outside France.
- **nginx + certbot**: more configuration, a renewal timer and explicit WebSocket upgrade headers, for nothing Caddy lacks here.
- **Docker Compose**: reproducible, but a layer to maintain for one process and one file, against ADR 0004's "no Docker image".
- **`.org` or `.app`**: `.org` renews at about €13, `.app` was taken; `.fr` is the cheapest and the owner, living in France, may hold one.
- **An embedded itch.io build**: itch.io's guidelines discourage third-party logins and redirecting traffic, which Lichess sign-in would do inside an iframe.

## Consequences

- Running cost about €5.40 a month with VAT plus about €9 a year for the domain, inside the €10/month budget.
- Registrar and host share one OVH account: losing it loses both; two-factor authentication is the mitigation, accepted for a hobby site.
- The host is in the EU, so the privacy notice needs no transfer clause for hosting (`docs/research/french-legal.md`, branch `research/french-legal`). OVH is the host named in the legal notice.
- Left to later decisions: deploys (CI or by hand), backups of the SQLite file beyond OVH's daily backup, snapshot refresh on the hosted instance, and the flags that switch `chessop serve` into hosted mode.

## Amendment (chessop-public ticket 13, 2026-09-30)

**Install by checkout, not `uv tool install`**: the VPS checks out a release tag into `/opt/chessop/releases/vX.Y.Z` and runs `uv sync --frozen --no-dev` with uv-managed CPython 3.12, behind a `current` symlink. `uv tool install` re-resolves dependencies and ignores `uv.lock`, so the server could run a set CI never tested. **Releases come from a private repo**: development stays in the local repo; the public GitHub repo holds no history, one squashed commit per release made by `deploy/publish.sh`, which leaves out third-party reference copies and personal tooling. Deploys are by hand (`deploy/deploy.sh`) with the owner's SSH key, gated on a green CI run, with a pre-deploy SQLite backup and an automatic symlink rollback if `/healthz` fails. Details in the ticket (Deploying chessop to the VPS).

Considered: **push-triggered deploys from GitHub Actions** (a deploy key in GitHub, and a release ships on push, not by choice); **`uv tool install`** (ignores the lock); **publishing the full history** (a Lichess token in one commit and third-party PDFs throughout); **a from-scratch public repo developed in the open** (the owner prefers to keep day-to-day history private); **a staging instance** (hosted mode on localhost already rehearses).
