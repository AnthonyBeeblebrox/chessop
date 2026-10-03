# Hosting options for a public chessop

Research question: what does each hosting route actually offer and cost today for chessop as it runs now (one FastAPI + uvicorn process, the ~1.4 MB compressed snapshot held in memory, one WebSocket per browser tab, SQLite on disk; ADR 0004), run by a private individual in France for tens of concurrent learners on about €10/month or less? Date: 2026-09-29. Every source below was accessed on 2026-09-29 unless stated. Prices are as the provider shows them; "HT" means excluding VAT (French VAT is 20 %).

Context this does not change: ADR 0002 and ADR 0004 describe chessop as a local, single-learner tool and say a hosted deployment is "doubly ruled out". Going public means revisiting those ADRs, and accounts/multi-learner storage are outside this note. This note only prices the routes.

## Summary

1. **Measured footprint:** a running `chessop serve` with the packaged snapshot holds **~78 MB RSS** (measured on this machine, Python 3.12, one learner, idle). A 512 MB instance is enough for the process; 1 GB or more leaves room for the OS, many sockets and a SQLite page cache.
2. **Cheapest good fit is a small EU VPS, €4.50 to €6.60 a month with VAT.** OVH VPS-1 (France: Gravelines, Roubaix, Strasbourg; 2 vCore, 4 GB, 40 GB NVMe, unlimited traffic) is €4.49 HT/month with no commitment, €3.81 HT on a 12-month commitment. Hetzner CX23 (2 vCPU, 4 GB, 40 GB, 20 TB traffic; Germany/Finland) went up on 2026-06-15 to €5.49 HT plus IPv4. Scaleway DEV1-S (Paris, 2 GB) is €6.55 HT **plus** ~€3.65 for IPv4 plus storage, so ~€10+. DigitalOcean's $4 droplet has only 512 MiB and 10 GiB.
3. **PaaS always-on costs about the same or more, and disks are extra:** Render Starter $7/month (512 MB, 0.5 CPU) + disk $0.25/GB, Hobby workspace includes only 5 GB bandwidth then $0.15/GB. Fly.io shared-cpu-1x 1 GB in Paris ≈ $3.59/month + volume $0.15/GB + $2 dedicated IPv4 if wanted. Railway Hobby $5/month including $5 of usage (RAM $10/GB-month, so ~0.25 GB always-on fits in the credit). Koyeb's pricing page now sells only Pro at $29/month; not a €10 option for a new account.
4. **Free tiers that could actually run this app are few.** Oracle Always Free (Ampere A1 ≈ 2 OCPU / 12 GB, 200 GB block, 10 TB egress) is the only one with always-on compute, a real disk and WebSockets, but idle instances are reclaimed (CPU p95, network and memory all under 20 % over 7 days), even after upgrading to Pay As You Go. Render free sleeps after 15 minutes (≈1 minute cold start) and cannot attach a disk. Koyeb free sleeps after 1 hour, no volumes, Frankfurt/Washington only. Google's e2-micro free tier is US regions only. Hugging Face now requires PRO ($9/month) to create a Docker Space; free CPU Basic sleeps after 48 h and its disk is ephemeral. PythonAnywhere's ASGI hosting is "experimental", command-line only, and free web apps must be renewed monthly.
5. **Static hosting + chess logic in the browser is feasible and cheap but reverses ADR 0004.** Pyodide 314.0.7 costs ~6.2 MB on the wire (wasm 3.4 MB + stdlib 2.5 MB, brotli/gzip) plus the chess wheel (148 KB) and the snapshot (1.38 MB): **~7.8 MB first load**, cached afterwards. Measured in Node 24: Pyodide boot ~960 ms, `import chess` ~65 ms, legal-destinations for a position ~0.04 ms. python-chess 1.11.x ships only an sdist on PyPI, so it must be served as a self-built wheel. GitHub Pages (1 GB, 100 GB/month soft) forbids SaaS/commercial use; Cloudflare Pages free gives 500 builds/month, 20,000 files, 25 MiB per file. Accounts would need Supabase (free: 500 MB DB, 50,000 MAU, pauses after 7 days idle) or Turso (free: 5 GB, 500 M rows read / 10 M written per month).
6. **Browser game portals are a poor fit except itch.io.** itch.io hosts a ZIP (≤1,000 files, ≤500 MB) in an iframe and its docs explicitly allow talking to an API on another domain over HTTPS; its guidelines discourage third-party logins and redirecting traffic. Poki is hand-picked, web-exclusive, blocks all external requests by default and forbids email/Google logins. CrazyGames requires its SDK and account-linked progress for Full Launch and targets entertainment games. Newgrounds accepts open HTML5 ZIP uploads judged by community vote (primary pages were not reachable, see below).
7. **Domains:** OVH is cheapest for .fr (€4.99 HT first year, €7.79 HT renewal) and .org (€12.49 / €12.99 HT); Porkbun is cheapest for .org ($7.98 / $11.84) and .app ($8.75 / $14.93) but does not sell .fr; Gandi renews at €23.98 (.fr), €31.98 (.org), €40.00 (.app) HT; Cloudflare sells .org and .app at registry cost but shows prices only in its dashboard and has no .fr page.

## What chessop needs from a host

- One long-lived Python process (uvicorn, single async worker, all state in memory). Anything that scales to zero loses in-flight rounds and forces a cold start of Python + snapshot load.
- WebSockets that stay open for the length of a session (ADR 0004: one per tab, the server pushes).
- A persistent filesystem for SQLite. Object-store mounts and ephemeral container disks are not safe for SQLite.
- Memory: ~78 MB RSS measured (`ps` on `chessop serve` with the packaged `snapshot.graph.json.gz` 945,694 B + `snapshot.explanations.json.gz` 431,852 B, 2026-09-29). Per-learner growth with tens of learners is not measured; the current app is single-learner.
- Bandwidth: small. The page, chessground and the pieces are static and cacheable; a round is a handful of small JSON messages.

## VPS

| Provider | Smallest sensible plan | Price | RAM / CPU / disk | EU location | Traffic |
|---|---|---|---|---|---|
| OVHcloud | VPS-1 (VPS 2027) | €4.49 HT/month no commitment; €4.26 on 6 months; €3.81 HT (€4.57 TTC) on 12 months | 4 GB / 2 vCore / 40 GB NVMe, daily backup | Gravelines, Roubaix, Strasbourg (FR), Germany, UK, Warsaw, Milan; "Local Zone" variant (Paris absent; Marseille, Amsterdam, Brussels, …) at €5.49 HT | Unlimited, 500 Mbit/s |
| Hetzner | CX23 (x86) / CAX11 (Arm) | €5.49 / €5.99 HT per month since 2026-06-15 (was €3.99 / €4.49), plus IPv4 | 4 GB / 2 vCPU / 40 GB NVMe | Falkenstein, Nuremberg (DE), Helsinki (FI) | 20 TB |
| Scaleway | DEV1-S | €6.55 HT/month (€0.00898/h) + IPv4 €0.005/h (~€3.65) + block storage ~€0.095/GB-month | 2 GB / 2 vCPU | Paris, Amsterdam, Warsaw | Egress included, 200 Mbps |
| Scaleway | STARDUST1-S | €0.43 HT/month + IPv4 + storage | 1 GB / 1 vCPU, 10 GB max volume | Paris: availability "shortage"; Amsterdam: "scarce" | 100 Mbps |
| DigitalOcean | Basic $4 / $6 | $4 / $6 per month | 512 MiB, 10 GiB SSD / 1 GiB, 25 GiB SSD | Amsterdam, Frankfurt, London | 500 GiB / 1,000 GiB |

Notes:

- OVH prices come from OVH's public order catalogue API (`vps-2027-model1`: `default` 4.49 monthly, `upfront6` 4.26, `upfront12` 3.81; datacenters `GRA`, `SBG`, `EU-WEST-RBX`, `DE`, `UK`, `WAW`, `EU-SOUTH-MIL`, …). The marketing page's "À partir de 3,81 € HT/mois" is the 12-month-commitment price. Asia-Pacific VPS have a traffic quota; European ones are "Trafic illimité". [OVH VPS], [OVH catalogue API]
- Hetzner: the price-adjustment page lists CX23 €3.99 → €5.49 and CAX11 €4.49 → €5.99 (EU, monthly, excl. VAT and excl. IPv4), effective "15 June 2026; 8 AM CEST" for new orders and rescales. IPv6-only servers are possible, which avoids the IPv4 charge but leaves IPv4-only visitors out. The IPv4 surcharge (€0.50/month in secondary sources) was not found on a Hetzner page. [Hetzner price adjustment], [Hetzner cost-optimized], [Hetzner Primary IP FAQ]
- Scaleway: list prices "include egress and IPv6 addresses. Storage (local, block) and attached public IPv4 addresses are excluded." Availability read from Scaleway's public `products/servers/availability` API per zone. [Scaleway instances], [Scaleway network], [Scaleway storage], [Scaleway API]
- DigitalOcean: [DO droplets].

## PaaS

| Platform | Always-on small instance | WebSockets | Persistent disk | Sleep / cold start |
|---|---|---|---|---|
| Render | Starter $7/month: 512 MB, 0.5 CPU. Hobby workspace $0 + compute; 5 GB bandwidth included, then $0.15/GB | Yes, no fixed timeout; closed when the instance is replaced (deploy) | Paid services only, $0.25/GB-month; one instance only; disk prevents zero-downtime deploys | Paid instances do not sleep |
| Railway | Hobby $5/month includes $5 usage; RAM $10/GB-month, CPU $20/vCPU-month (per-second) | Not checked on a primary page | Volumes $0.15/GB-month | "Serverless" sleeping is opt-in; sleeps 5–10 min after the service stops *sending* packets; first request may get a 502 |
| Fly.io | shared-cpu-1x: 256 MB ≈ $3.42, 1 GB ≈ $3.59 per 30 days in Paris (cdg); Frankfurt ≈ $3.80 / $3.99 | Yes (plain TCP/HTTP proxy) | Volumes $0.15/GB-month of provisioned size | Machines can auto-stop/start; trial is 2 VM-hours or 7 days, then pay-as-you-go |
| Koyeb | Pricing page lists Pro $29/month (+ $10 compute included); nano 256 MB $2.68, micro 512 MB $5.36, eco-micro 512 MB $2.68 per month on top | Yes; WebSocket/gRPC streams up to 12 h with client keep-alives | Volumes on paid plans; not on free | Scale-to-zero after 5 min idle by default (1–5 s cold start, ~200 ms "light sleep" preview); a held WebSocket keeps it up |

Notes:

- Render: [Render pricing] (instance table, $0.25/GB disks, Hobby 5 GB bandwidth "then $0.15 per GB"), [Render WebSockets] ("Render doesn't impose a fixed timeout for WebSocket connections, but they close automatically when the instance is replaced"), [Render disks] ("You can attach a persistent disk to a paid Render web service…", "Adding a disk to a service prevents zero-downtime deploys"). Starter + 1 GB disk = $7.25/month; bandwidth beyond 5 GB is metered.
- Railway: [Railway pricing plans] (Free $1 credit/month, 0.5 GB RAM, 0.5 GB volume per service; Trial one-time $5; Hobby $5 with $5 usage; unit prices), [Railway serverless]. At $10/GB-month, a 256 MB process uses ~$2.50 of the $5 credit before CPU; actual CPU is billed on use.
- Fly.io: [Fly pricing] (region multipliers, volumes $0.15/GB, Europe egress $0.02/GB, dedicated IPv4 $2/month), [Fly trial].
- Koyeb: the pricing page shows only Pro/Scale/Enterprise and "Koyeb is joining Mistral AI". Its FAQ still says new sign-ups default to Pro with a $29 pre-authorisation and "can downgrade to the free Starter plan"; the two primary pages disagree, so treat Koyeb as $29/month minimum for a new account until verified in the console. [Koyeb pricing], [Koyeb FAQ], [Koyeb instances], [Koyeb scale-to-zero], [Koyeb edge network].

## Free tiers

| Offer | Compute | Sleep | Disk persistence | WebSockets | Reclamation / expiry |
|---|---|---|---|---|---|
| Oracle Cloud Always Free | 2× AMD micro (1/8 OCPU, 1 GB) or Ampere A1: **1,500 OCPU-h and 9,000 GB-h/month ≈ 2 OCPU + 12 GB** | None | 200 GB block (boot + volumes), home region only | Yes (it is a VM) | Idle instances reclaimed when, over 7 days, CPU p95 < 20 %, network < 20 % and (A1) memory < 20 %; upgrading to Pay As You Go does **not** exempt them. 10 TB/month egress |
| Render free | 512 MB, < 1 CPU; 750 instance-hours/month per workspace | Spins down after 15 min without inbound HTTP or WebSocket messages; ~1 min to wake with a loading page | No persistent disk; local files lost on spin-down | Yes; messages count as activity | Free Postgres expires after 30 days |
| Koyeb free | One per org: 512 MB, 0.1 vCPU, 2 GB SSD; Frankfurt or Washington | Scale to zero after 1 h without traffic (not configurable) | No volumes | Yes | Requires a card; account model in flux (see PaaS) |
| Google Cloud e2-micro | 1 non-preemptible e2-micro, 30 GB standard disk | None | Yes | Yes | **US regions only** (us-west1, us-central1, us-east1); 1 GB egress/month from North America |
| Hugging Face Spaces | CPU Basic 2 vCPU / 16 GB, free hardware | Sleeps after 48 h without use; visitors wake it | Container disk is ephemeral; persist via Storage Buckets mounted as volumes (object storage: unsafe for SQLite) | Docker Space on ports 80/443/8080 | **Creating a Docker or Gradio Space now needs PRO ($9/month)**; static Spaces free |
| PythonAnywhere Beginner | 1 web app at `user.pythonanywhere.com`, 512 MB disk, restricted outbound internet | Free web apps stop unless renewed ("Run until 1 month from today") | Yes | ASGI (FastAPI) and WebSockets only via the "experimental", command-line-only ASGI system; free-plan status of ASGI undecided | Developer plan $10/month |

Notes:

- Oracle: [OCI Always Free] quotes the A1 allowance as "1,500 OCPU hours and 9,000 GB hours per month… equivalent to 2 OCPUs and 12 GB of memory", block storage 200 GB total, outbound 10 TB/month, and the reclamation rule. A chessop instance with tens of learners will sit far below 20 % CPU, so it is exactly what gets reclaimed; a cron job burning CPU to dodge the rule is against the spirit of the offer. Paris and Marseille home regions exist, but Always Free resources must live in the home region.
- Render: [Render free] ("Render spins down a Free web service that goes 15 minutes without receiving any inbound traffic. This includes both HTTP requests and WebSocket messages from existing connections… This process takes about one minute.").
- Koyeb: [Koyeb instances] ("Each organization is limited to one Free Instance", Frankfurt or Washington, "scale down to zero when they don't receive any traffic for 1 hour", no Volumes); [Koyeb scale-to-zero].
- Google: [GCP free tier].
- Hugging Face: [HF Spaces overview] ("Static Spaces are free for everyone. Gradio and Docker Spaces run on compute and require a paid plan to create: PRO for personal accounts…"), [HF Spaces GPUs] (48 h sleep), [HF Spaces storage] ("This disk space is ephemeral"), [HF pricing] (PRO $9/month).
- PythonAnywhere: [PA pricing], [PA ASGI] ("deployment of ASGI (and other async) websites on PythonAnywhere is an experimental feature", "We're 99.9% certain that there will be a way to host them in a free plan"), [PA forum 35690] (staff: WebSockets "experimental and command-line only"), [PA forum 36620] (the 1-month renewal).

## Static hosting with chess logic in the browser

This route drops the Python server: the snapshot, sampling, memory model and python-chess run in the browser under Pyodide, progress lives in IndexedDB, and an optional backend holds accounts. It contradicts ADR 0004 ("The browser holds no chess logic") and ADR 0002's server-authoritative thin client, so it is a redesign, not a deploy.

**Pyodide cost, measured 2026-09-29** against `https://cdn.jsdelivr.net/pyodide/v314.0.7/full/` (current version per [Pyodide deploying]; Python 3.14.2 per its `pyodide-lock.json`):

| File | Raw | On the wire (br/gzip) |
|---|---|---|
| `pyodide.asm.wasm` | 9,598,218 B | 3,438,516 B |
| `python_stdlib.zip` | 2,545,637 B | 2,505,313 B |
| `pyodide.asm.mjs` | 1,250,344 B | 262,041 B |
| `pyodide-lock.json` | 119,077 B | 24,708 B |
| `pyodide.js` | 18,912 B | 7,613 B |
| chess 1.11.2 wheel (self-built, pure Python) | 148,423 B | (already zipped) |
| chessop snapshot (graph + explanations, gzip) | 1,377,546 B | (already gzipped) |
| **Total** | | **≈ 7.8 MB** |

- That is ~6 s on a 10 Mbit/s line and ~1.3 s at 50 Mbit/s for the first visit; the CDN files are cached by the browser afterwards. `micropip` (111 KB) is not needed if the wheel is unzipped into `site-packages` directly.
- Timings in Node 24 on this machine (3 runs): `loadPyodide()` 955–985 ms, `import chess` 63–65 ms, computing the legal-destinations map and a push/pop 0.042–0.044 ms per position. Browsers compile the wasm similarly but mobile CPUs will be slower; not measured in a browser.
- PyPI's `chess` 1.11.0–1.11.2 ship only sdists (1.11.2 is a 6.1 MB sdist); 1.10.0 was the last with a `py3-none-any` wheel. micropip installs wheels, so chessop would build and host its own wheel. [PyPI chess JSON]
- **GitHub Pages:** sites ≤ 1 GB, soft 100 GB/month bandwidth, soft 10 builds/hour; the page rules out using Pages to run an online business, e-commerce or commercial SaaS, and sites should not handle sensitive data such as passwords. A free, non-commercial trainer is within bounds; logins would go through a third-party backend. [GitHub Pages limits]
- **Cloudflare Pages (free):** 500 builds/month, 20,000 files per site, 25 MiB per asset, no bandwidth cap stated; Cloudflare now points new static sites toward Workers Static Assets. [Cloudflare Pages limits]
- **Free account backends:** Supabase free: 500 MB database, 50,000 MAU auth, 5 GB egress, 2 active projects, projects "pause after 1 week of inactivity"; Pro from $25/month. [Supabase pricing]. Turso free: 100 databases, 5 GB, 500 M rows read and 10 M rows written per month; Developer $4.99/month; no auth product on the pricing page. [Turso pricing]

## Browser game platforms

| Platform | How a web build is hosted | Network / external site | Obligations | Fit for a training tool |
|---|---|---|---|---|
| itch.io | ZIP with `index.html` (≤ 1,000 files, ≤ 500 MB, ≤ 200 MB per file) shown in an iframe on the project page | Docs: "If your project tries to load files or talk to an API on another domain, then that domain must be requested with HTTPS". So a `wss://` socket to our own server, or an iframe of our HTTPS site, is allowed by the docs (not tested live) | None mandatory; HTML5 projects take payments as donations only; guidelines: "Avoid obtrusive advertisements or third-party logins", avoid "trying to redirect traffic to a third-party service", "Prefer uploading your files directly to itch.io" | Good: free, accepts tools and non-games, no SDK. A page that only frames an external site is tolerated technically but discouraged |
| Poki | Hand-picked; submit through Poki for Developers | "Poki blocks all external requests by default"; external multiplayer servers "fine once approved"; no external CDNs or fonts | Poki SDK and ads; web exclusivity ("you can't publish the same game on other web portals"); 50/50 revenue on Poki traffic; "No email-based logins, no Google or Facebook sign-in" | Poor: curated for entertainment games, no own accounts |
| CrazyGames | Upload; Basic Launch then Full Launch | Backends not addressed on the pages read; sitelock must whitelist their domains | Full Launch requires the SDK (gameplay start/stop events, SDK-only ads, progress linked to a CrazyGames account); initial download ≤ 50 MB (20 MB for mobile homepage), total ≤ 250 MB, ≤ 1,500 files; PEGI 12; "Only games that prioritize quality and gameplay" | Poor: game-first, accounts must be CrazyGames' |
| Newgrounds | Open upload of an HTML5 ZIP, then public "Judgment" by vote; games need no scouting | Not verified | Newgrounds.io API is available, not shown to be mandatory | Possible but audience is entertainment-first |

Notes: [itch.io HTML5 docs] and [itch.io quality guidelines] were read through Internet Archive captures of 2026-09-26 because itch.io returned a bot challenge; [Poki working with Poki], [Poki external resources]; [CrazyGames requirements], [CrazyGames technical], [CrazyGames gameplay]. Newgrounds' own wiki returned HTTP 403 to every fetch; the Newgrounds lines rest on the fan wiki [Wikigrounds submission] (HTML5 ZIP up to 3,000 MB, judgment by vote), which flags itself as out of date. Treat them as unverified.

## Domain registrars (per year)

| TLD | OVHcloud (HT) | Gandi (HT, France) | Porkbun (USD) | Cloudflare |
|---|---|---|---|---|
| .fr | €4.99 first year, €7.79 renewal | €6.00 first year, €23.98 renewal (€21.58 on 2–9 years) | not offered | no .fr product page (404); not confirmed |
| .org | €12.49 first year (Sept–Nov 2026 promo), €12.99 renewal | €7.99 first year (promo), €31.98 renewal | $7.98 first year, $11.84 renewal | registry cost, no markup; price shown only in the dashboard |
| .app | €14.09 first year (Q3 2026 promo), €18.09 renewal | €8.99 first year (promo), €40.00 renewal | $8.75 first year, $14.93 renewal | registry cost, no markup; price shown only in the dashboard |

Sources: OVH public domain catalogue API (`create-default` and `renew` pricings) [OVH domain catalogue]; Gandi TLD pages with "Prices for France, Taxes excluded" [Gandi .fr], [Gandi .org], [Gandi .app]; Porkbun public pricing API [Porkbun pricing API]; Cloudflare product pages [Cloudflare .org], [Cloudflare .app]. Renewal price is what matters after year one; .app is HSTS-preloaded (HTTPS only), which chessop's host would need anyway.

## Comparison

Monthly figures are what a learner-facing, always-on chessop would cost; VAT added where the provider bills French individuals in HT (×1.2).

| Route | €/month (approx., incl. VAT) | Always on | WebSockets | SQLite on real disk | Main catch |
|---|---|---|---|---|---|
| OVH VPS-1, Gravelines/Roubaix/Strasbourg | €5.39 (no commitment), €4.57 (12 months) | Yes | Yes | Yes (40 GB) | You run the OS, TLS, backups |
| Hetzner CX23 | ~€6.60 + IPv4 | Yes | Yes | Yes (40 GB) | Germany/Finland; price rose 38 % in June 2026 |
| Scaleway DEV1-S | ~€12+ (with IPv4, 10 GB block) | Yes | Yes | Yes | Over budget once IPv4 and storage are added |
| DigitalOcean $6 | ~$6 (+VAT) | Yes | Yes | Yes (25 GiB) | 1 GiB RAM, US company, USD |
| Render Starter + 1 GB disk | ~$7.25 + bandwidth over 5 GB | Yes | Yes | Yes | 512 MB; deploys drop sockets and are not zero-downtime |
| Fly.io 1 GB, cdg + 1 GB volume | ~$3.75 (+$2 IPv4 optional) | Yes (auto-stop optional) | Yes | Yes (volume) | Usage-billed; no free allowance |
| Railway Hobby | $5 (+ usage above $5) | Yes unless serverless | Not checked | Yes (volume) | Metered RAM at $10/GB-month |
| Koyeb | $29 minimum for a new account | Yes | Yes (≤ 12 h streams) | Paid only | Over budget |
| Oracle Always Free | €0 | Yes, until reclaimed | Yes | Yes (200 GB) | Idle reclamation; capacity and account approval |
| Render / Koyeb free | €0 | No (15 min / 1 h sleep) | Yes | No | Cold starts, data loss |
| Hugging Face Docker Space | $9 (PRO) | Sleeps after 48 h on free hardware | Yes | No (bucket mounts only) | Ephemeral disk |
| PythonAnywhere | €0 / $10 | Free: monthly renewal | Experimental | Yes | ASGI experimental, CLI only |
| Static (GitHub/Cloudflare Pages) + Pyodide | €0 (+ Supabase/Turso free for accounts) | n/a | n/a | Browser IndexedDB | ~7.8 MB first load; reverses ADR 0002/0004 |
| itch.io | €0 | Hosts the static build only | To our own server over HTTPS | n/a | Still needs a server or the Pyodide route |

## Sources

All accessed 2026-09-29.

- [OVH VPS]: https://www.ovhcloud.com/fr/vps/
- [OVH catalogue API]: https://eu.api.ovh.com/1.0/order/catalog/public/vps?ovhSubsidiary=FR
- [OVH domain catalogue]: https://eu.api.ovh.com/1.0/order/catalog/public/domain?ovhSubsidiary=FR
- [Hetzner price adjustment]: https://docs.hetzner.com/general/infrastructure-and-availability/price-adjustment/
- [Hetzner cost-optimized]: https://www.hetzner.com/cloud/cost-optimized/
- [Hetzner Primary IP FAQ]: https://docs.hetzner.com/cloud/servers/primary-ips/faq/
- [Scaleway instances]: https://www.scaleway.com/en/pricing/virtual-instances/
- [Scaleway network]: https://www.scaleway.com/en/pricing/network/
- [Scaleway storage]: https://www.scaleway.com/en/pricing/storage/
- [Scaleway API]: https://api.scaleway.com/instance/v1/zones/fr-par-1/products/servers and `/products/servers/availability` (also nl-ams-1, pl-waw-1, fr-par-2)
- [DO droplets]: https://www.digitalocean.com/pricing/droplets
- [Render pricing]: https://render.com/pricing
- [Render free]: https://render.com/docs/free
- [Render WebSockets]: https://render.com/docs/websocket
- [Render disks]: https://render.com/docs/disks
- [Railway pricing plans]: https://docs.railway.com/reference/pricing/plans (and https://railway.com/pricing)
- [Railway serverless]: https://docs.railway.com/reference/app-sleeping
- [Fly pricing]: https://docs.fly.io/about/pricing/
- [Fly trial]: https://docs.fly.io/about/free-trial/
- [Koyeb pricing]: https://www.koyeb.com/pricing
- [Koyeb FAQ]: https://www.koyeb.com/docs/faqs/pricing
- [Koyeb instances]: https://www.koyeb.com/docs/reference/instances
- [Koyeb scale-to-zero]: https://www.koyeb.com/docs/run-and-scale/scale-to-zero
- [Koyeb edge network]: https://www.koyeb.com/docs/reference/edge-network
- [OCI Always Free]: https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm
- [GCP free tier]: https://docs.cloud.google.com/free/docs/free-cloud-features
- [HF Spaces overview]: https://huggingface.co/docs/hub/spaces-overview
- [HF Spaces GPUs]: https://huggingface.co/docs/hub/spaces-gpus
- [HF Spaces storage]: https://huggingface.co/docs/hub/spaces-storage
- [HF pricing]: https://huggingface.co/pricing
- [PA pricing]: https://www.pythonanywhere.com/pricing/
- [PA ASGI]: https://help.pythonanywhere.com/pages/ASGICommandLine/
- [PA forum 35690]: https://www.pythonanywhere.com/forums/topic/35690/
- [PA forum 36620]: https://www.pythonanywhere.com/forums/topic/36620/
- [Pyodide deploying]: https://pyodide.org/en/stable/usage/downloading-and-deploying.html (file sizes measured from https://cdn.jsdelivr.net/pyodide/v314.0.7/full/ and npm `pyodide@314.0.7`)
- [PyPI chess JSON]: https://pypi.org/pypi/chess/json
- [GitHub Pages limits]: https://docs.github.com/en/pages/getting-started-with-github-pages/github-pages-limits
- [Cloudflare Pages limits]: https://developers.cloudflare.com/pages/platform/limits/
- [Supabase pricing]: https://supabase.com/pricing
- [Turso pricing]: https://turso.tech/pricing
- [itch.io HTML5 docs]: https://itch.io/docs/creators/html5 (via https://web.archive.org/web/20260926024022/https://itch.io/docs/creators/html5)
- [itch.io quality guidelines]: https://itch.io/docs/creators/quality-guidelines (via Internet Archive, 2026 capture)
- [Poki working with Poki]: https://developers.poki.com/guide/working-with-poki
- [Poki external resources]: https://developers.poki.com/guide/external-resources-policy
- [CrazyGames requirements]: https://docs.crazygames.com/requirements/intro/
- [CrazyGames technical]: https://docs.crazygames.com/requirements/technical/
- [CrazyGames gameplay]: https://docs.crazygames.com/requirements/gameplay/
- [Wikigrounds submission]: https://newgrounds.wiki.gg/wiki/Submission_to_Newgrounds (secondary, self-flagged as outdated)
- [Gandi .fr]: https://www.gandi.net/en/domain/tld/fr
- [Gandi .org]: https://www.gandi.net/en/domain/tld/org
- [Gandi .app]: https://www.gandi.net/en/domain/tld/app
- [Porkbun pricing API]: https://api.porkbun.com/api/json/v3/pricing/get
- [Cloudflare .org]: https://www.cloudflare.com/application-services/products/registrar/buy-org-domains/
- [Cloudflare .app]: https://www.cloudflare.com/application-services/products/registrar/buy-app-domains/
