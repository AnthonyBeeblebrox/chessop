# Hosting options for a hobby-scale chessop

Type: research
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

What does each hosting route actually offer and cost today, for an app that is a FastAPI + uvicorn process holding a ~1.4 MB (compressed) snapshot in memory, one WebSocket per tab, and SQLite on disk, run by an owner in France at tens of concurrent learners and about €10/month or less? Verify, from primary sources (provider pricing and terms pages):

- **VPS**: Hetzner, OVH, Scaleway, DigitalOcean — smallest plan's price, RAM, EU location, bandwidth.
- **PaaS**: Render, Railway, Fly.io, Koyeb — price of an always-on small instance, WebSocket support, persistent-disk cost, sleep/cold-start behaviour.
- **Free tiers**: Oracle Cloud Always Free, Render free, Koyeb free, Google Cloud e2-micro, Hugging Face Spaces, PythonAnywhere — limits, sleeping, disk persistence, WebSockets, reclamation rules.
- **Static hosting + logic in the browser**: GitHub Pages / Cloudflare Pages limits; Pyodide first-load size and time with python-chess; what a free backend for accounts would be (Supabase, Turso, etc.).
- **Browser game platforms**: itch.io (can an HTML5 upload open a WebSocket or iframe an external site?), CrazyGames, Poki, Newgrounds — submission requirements, SDK/ad obligations, fit for a training tool.
- **Domain registrars** for a `.org`/`.fr`/`.app`: yearly price (Gandi, OVH, Cloudflare, Porkbun).

Write findings with citations and access dates to `docs/research/hosting-options.md`.

AFK. Fired at charting time. Findings: branch `research/hosting-options`, file `docs/research/hosting-options.md`.

## Answer

Full findings with citations and a comparison table: `docs/research/hosting-options.md` on branch `research/hosting-options` (commit b8515bc).

- **Footprint**: `chessop serve` with the packaged snapshot measured about 78 MB of memory when idle. Any plan with 512 MB or more fits. Growth with many learners was not measured.
- **Best-value VPS: OVH VPS-1**: 2 vCore, 4 GB RAM, 40 GB NVMe, unlimited traffic, in France. €4.49 HT/month with no commitment, or €3.81 on 12 months. Hetzner CX23 is now €5.49 HT plus IPv4 (raised 2026-06-15). Scaleway DEV1-S is €6.55 plus IPv4 and storage. DigitalOcean's $6 plan has 1 GiB.
- **PaaS is no cheaper, and disks cost extra**: Render Starter $7 (drops WebSockets on deploy, 5 GB bandwidth on Hobby), Fly.io about $3.59 in Paris plus a volume (no free allowance), Railway $5 with RAM at $10/GB-month. Koyeb's pages disagree with each other.
- **Free tiers**: only Oracle Always Free is always on with a disk and WebSockets. But it reclaims idle instances, and a low-traffic chessop would match its idle rule. Render and Koyeb free sleep and have no disk. Google's free VM is US-only. Hugging Face needs PRO. PythonAnywhere's WebSocket support is experimental.
- **Static + Pyodide**: about 7.8 MB first load, about 1 s startup (measured in Node). python-chess 1.11 has no Pyodide-ready package, so we would build and host our own. Contradicts ADR 0002 and 0004. GitHub Pages bars SaaS-style use; Cloudflare Pages is fine. Accounts would need Supabase or Turso free.
- **Game portals**: only itch.io fits. It allows HTTPS/WebSocket calls to our own server and has no SDK or ads, but discourages third-party logins and redirects. Poki and CrazyGames impose their SDK or accounts. Newgrounds could not be verified.
- **Domains**: OVH .fr €4.99 HT the first year, then €7.79; .org €12.99 renewal. Porkbun .org or .app about $12–15 renewal (no .fr). Gandi renews at 2–3× those prices.
- **Weakly sourced**: Hetzner's IPv4 surcharge, Koyeb's plans, Newgrounds. itch.io pages were read through Internet Archive captures.
