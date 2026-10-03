# Where and how chessop is hosted

Type: grilling
Status: resolved
Blocked by: 01
Map: [chessop in public](../map.md)

## Question

With the hosting research in hand, choose the route: a VPS running the existing server, a PaaS, a free tier, or a static site with the chess logic moved into the browser (which would reverse ADR 0004's server-authoritative client). Also choose the provider and region, the domain registrar and name, how HTTPS is served, and whether a game-platform listing (itch.io) is added. Amends ADR 0002's and ADR 0004's "no hosting".

## Answer

Recorded in [ADR 0007](../../../docs/adr/0007-hosting.md), with amendments to ADR 0002 and ADR 0004. Grilled 2026-09-29.

- **Route**: one VPS runs the existing server unchanged: authoritative, state in the process, SQLite on disk, one WebSocket per tab. Rejected: PaaS (no cheaper, disks extra, Render drops WebSockets on deploy), Oracle free tier (reclaims idle instances), Pyodide in the browser (a redesign reversing ADR 0004, splits local from hosted).
- **Host**: OVH VPS-1, Gravelines (France). €4.49 HT/month without commitment at first, then the 12-month commitment (€3.81 HT) once the site is kept.
- **Domain**: `chessop.fr` (free per AFNIC RDAP on 2026-09-29; `chessop.org` also free, `chessop.app` taken), registered at OVH (€4.99 HT first year, €7.79 HT renewal). Auto-renew and 2FA on. `www` redirects to the apex.
- **HTTPS**: Caddy reverse proxy with automatic Let's Encrypt, HTTP→HTTPS redirect, HSTS, WebSockets passed to uvicorn on 127.0.0.1.
- **Server**: Debian 13, `uv tool install` under an unprivileged user, systemd unit, no Docker. Unattended upgrades; firewall 22/80/443; SSH by key only.
- **itch.io**: no embedded build; a link-only page, if any, stays in the map's Discovery fog.
- **Cost**: about €5.40/month TTC plus about €9/year for the domain.
- Still fog (Deploying and operating): deploys, SQLite backups beyond OVH's daily backup, snapshot refresh, hosted-mode flags.
