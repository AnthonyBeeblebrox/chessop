# chessop in public: build-ready spec

Status: ready-for-agent
Map: [chessop in public](map.md)

Synthesised on 2026-10-02 from the map's sixteen resolved tickets, ADRs 0002, 0003, 0004, 0007 and 0008 with their amendments, and the glossary (`CONTEXT.md`). It decides nothing new except the few gaps listed under [Further Notes](#further-notes), each marked as such. **Where two sources disagree, the later one wins.** The v1 spec (`.scratch/chessop/spec.md`) still describes everything this document does not change: the repertoire rule, the memory model, the sampling rule, the Score, the wire protocol, the progress view.

Sources, by ticket: [01 hosting options](issues/01-hosting-options.md), [02 open-ended bands](issues/02-open-ended-bands.md), [03 hosting decision](issues/03-hosting-decision.md), [04 many learners](issues/04-many-learners.md), [05 sign-in](issues/05-sign-in.md), [06 French law](issues/06-french-legal.md), [07 mobile and PWA](issues/07-mobile-and-pwa.md), [08 help](issues/08-help-explanations.md), [09 monitoring](issues/09-monitoring.md), [10 legal pages and data rights](issues/10-legal-pages-and-data-rights.md), [11 hosted-mode seam](issues/11-hosted-mode-seam.md), [12 abuse and limits](issues/12-abuse-and-limits.md), [13 deploying](issues/13-deploying.md), [14 operating](issues/14-operating.md), [15 latency](issues/15-latency.md), [16 discovery](issues/16-discovery.md).

## Problem Statement

chessop only runs on the machine of someone who can install a Python tool from a repository. Nobody else can drill with it: there is no URL to open, nothing to keep a second person's history apart from the first's, no way to carry progress from a laptop to a phone, and the play page is laid out for a desktop with a keyboard. The one rating band a learner gets is the closed band their declared rating maps to, so a 1600 learner cannot drill against what stronger players really play. A stranger who did reach the app would meet Score, Known and the verdict with nothing to explain them. And the owner, who lives in France, has no hosting, no legal pages, no way to see whether the site is up or used, and no way to accept a tip toward the bill.

## Solution

chessop gains a **hosted mode** beside the local one, in one codebase. Anyone opens `https://chessop.fr` on a desktop or a phone and drills at once, as an anonymous learner, at the new default band 1500+. Their history is kept on the server behind a cookie. If they want it on other devices they sign in with Lichess or an email magic link, and the account adopts the anonymous history. The pages work on a phone and install as an app. A help page explains every figure. The site carries the legal notice, privacy notice and data rights French and EU law require, with no cookie banner because nothing needs consent. The owner runs it on one small French VPS for about €5.40 a month, deploys by hand with a script, gets alerted when it breaks, sees visitor and learning figures, and links a Ko-fi page. `chessop` run locally stays what it was: one learner, offline, no account, plus the new bands, the phone layout and the help page.

## User Stories

### Visiting and drilling anonymously

1. As a visitor, I want to open `chessop.fr` and be playing a round with no sign-up and no question asked, so that I can try the drill in seconds.
2. As a visitor, I want my rounds remembered on this browser without creating an account, so that the opponent steers toward what I know least from my second round on.
3. As an anonymous learner, I want to be told once, after my first round, that my progress lives in this browser and that signing in keeps it elsewhere, so that I am not surprised when clearing cookies loses it.
4. As a visitor who only looks at a page and never plays, I want nothing stored about me, so that browsing costs me no data.
5. As an anonymous learner, I want my settings (rating band, widths, openings, sound, animation) to be mine alone, so that another visitor's choices never change my drill.
6. As a learner, I want my day to end at my own midnight, so that the daily Score and "change since your last day" follow my time zone and not the server's.
7. As a learner, I want to play in several tabs or on several devices at once, so that I never have to close one to use another.
8. As a visitor from a network that has created too many new learners in the last hour, I want to still be able to play, with a clear notice that this round will not be saved, so that a shared network does not lock me out.
9. As a visitor arriving when the site is full, I want a plain "chessop is full right now, try again in a few minutes", so that I know it is not broken.

### Rating bands

10. As a learner, I want to choose an open band such as 1500+, so that I drill against the moves of everyone at or above that rating, stronger players included.
11. As a learner, I want the closed bands to stay available, so that I can still drill against exactly my peers.
12. As a new learner, I want the band to default to 1500+ without being asked my rating, so that I start with a sensible repertoire.
13. As a v1 learner who had declared a rating, I want to stay on the closed band it mapped to after upgrading, so that my repertoire does not move under me.
14. As a v1 learner who had declared nothing, I want to be told once that my band is now 1500+ and my repertoire was regenerated, so that the change is not silent, and I want my position records untouched.
15. As a learner, I want to pick the band from a list in settings rather than typing a rating, so that the choice is one setting, not two.

### Signing in and accounts

16. As an anonymous learner, I want to sign in with my Lichess identity in two clicks, so that I need no new credentials.
17. As a learner without a Lichess account, I want to sign in with an email magic link, so that I am never asked for a password.
18. As a learner reading mail on my phone while drilling on my laptop, I want a 6-digit code in the same email, so that I can finish signing in on the laptop.
19. As a learner, I want the link in the email to open a confirm button rather than sign me in directly, so that a mail scanner pre-fetching the link does not spend it.
20. As a learner signing in for the first time, I want my anonymous history to become my account's history with no prompt, so that committing to the site never throws progress away.
21. As a learner signing in on a second device that already has anonymous history, I want the two histories merged, each position keeping the record with the later last pass, so that neither device's work is lost.
22. As a signed-in learner, I want to stay signed in for a year from my last visit, so that I rarely sign in again.
23. As a signed-in learner, I want the header to show my Lichess username or email and lead to an account page, so that I can see who I am signed in as.
24. As a signed-in learner on a shared computer, I want sign-out to leave no learner on the browser, so that the next person starts fresh and never sees my history.
25. As an email account holder, I want to change my address, confirmed by a link sent to the new one, so that I keep my history when I change mailbox.
26. As an account holder, I want to delete my account at once from the account page, so that my history, identity and every session on every device are gone immediately.
27. As a learner who typed the wrong address, I want the same "check your inbox" answer whatever the address, so that the site never reveals who has an account.
28. As a learner, I want Lichess to be asked for nothing beyond my identity, and the token thrown away at once, so that chessop can do nothing on Lichess in my name.
29. As a local-mode learner, I want no sign-in link, cookie or notice, so that the local app stays the offline single-learner tool it was.

### Phone and installed app

30. As a learner on a phone, I want the board as wide as the screen with the verdict and a big Next round button under it, so that I can drill one-handed in portrait.
31. As a learner on a phone, I want dragging a piece never to scroll or zoom the page, so that moves land where I drop them.
32. As a learner on a phone, I want tap-to-move as well as drag, so that I can move on a small board.
33. As a learner on a phone, I want icon buttons for sound, progress and settings in the header, so that I have touch equivalents for what the keyboard does on desktop.
34. As a learner holding the phone in landscape, I want the board on the left at full height and the rest in a column beside it, so that the board stays as large as it can.
35. As a learner on a phone, I want the progress table cut to opening, Score, White and Black, with the actions appearing when I open a row, so that it fits the screen.
36. As a learner, I want to install chessop to my home screen and have it open full-screen, so that it feels like an app.
37. As a learner with the app installed and no connection, I want a page saying chessop needs a connection with a Try again button, so that I do not face a browser error.
38. As a learner on 4G whose socket drops, I want the page to reconnect by itself and tell me the cut round was not counted, so that I never stare at a dead board or get charged a miss I did not make.
39. As a learner on a slow connection, I want a "waiting for the server…" hint after a second of silence, so that I know my move was sent.
40. As a desktop learner, I want the desktop layout and keys unchanged, so that nothing I am used to moves.

### Understanding the figures

41. As a new learner, I want one help page explaining how a round works, the verdict, Score, Known, and every other figure, so that I can make sense of what I see.
42. As a learner on the progress view, I want each figure's label to link to its help section, so that the explanation is one tap away.
43. As a learner who has just finished a round, I want "what does this mean?" and "what is the Score?" links under the verdict, so that help is offered at the moment I wonder.
44. As a learner, I want the help page to quote the running sure threshold and target success range, so that the explanation matches the app's actual settings.
45. As a learner with a question or a bug, I want a contact address and a pointer to the issue tracker on the help page, so that I can reach the owner.
46. As a local-mode learner, I want the help page too, so that the local app explains itself.

### Privacy, legal and data rights

47. As a visitor in the EU, I want no cookie banner because nothing on the site needs my consent, so that I am not nagged.
48. As a visitor, I want a privacy notice a teenager can read, naming who controls my data, what is kept, why, for how long and who receives it, so that I can decide whether to play.
49. As a visitor, I want a legal notice naming the host, so that the site meets French law while the owner's address stays private.
50. As a learner, signed in or anonymous, I want to download everything chessop holds about me as one JSON file, so that I can exercise my right of access.
51. As an anonymous learner, I want a "Forget this browser's history" button, so that I can erase my data without an account.
52. As a visitor, I want to opt out of audience statistics with one toggle, and to have Do Not Track and Global Privacy Control honoured, so that I am not counted if I do not want to be.
53. As a learner who stops coming, I want my data deleted after a stated period of inactivity, so that it is not kept forever.
54. As an email account holder who has been away for 23 months, I want one warning email before deletion, so that I can keep my history by visiting.
55. As a learner who deleted their data, I want it gone from backups within 30 days, so that deletion means deletion.
56. As a visitor, I want the server to keep no access logs and never log my IP, so that my visits leave no trace beyond what the notice lists.
57. As a visitor on any hosted page, I want footer links to the legal notice, privacy notice, source and Ko-fi, so that these are always one click away.

### Finding and supporting chessop

58. As someone who sees a chessop link in a chat, I want a preview with a title, a one-line pitch and an image, so that I know what it is before clicking.
59. As someone searching for opening drills, I want the home and help pages indexable and every private page marked `noindex`, so that search results show the useful pages only.
60. As a visitor who types `www.chessop.fr` or `http://`, I want to land on `https://chessop.fr`, so that there is one address.
61. As a grateful learner, I want a Ko-fi link in the footer and on the progress page, with a line saying tips pay for the server and domain and are not tax-deductible, so that I can chip in knowingly.
62. As a developer, I want the source linked from the site and a README that leads with the site, then local install, then hosting my own, so that I can read, run or host chessop myself.

### Owning and operating the site

63. As the owner, I want one flag, `--hosted`, plus environment variables to switch a server into hosted mode, so that local and hosted stay one codebase with one branch point.
64. As the owner, I want a missing required variable to stop startup and list every missing name, so that a misconfigured server never half-starts.
65. As the owner, I want hosted mode to run on `http://localhost` with emails printed to the console, so that I can rehearse sign-in and deploys without the VPS or a mail key.
66. As the owner, I want a `provision.sh` that sets a fresh Debian 13 VPS up idempotently, so that the box can be rebuilt from the repository.
67. As the owner, I want `publish.sh` to turn a tagged private commit into one squashed public commit, refusing if tests fail or a secret pattern is found, so that the public repository never holds private history or a token.
68. As the owner, I want `deploy.sh` to deploy a tagged, CI-green release with a pre-deploy database backup and to roll the symlink back by itself if the health check fails, so that a bad release does not take the site down.
69. As the owner, I want CI to run the linter and tests on every public push and tag and never deploy, so that a release only ships when I choose.
70. As the owner, I want one nightly `chessop maintain` job that writes the usage aggregate, sends account warnings, runs the purges and takes the backup, so that the site stays legal with nothing to remember.
71. As the owner, I want a nightly encrypted off-site copy of the database that expires after 30 days, uploaded with a key that can only write, so that losing the VPS loses at most a day and a stolen key leaks nothing.
72. As the owner, I want an email when the service fails, when the disk passes 80 %, and a daily digest of errors only when there are any, so that I hear about problems without watching a dashboard.
73. As the owner, I want an external uptime check on a health endpoint that is green only when the database answers and the snapshot is loaded, so that I am alerted even when the VPS cannot send mail.
74. As the owner, I want cookieless page-view statistics from a self-hosted GoatCounter, so that I see traffic without sending anything to a third party.
75. As the owner, I want a `chessop stats` command over SSH printing active and new learners, rounds, success rate, sign-ins, adoptions, retention, band and opening mix and snapshot versions, so that I can tell whether anyone uses the site.
76. As the owner, I want a counts-only daily aggregate that survives deletions, so that the usage history stays stable while holding no personal data.
77. As the owner, I want limits on sessions, sockets, requests, new learners and emails, so that one abusive client cannot exhaust a €4.49 box or the mail quota.
78. As the owner, I want every move handled under 10 ms at p95 with 30 learners playing, and a kept load-test script to prove it on the VPS before launch, so that the drill stays fast in public.
79. As the owner, I want a runbook with the first-time setup in dependency order and the routine procedures (deploy, restore, rotate a key, answer a data request, handle a breach), so that I can operate the site months later without rediscovering it.
80. As the owner, I want a one-page record of processing in the public repository, so that the GDPR paperwork exists and is honest.
81. As the owner, I want a new snapshot to ship only with a release, each learner seeing the regeneration notice once on their next visit, so that a data refresh never touches position records or surprises anyone twice.

## Implementation Decisions

### 1. Two modes, one branch point

- `chessop` with no arguments and `chessop serve` without `--hosted` are **local mode**, unchanged in behaviour: one implicit learner, no cookie, bound to localhost with the free-port fallback, browser opened.
- `chessop serve --hosted` is **hosted mode**. The CLI builds one hosted-settings object from the environment (or none) and hands it to the app factory. The code tests the mode at **three seams only**:
  1. **The current-learner dependency**, used by every page route and the WebSocket: the implicit learner locally; the cookie learner hosted.
  2. **A hosted-only router**, mounted only in hosted mode: Lichess and email sign-in, sign-out, the account page, `/legal`, `/privacy`, `/data`, `robots.txt`.
  3. **The base template's `site` value**: footer (legal, privacy, source, Ko-fi), GoatCounter snippet, sign-in link or account name, Open Graph and canonical tags. No other template or route tests the mode. This requires introducing a shared base template that every page extends.
- **Environment variables**, read only under `--hosted` (and by the hosted-only commands in §13):

  | Variable | Meaning | Required |
  | --- | --- | --- |
  | `CHESSOP_BASE_URL` | the site's public URL, e.g. `https://chessop.fr` | always |
  | `CHESSOP_DATA_DIR` | data directory (already exists in v1) | on the VPS; default as in local mode |
  | `CHESSOP_MAIL_FROM` | sender, `login@chessop.fr` | always |
  | `CHESSOP_OWNER_EMAIL` | where owner alerts go | always |
  | `CHESSOP_TEM_SECRET_KEY`, `CHESSOP_TEM_PROJECT_ID` | Scaleway Transactional Email | when the base URL is `https` (gap G2) |
  | `CHESSOP_GOATCOUNTER_URL` | e.g. `https://stats.chessop.fr` | no: unset means no snippet (gap G3) |
  | `CHESSOP_BACKUP_*` | off-site bucket, write-only key, `age` recipient | no: unset means the upload is skipped and logged |

  A missing required variable stops startup with every missing name listed. `CHESSOP_BASE_URL` alone never turns hosted mode on. No TOML file.
- **Hosted bind**: `127.0.0.1`, port fixed (default 8000, no free-port fallback), no browser opened, no access log. Forwarded headers (`X-Forwarded-For`, `X-Forwarded-Proto`) are trusted from `127.0.0.1` only.
- **The base URL comes from configuration, never from the request's `Host`**: magic links, the Lichess `redirect_uri` and `client_id`, canonical links, Open Graph URLs and the manifest's absolute URLs all use it.
- **Development**: hosted mode runs on `http://localhost:8000`. On an `http` base URL the cookie drops `Secure`; with no TEM key every email (magic link, warning, owner alert) is printed to the console.
- **Served in both modes**: `/help`, the web app manifest, the service worker, the offline page, `/healthz`. **Hosted only**: account routes, legal pages, footer, analytics, link previews, `robots.txt`. Local mode has no footer.
- **Secrets**: the TEM key and the backup bucket's write-only key, both in the environment file. Session tokens, magic-link tokens and codes are random and stored as SHA-256 hashes; there is no signing key and nothing to rotate. Lichess uses PKCE with no client secret.

### 2. Rating bands and the snapshot

- **Eight bands**: the closed bands below 1200, 1200–1500, 1500–1800, 1800–2100, 2100+ stay; the open bands **1200+, 1500+, 1800+** are added (2100+ is both). Inside an open band means **both players at or above the bound**. A game counts toward every band both players fall in.
- The snapshot build keeps one game in several bands; the cap of 150,000 kept games per band, the storage cut-off, the filters, the ply cap and the file shapes are unchanged. The packaged snapshot is rebuilt with all eight bands (owner step, see Further Notes).
- **The learner chooses the band directly** from a list in settings. The declared rating and its mapping to a band are removed from settings, storage and UI.
- **Default band 1500+ in both modes.** A band absent from the loaded snapshot falls back to 1500+.
- **Snapshot change is per learner**: the snapshot version a learner's repertoire was generated from is a per-learner setting. On their first visit after a release with a new snapshot, that learner sees the existing regeneration notice once. Position records are untouched; records of positions the new repertoire drops go dormant and return if a later snapshot restores them.

### 3. Learners and storage

- **Still one SQLite file**, now in **WAL mode with `synchronous=NORMAL`** in both modes. Any copy of it goes through SQLite's backup API, never a file copy.
- **Schema** (forward-only migration): a learner table (id, created, last seen, snapshot version); position records, round log, daily score and settings each gain the learner id. New tables: account (learner, kind `lichess` or `email`, identity key, display name, created, `warned_at`), session (token hash, learner, created, last used, expiry), pending sign-in (token hash, code hash, email, the requesting browser's binding, expiry, tries, purpose sign-in or email-change), daily usage aggregate (§12).
- **Local mode** uses the same schema with one implicit learner. The migration attaches an existing v1 file's rows to that learner, and turns a stored declared rating into the closed band it mapped to; a file with no declared rating moves to 1500+ and the learner is told once (the snapshot-refresh rule: repertoire regenerates, records untouched). There is no import of local history into the hosted site.
- **Per-learner settings**: band, widths, opted-out openings, sound, animation, and a new **timezone**. The browser reports its IANA timezone in a new client-to-server message sent when the socket opens (`hello {tz}`); the server stores it when unset. It is editable in settings. Local mode uses the machine clock. The daily score's day is the learner's local day. A new learner gets the defaults (1500+, widths 2 and 3).
- **Model parameters are server-wide**, set by the owner, not shown as per-learner settings in hosted mode.
- **An anonymous learner** is a server-side record created at the learner's **first round** (not first page view; see gap G1 for settings), keyed by a random token in one cookie: `HttpOnly`, `Secure`, `SameSite=Lax`, 12 months, sliding. The cookie holds only that pointer. No history lives in the browser.
- **Last seen** is updated at most once a day per learner.
- **Deleting a learner** deletes their records, round log, daily scores, settings, account, sessions and pending sign-ins. No anonymised copy is kept.
- **The "progress lives in this browser" notice** is shown once to an anonymous learner after their first round, with a sign-in link.

### 4. In-process state (hosted)

- **Band graphs** load on first use and stay for the process's life (at most eight).
- **Repertoire, progress ledger and the repertoire-only steering caches** (counts, parents, below, weights) are shared by every learner with the same settings key (band, widths, popularity floor, share, opted-out openings), cached least-recently-used, 16 entries.
- **The default settings key (1500+, default settings) is warmed at startup.** Any other band graph, repertoire or ledger is **built in a worker thread**, so it never stalls other learners' moves.
- **A learner session** (records, per-learner steering state, faced counts, notices; about 1 MB once the caches are shared) loads when the learner first connects or requests a page and is dropped after **30 minutes** with no socket open and no request. The progress view's "this session" success rate counts from its start.
- A settings change regenerates only that learner's repertoire and restarts only that learner's tabs.
- **The single round-end lock stays**, with the commit on the event loop. No per-learner locks, no worker thread for commits.

### 5. Sign-in, sessions and the account page

- **An account is exactly one identity**: a Lichess id or an email address. No linking, no joining by email. Signing in with the other method reaches a different account.
- **Lichess**: OAuth2 with PKCE, `client_id` derived from the base URL (`chessop.fr`), no scope. After the callback the server calls the Lichess account endpoint once for the `id` (the key) and username (display), then revokes the token. No token and no email are stored.
- **Email**: one message carrying a **link and a 6-digit code**, both single-use, valid 15 minutes, the token at least 128 bits, both stored hashed. The link opens a page with a confirm button; only that button's POST signs in. The code is typed into the requesting tab and is bound to that browser's pending sign-in; 5 tries, and a resend does not reset the count. An unknown address creates the account at first sign-in. The landing page sends `Referrer-Policy: no-referrer`.
- **Sending**: Scaleway Transactional Email's HTTP API (Paris), in the background; the response is always "check your inbox". Limits: 3 emails per address per 15 minutes, 10 per IP per hour, 250 per day site-wide.
- **Session**: the same single cookie as the anonymous one, holding a server-side session token, **rotated at sign-in and at sign-out**. Signed-in sessions last one year, sliding. No limit on concurrent sign-ins.
- **Adopting** (at sign-in, no prompt): if the browser holds an anonymous learner, it joins the account.
  - Account with no history: it takes everything.
  - Otherwise merge. A position on one side only carries over; on both, the record with the later last pass wins whole. Both round logs are kept. Daily score: a shared day keeps the account's Score and adds the anonymous rounds and successes; a day on one side only carries over. The account's settings win if it has any.
  - The anonymous learner is then deleted.
- **Sign-out** clears the cookie; the browser has no learner until the next round creates a fresh anonymous one.
- **Account page**: sign out; change email (email accounts only: a confirm link to the new address with the same mechanics, refused if another account holds it); delete my account (confirm dialog, immediate deletion of learner, history, identity and every session).
- **UI**: header "Sign in" leads to `/signin` (Lichess first, the email field below, a link to the privacy notice) and returns to the page the learner came from. Signed in, the header shows the username or email, linking to the account page.
- **Local mode**: no sign-in routes, link, notice or cookie.

### 6. Limits (hosted only)

One limits module of in-memory counters, lost on restart. The client is its IPv4 address or IPv6 /64 prefix, from the forwarded header. Counters are dropped once their window passes. IPs are never logged.

| Limit | Value | Past it |
| --- | --- | --- |
| Live learner sessions, server-wide | 300 | new session refused: "chessop is full right now, try again in a few minutes"; running sessions unaffected |
| New anonymous learners per IP | 30 per hour | a **throwaway learner** |
| WebSocket messages per connection | 5/s, burst 20, 1 KB max | close with code 1008 |
| Open sockets | 10 per learner, 40 per IP | the new socket is refused |
| HTTP requests per IP, non-static routes | 120/min | 429 |
| Settings saves per learner | 10/min | 429 |
| Data downloads per learner | 5/hour | 429 |
| Sign-in emails | §5 | "check your inbox" regardless |

- A 429 carries `Retry-After` and a plain page "Slow down: try again in N seconds." `/healthz` and static files are exempt.
- **Throwaway learner**: in memory, default settings, never written to SQLite, no cookie, gone when its socket closes, counted in the 300. Play works. A notice says "Too many new visitors from your network: this round won't be saved. Try again later or sign in." Settings and progress show the notice instead of saving. Sign-in still works.

### 7. Latency and the socket

- **Budget**: server handling of a learner move under 10 ms at p95 over all moves, round-ending ones included, on an on-disk store; in hosted mode with 30 learners playing at once. End to end, drop to reply under 250 ms at p95 from a French 4G phone. Past 30 the site may degrade up to the session ceiling.
- **A closed socket abandons the round**: nothing written, no miss charged, no resume.
- **The play page reconnects by itself**: backoff 1 s, 2 s, 5 s, then every 10 s; at once when the tab becomes visible or the browser reports it is online. The new socket gets a fresh round. No retry after a close with code 1008 or a "full" refusal: those keep a manual "connection lost, reload" state.
- **While disconnected** the board locks and a "Reconnecting…" banner sits over the verdict area. After reconnecting, one line: "Connection was lost; that round wasn't counted".
- **Slow socket**: after 1 s with no reply to a move, a "waiting for the server…" hint; after about 10 s of silence the page closes the socket and reconnects. No application heartbeat.
- **Pre-launch gate**: a kept load-test script (N scripted WebSocket learners playing rounds, reporting p50, p95 and resident memory), run by hand against the VPS: the budget at 30 learners, and resident memory under 1 GB at 300 sessions. Re-run after any change to the round-end path. Not in CI.

### 8. Phone layout and installable app

Reference: branch `prototype/mobile` (variant Stacked for play, Condensed table for progress). The desktop layout is unchanged.

- **Play, below about 40em wide (Stacked)**:
  - one compact header row: side badge, Score and its change, then three 44 px icon buttons (sound on/off showing 🔊/🔇, progress, settings) replacing the corner text links;
  - the opening name, and the "not X this time" line, on its own line under the header;
  - the board as wide as the screen, capped at 72vh, `touch-action: none`; drag and tap-to-move both work;
  - the verdict strip under the board, wrapping to two lines; the "space next round" hint hidden on touch;
  - a full-width green **Next round** button, at least 52 px tall, shown only once the round is over; tapping the verdict still starts the next round;
  - the Explanation below, scrolling with the page.
- **Landscape on a narrow screen**: the board on the left at full height; header, verdict, Next and Explanation in a column on its right.
- **Progress, narrow**: columns cut to opening name, Score, White, Black; ECO, positions and the known/learning bar hidden; in/out and reset buttons only when the row is opened; move chips gain about 6 px of tap padding. Settings needs no change.
- **Manifest**: name "chessop — drill your openings", short name "chessop", `start_url` `/`, `display: standalone`, any orientation, background and theme `#161512`, icons 192 and 512 px PNG plus a maskable 512; Apple touch icon and the iOS web-app meta tag.
- **Service worker** at `/sw.js`, root scope: caches **only the static shell** (chessground's JS and CSS, pieces, the five sounds, page CSS and JS, the icon) under a cache name that changes with each release; old caches deleted on activate. Page loads always go to the network. When a page load fails it shows the offline page: "chessop needs a connection: every move is checked by the server", with a Try again button. **No offline play.**

### 9. Help page

Reference: branch `prototype/help` (variant B); its help-copy template is the starting draft of the wording.

- `/help`, titled "How chessop works", both modes. A list of sections at the top, then one anchored section each: How a round works; The verdict under the board (`#verdict`); "Not X this time" (forced exploration); Score (`#score`); Change since your last day; As White and as Black; Known, learning, never passed; This session; The line (sparkline); Openings (the table, out and reset); Move colours; Rating band.
- The Known section quotes the running sure threshold; the session section quotes the running target range (80–90 % by default).
- **Progress**: each figure's label is a dotted-underline link to its section (Score, change since, as White/as Black, known/learning/never passed, this session, the sparkline's "daily", the Opening column header, the colour legend).
- **Play**: the corner links gain **help**; after a round a small line under the verdict reads "what does this mean? · what is the Score?".
- A closing line: "Questions or a bug? Write to contact@chessop.fr, or open an issue on GitHub" (hosted; local mode links the repository only).
- No popovers, no first-visit walkthrough.

### 10. Legal pages and data rights (hosted only)

- **`/legal`**: anonymous under LCEN art. 1-1 II. Shows only the host (OVH SAS, 2 rue Kellermann, 59100 Roubaix, and its phone number), states that the publisher's identity has been given to the host, gives `contact@chessop.fr`, and three lines of terms: free and provided as is with no warranty; may change or end; no misuse (bots, scraping). English with a short French version on the same page.
- **`/privacy`**: English, plain enough for a 13-year-old. Names the owner (first and last name) as controller with `contact@chessop.fr`. One entry per processing with purpose, basis, data, recipients, retention:
  - email accounts, Lichess accounts, signed-in history, anonymous history and its cookie: contract;
  - memory-model refitting and usage counting from the round log: legitimate interest, only data already held, deleted with the learner, objecting means deleting your data;
  - error logs: legitimate interest;
  - audience statistics: legitimate interest under the CNIL exemption, with the **opt-out toggle on this page**;
  - Ko-fi: its own controller; no donor data reaches chessop.

  Also: recipients (OVH as host, Scaleway for sign-in emails and encrypted backups, Lichess only when the learner chooses it; all in France, no transfer outside the EU; GoatCounter self-hosted; UptimeRobot sees no personal data); the cookie list (one cookie); the rights (access, export, correction, erasure, restriction, objection); complaint to the CNIL; post-mortem directives; a reply within one month; deleted data leaves backups within 30 days; the retention periods below, including that Lichess accounts get no warning.
- **`/data`** ("Your data"), linked from the footer, the privacy notice and the account page:
  - **Download my data**: one JSON file named `chessop-data-YYYY-MM-DD.json`, generated on request, streamed, never stored. Contents: format version, export time, snapshot version; the account (kind, email or Lichess username, created date) or `null`; the learner's creation and last-seen times; settings; every position record (FEN, passes, misses, last pass, relearning owed); the full round log; the daily scores. No session tokens or hashes, no computed estimates.
  - **Delete**: for an anonymous learner, "Forget this browser's history" (confirm, hard delete, cookie cleared); for a signed-in learner, the account deletion of §5.
  - With no learner yet, the page says nothing is stored.
- **Retention**:
  - anonymous learner: deleted after 12 months with no request, no warning; and after **30 days** with no request if they have fewer than 5 rounds;
  - account: deleted after 24 months with no request. Email accounts are warned at 23 months (`warned_at` set) and deleted only when the warning is at least 30 days old and the account still unseen; any request clears `warned_at`, so a mail outage delays deletion. Lichess accounts are deleted at 24 months with no warning;
  - logs: no access logs anywhere; the app logs errors only, never IPs or tokens; journald capped at 6 months and 500 MB;
  - GoatCounter: 760 days; the counts-only aggregate: forever;
  - backups: 14 days on the VPS, 30 days off-site, last 3 pre-deploy copies.
- **Footer on every hosted page**: "Legal notice · Privacy · Source · Ko-fi". The Ko-fi link also sits on the progress page, with the line that tips pay for the server and domain and are not tax-deductible. No payment code, no webhook.
- **Processing register**: a one-page GDPR art. 30 record in the repository's legal docs, noting the OVH and Scaleway processor agreements and the backup bucket (encrypted, Paris, 30 days).
- `contact@chessop.fr` appears as a mail link on `/legal`, `/privacy`, `/data` and `/help`. No contact form.

### 11. Discovery

- **The pitch**, one wording: title on `/` is `chessop: grind chess openings`; description (meta description, link preview, README lead) is "Grind chess openings against the moves people at your rating really play, drawn from Lichess games. Free, no sign-up." `/help` keeps its own title with the same description. "Grind" appears in the pitch only; everything else says "drill".
- **Indexing** (hosted): `/` and `/help` indexable with `rel=canonical` from the base URL; every other page carries `noindex`. `robots.txt` allows crawling; no sitemap. The statistics host serves a `robots.txt` disallowing everything.
- **Link previews** (hosted, through `site`): Open Graph title, description, URL, type `website`, image, plus `twitter:card` `summary_large_image`. One static 1200×630 PNG shipped with the static files: a board in an opening position, the name "chessop" and the pitch beside it; made once, not generated.
- **Language**: English only, `lang="en"`.
- **README**: the pitch, the site link, one real desktop screenshot of the play page; then "Run it yourself" (the existing local instructions); then a short "Hosting your own" pointing at `serve --hosted` and the deploy scripts, promising no support; licence last. No badges.
- **Local mode**: no Open Graph, no canonical, no `robots.txt`; its title unchanged.

### 12. Monitoring

- **`/healthz`** (both modes): 200 only when the database answers and the snapshot is loaded. Exempt from limits.
- **Visitor analytics**: the GoatCounter script, served in hosted mode only, page views only, no custom events, referrer reduced to its host, UTM parameters dropped, never the learner cookie or account id. The privacy page's toggle sets GoatCounter's `skipgc` local-storage flag. Do Not Track and Global Privacy Control suppress the count.
- **Errors**: logged to journald by the app; nothing else in-app.
- **Daily usage aggregate**: one row per finished UTC day, counts only, never learner ids: active learners (anonymous and signed-in), new learners, rounds, successes, sign-ins, adoptions, deletions. Each finished day is written once and kept forever. Sign-ins, adoptions and deletions are counted when they happen (gap G4).
- **`chessop stats`**: reads the database and prints tables: active learners per day, week and month (anonymous and signed-in); new learners per day; rounds per day and per active learner; overall success rate; sign-ins and adoptions per day; retention (of a week's new learners, how many returned after 1, 7 and 30 days); band and opening choices of active learners; snapshot versions in use. Past days come from the aggregate; retention and the mixes are computed live over the learners that remain. No admin page.

### 13. Owner commands

All read the same environment as `serve --hosted`.

- **`chessop maintain`**, in order: write yesterday's aggregate row; send account warnings; run the three purges (anonymous at 12 months idle, anonymous under 5 rounds at 30 days idle, accounts at 24 months idle per §10); take the SQLite backup into the data directory's backups folder (14 kept), encrypt it with `age` to the configured recipient and upload it. Each step is idempotent and logs its counts. A failed step does not stop the later ones but makes the run exit non-zero.
- **`chessop notify-owner --subject …`**: reads the body on stdin and sends it to the owner's address through the same mailer.
- **`chessop stats`**: §12.

### 14. Deployment and operations artefacts

A `deploy/` directory in the repository holds everything below; none of it runs in CI.

- **Host**: OVH VPS-1, Gravelines, Debian 13. Domain `chessop.fr` at OVH. No Docker, no staging.
- **`provision.sh`**, idempotent: system user `chessop` (no login shell); uv pinned to a version; uv-managed CPython 3.12 under `/opt/chessop/python`; Caddy from Debian; firewall open on 22, 80, 443; unattended upgrades; SSH password login off; the `/opt/chessop` and `/etc/chessop` layout; the journald drop-in; GoatCounter from a pinned release binary with its SHA-256 checked, own user and unit, data in `/var/lib/goatcounter`, retention 760 days; every unit and timer below.
- **Layout**: code in `/opt/chessop/releases/vX.Y.Z` behind a `current` symlink, root-owned; data in `/var/lib/chessop` (0700); `/etc/chessop/chessop.env` root:chessop 0640.
- **`chessop.service`**: runs `chessop serve --hosted` from the current release as `chessop`, with the environment file, a state directory, restart on failure after 2 s, `OnFailure=` the notify template, and hardening (`NoNewPrivileges`, `ProtectSystem=strict`, `ProtectHome`, `PrivateTmp`, `PrivateDevices`, address families limited to IPv4, IPv6 and Unix).
- **Timers**: `chessop-maintain` daily at 03:30 UTC, persistent; a daily disk check piping `df` into `notify-owner` above 80 %; a daily error digest piping the last 24 hours' error-priority journal into `notify-owner` only when non-empty.
- **`chessop-notify@.service`**: pipes the failed unit's status and last 50 journal lines into `notify-owner`. `OnFailure=` points at it from the chessop, maintain, disk, digest and GoatCounter units.
- **`Caddyfile`**: automatic HTTPS for `chessop.fr`; `www` and plain http redirect to the apex over https; HSTS; WebSockets passed to `127.0.0.1`; access logging off; a static "back in a moment" page on 502; `stats.chessop.fr` proxied to GoatCounter with its disallow-all `robots.txt`.
- **`publish.sh vX.Y.Z`** (private repo to public): refuses a dirty `main`; runs ruff and pytest; tags the private commit; copies its tree onto the local `public` branch minus the paths in a `public-exclude` list; scans for secret patterns (Lichess tokens, TEM keys) and refuses on a hit; commits `Release vX.Y.Z`, tags, pushes. Excluded: the third-party PDF and HTML copies under `refs/` (its README becomes a bibliography of links; the Lichess analysis scripts are published), the loop script, the first wayfinder prompt, the token file. Published: source, tests, docs, `.scratch`, prototypes, licences.
- **CI** (GitHub Actions on the public repo, every push and tag): `uv sync --frozen`, ruff, pytest, on the pinned Python version. Never deploys.
- **`deploy.sh vX.Y.Z`**, run by hand with the owner's SSH key: requires a public tag whose CI run is green; on the VPS checks the tag out into its release directory; `uv sync --frozen --no-dev`; SQLite backup to the pre-deploy folder (last 3 kept); switches the symlink; restarts; polls `/healthz` for 30 s; on failure switches the symlink back and restarts. The database is never restored automatically. Last 3 releases kept.
- **Restart** is plain: rounds in flight, sessions and limit counters are lost; the worst case is one unscored round per open tab.
- **An environment-file example** listing every variable of §1.
- **Runbook** in the operating docs (`docs/operating.md`). First-time setup in dependency order: order the VPS; DNS at OVH (apex, `www`, `stats`, the TEM SPF/DKIM/DMARC records, the `contact@` redirect); SSH key and admin user; `provision.sh`; Scaleway TEM key, backup bucket with its 30-day lifecycle rule and write-only key; generate the `age` key and store it in two places off the VPS; fill in the environment file; create the public GitHub repo (topics `chess`, `openings`, `spaced-repetition`, description = the pitch); first deploy; create the GoatCounter site and login; UptimeRobot on `/healthz` every 5 minutes with certificate-expiry warning; restore rehearsal; load-test gate. Routine sections: deploy; restore from backup (deleted learners come back, purges re-run, emailed deletion requests re-applied by hand); rotate the TEM key; answer a data request by email; a data breach (CNIL within 72 hours).

### 15. Glossary and ADRs

Already updated by the tickets: **Learner**, **Account**, **Adopt**, **Rating band**, **Drill**, **Round log** in the glossary; ADR 0002, 0003, 0004 amended; ADR 0007 and 0008 added. Code, UI text, emails and docs use the glossary's terms and avoid its *Avoid* words (in particular: never "user" for a learner, never "login" or "profile" for an account, never "sync" or "import" for adopt, "grind" only in the pitch).

## Testing Decisions

A good test here drives chessop from outside, the way a browser or the owner's shell does, and asserts on what comes back: pages, redirects, cookies, socket messages, the exported JSON, the emails handed to the mailer, a command's output and exit code. It does not reach into sessions, caches, counters or table layouts. No browser automation (ADR 0004 stands); the phone layout, reconnect behaviour and the service worker are verified by hand against the prototypes' behaviour.

**One primary seam: the app factory driven through FastAPI's test client**, over the fixture graph, exactly as the existing wire, settings and progress tests do. Hosted mode is the same seam with a hosted-settings object passed in. Three things are injected there because they are the process's edges: a **mailer** (a recording fake; the console mailer is the real dev implementation), a **Lichess client** (a fake returning an id and username), and a **clock** (so 15 minutes, 30 days and 24 months can pass). The limits take the same clock. Through this seam:

- local mode is unchanged: no cookie set, no sign-in routes, no footer, hosted-only routes answer 404;
- an anonymous learner appears at the first round, not the first page view; two cookies give two isolated histories and settings;
- email sign-in end to end (link then confirm POST; code in the requesting client; wrong code five times; expiry; single use; unknown address creates the account; always "check your inbox"); Lichess sign-in with the fake;
- adopt: empty account takes everything; merge keeps the later last pass per position, both round logs, the daily-score rule; the anonymous learner is gone; the cookie token rotates;
- sign-out leaves no learner; account deletion signs out a second client; email change, including refusal on a held address;
- `/data` export contents and the two deletions; `/legal`, `/privacy`, footer, `noindex`, canonical and Open Graph from the configured base URL even with a forged `Host`;
- limits: 429 with `Retry-After`, the throwaway learner past 30 new learners (plays, nothing saved, no cookie), socket message rate closing with 1008, the socket caps, the "full" refusal;
- `/help` sections and anchors, the links to them from progress and play, the quoted running threshold; `/healthz` green and red; manifest and service worker served in both modes;
- band choice from the eight, the default, the fallback for a missing band, the per-learner snapshot notice shown once;
- the `hello {tz}` message setting the timezone once and moving the daily score's day.

**Secondary seams, all existing:**

- **The store on disk** (prior art: the store tests): the v1-to-multi-learner migration on a real v1 file, including the declared-rating-to-band mapping; WAL and `synchronous=NORMAL` in effect; learner deletion cascading to every table.
- **The CLI entry point** (prior art: the CLI tests): `--hosted` refusing to start with every missing variable named; `maintain` (aggregate row written once, warning sent then deletion only 30 days later, each purge boundary, a failing step giving a non-zero exit while later steps run, upload skipped when the backup variables are unset) with the fake mailer and clock; `stats` output over a seeded database; `notify-owner` sending stdin.
- **The snapshot build** (prior art: the build tests): a game feeding every band both players fall in; open-band membership needing both players at or above the bound.
- **Latency** (prior art: the latency test): moved to an on-disk store so it measures the real commit; still marked slow. The load-test script is run by hand, not asserted in CI.

**Not unit-tested**: the shell scripts, Caddyfile and systemd units. They are exercised by the runbook's first deploy, the restore rehearsal and the load-test gate.

## Out of Scope

- Native App Store or Play Store apps; offline play.
- Ads, paid tiers, payment code, a Ko-fi webhook.
- Announcements and listings (Lichess forum or blog, Reddit, itch.io).
- A French version of the site (beyond the short French legal notice).
- Linking a Lichess identity and an email on one account; passwords; importing local history into the hosted site; seeding from the learner's own Lichess games.
- An admin page, Sentry-like error reporting, a public status page, per-band success rates.
- A staging instance, Docker, push-triggered deploys, scheduled snapshot rebuilds, building the snapshot on the VPS.
- Per-learner locks or a worker thread for the round-end commit; resuming a round after a dropped socket.
- Anti-bot or anti-scraping work beyond the limits that protect the box.
- Changes to the repertoire rule, memory model, sampling rule or Score.
- A contact form; a cookie banner; an age gate; a sitemap.

## Further Notes

**Gaps the tickets left, decided here with the smallest reading. Each is easy to reverse.**

- **G1. Settings before the first round.** The tickets create an anonymous learner at the first round, but a visitor may save settings first. Saving settings (or toggling an opening from progress) also creates the anonymous learner, under the same 30-per-IP-per-hour cap. Viewing any page never does.
- **G2. When the TEM key is required.** Ticket 11 lists it as required yet optional for development. Here: required when the base URL is `https`, optional on `http` (console mailer). This keeps a production server from silently printing magic links.
- **G3. GoatCounter URL optional.** Unset means no analytics snippet and a privacy page without the toggle's effect; set on the VPS.
- **G4. Event counts in the aggregate.** An adopted or deleted learner leaves no row to count the next night, so sign-ins, adoptions and deletions are incremented in the day's counts-only row as they happen; `maintain` fills in the derived counts (active, new, rounds, successes) for the finished day. "Active" means at least one round logged that UTC day. The tickets' "pass rate" is read as the **success** rate of rounds, net of forced exploration, to match the glossary.
- **G5. "Full" on the wire.** A socket refused at the 300-session ceiling is closed with code 1013 and a page request gets 503 with the same sentence; the play page treats 1013 like 1008 (no auto-retry).
- **G6. The timezone message is named `hello`.** ADR 0002 says the browser reports its timezone "on its first socket message"; this is a sixth message type, client to server, with no reply.

**Steps only the owner can do** (all in the runbook): ordering the VPS and domain, DNS, the Scaleway and UptimeRobot accounts, the `age` key, the GitHub repository, the OVH `contact@` redirect, filling in the environment file, the privacy notice's controller name, the hand-made preview image and README screenshot, the restore rehearsal, the load-test gate against the VPS. Two more precede the first publish:

- **Rebuilding the packaged snapshot with eight bands** needs the Lichess dump month and about 11 GB of memory on the owner's machine (about 14 minutes). The build-tool change is agent work; running it is not.
- **Removing the committed Lichess token from the private history** (`git filter-repo`) and revoking it on Lichess. It rewrites history, so the owner runs it.

**Material on branches, not yet on `main`**: the research the ADRs cite (`research/hosting-options`, `research/french-legal`, `research/open-bands`, `research/sign-in`) and the two prototypes (`prototype/mobile`, `prototype/help`). The research files should be brought onto `main` so the published docs' links resolve; the prototypes are references to port from, not code to merge.

**Suggested build order** (each slice testable through the primary seam): open bands and band choice → multi-learner schema, migration and WAL → hosted switch, current-learner seam and base template → sign-in, adopt and account page → data rights and legal pages → limits → shared caches, builds off the loop, reconnect → phone layout and PWA → help page → discovery tags and README → `maintain`, `stats`, `notify-owner` → deploy artefacts and runbook.

**Cost**: about €5.40 a month with VAT plus about €9 a year for the domain; email and the backup bucket are about €0 at hobby scale.

Research is not legal advice: the legal reading comes from `docs/research/french-legal.md` (branch `research/french-legal`), including two points marked there as the researcher's own reading (the privacy notice may give a name and email only; Ko-fi tips are taxable income).
