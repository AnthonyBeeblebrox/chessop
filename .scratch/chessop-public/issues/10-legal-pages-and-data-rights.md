# Legal pages and data rights

Type: grilling
Status: resolved
Blocked by: 03, 04
Map: [chessop in public](../map.md)

## Question

With the legal research in hand (`docs/research/french-legal.md`): does the owner publish the legal notice under their own identity or anonymously via the host, and what name and contact the privacy notice gives; what the privacy notice says (written against the chosen host, analytics and learner model); the data-rights features and their surface (JSON export contents, account and anonymous-history deletion, email change (its flow is set in Sign-in with Lichess and email), analytics opt-out); retention periods (inactive accounts, unclaimed anonymous learners, logs, analytics); and how Ko-fi donations are framed given their likely tax treatment. Monitoring traffic, health and usage fixed the analytics: self-hosted GoatCounter, page views only, an opt-out toggle on the privacy page, DNT/GPC honoured, and a counts-only daily usage aggregate that is not personal data.

## Answer

Grilled 2026-09-29. No ADR (retention periods and page layout are easy to reverse); glossary: **Round log** now reads "never pruned while its learner exists", matching ADR 0002's amendment. Facts: `docs/research/french-legal.md` (branch `research/french-legal`).

- **Legal notice** (`/legal`): LCEN art. 1-1 II anonymity. It shows only the host, OVH SAS (2 rue Kellermann, 59100 Roubaix, and its phone number), and says the publisher's identity has been given to the host. It adds a contact address and three lines of terms: free and provided as is, with no warranty; may change or end; no misuse (bots, scraping). No separate terms page. Written in English with a short French version on the same page.
- **Privacy notice** (`/privacy`): English only, plain enough for a 13-year-old. It names the owner as controller (first and last name) with `contact@chessop.fr`. It has one entry per processing (purpose, basis, data, recipients, retention):
  - email accounts, Lichess accounts, signed-in history, and anonymous history with its cookie: contract;
  - memory-model refitting and usage counting from the round log: legitimate interest, only data already held, deleted with the learner, and objecting means deleting your data;
  - error logs: legitimate interest;
  - audience statistics: legitimate interest, CNIL exemption, with the opt-out toggle on this page;
  - Ko-fi: Ko-fi is its own controller, and no donor data reaches chessop.

  Recipients: OVH (host), Scaleway (sign-in emails), and Lichess only when the learner chooses it; all in France, no transfers outside the EU. GoatCounter is self-hosted; UptimeRobot sees no personal data. There is no consent-based processing, so no banner and no age gate. The notice also lists the cookies, the rights (access, export, correction, erasure, restriction, objection), complaints to the CNIL, post-mortem directives, a reply within one month, and that deleted data leaves backups within 30 days.
- **Contact**: `contact@chessop.fr`, via OVH's free email redirect to the owner's inbox. Replies come from the owner's own mailbox, not TEM.
- **Footer on every hosted page**: "Legal notice · Privacy · Source · Ko-fi". `/signin` links to the privacy notice. Local mode has no `/legal`, `/privacy` or `/data`.
- **Your data** (`/data`), linked from the footer, the privacy notice and the account page:
  - **Download my data**: one JSON file, `chessop-data-YYYY-MM-DD.json`, generated on request and streamed, never stored. It holds the format version, export time and snapshot version; the account (kind, email or Lichess username, created date) or `null`; the learner's creation and last-seen times; settings; every position record (FEN, passes, misses, last pass, relearning owed); the full round log; and the daily scores. No session tokens or hashes, no computed estimates, no CSV.
  - **Delete**: for an anonymous learner, "Forget this browser's history" (confirm, hard delete, cookie cleared); for a signed-in learner, the existing account deletion.
  - With no learner yet, the page says nothing is stored.
- **Retention**:
  - Anonymous cookie: 12 months, sliding. An anonymous learner is deleted after 12 months with no request, without warning.
  - Accounts: deleted after 24 months with no request. Email accounts get one TEM warning 30 days before; Lichess accounts get no warning, and the notice says so. Last-seen is updated at most once a day.
  - Logs: no access logs (Caddy access logging off, uvicorn `--no-access-log`). The app logs errors only, never IPs or tokens. Journald `MaxRetentionSec=6month`. Rate-limit counters stay in memory.
  - Analytics: GoatCounter retention 25 months (760 days). The counts-only daily aggregate is kept forever.
  - Backups: deleted data rolls off within 30 days. This constrains any off-site backup.
- **Paperwork**: a one-page record of processing (GDPR art. 30) at `docs/legal/processing-register.md` in the public repo. OVH's and Scaleway's processor agreements (GDPR art. 28) are accepted through their standard terms and noted in the register.
- **Ko-fi**: "Support chessop on Ko-fi" in the footer and on the progress page, with a line saying tips pay for the server and domain and are not tax-deductible. No webhook. The owner declares tips as BNC income and keeps a yearly total, outside the product.
- **Handed on**:
  - the purge timers and warning emails, the journald cap, the email redirect and the processor agreements → Deploying and operating fog;
  - routing `/legal`, `/privacy`, `/data` and the footer as hosted-only → "Switching chessop serve into hosted mode";
  - a shorter purge for anonymous learners with only a round or two → the abuse fog.
