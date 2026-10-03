# Record of processing activities (GDPR art. 30)

The register of the hosted site, `https://chessop.fr`. It mirrors the privacy notice (`/privacy`, `src/chessop/templates/privacy.html`); when one changes, change the other. Basis for each reading: `docs/research/french-legal.md` and the public spec §10.

- **Controller**: Anthony Fillion, a private person publishing on a non-professional basis; contact `contact@chessop.fr`. No representative, no data protection officer (art. 37 does not apply).
- **Data subjects**: visitors who play (anonymous learners) and learners signed in to an account. Visitors who only view pages leave nothing but the audience statistics.
- **Transfers outside the EU**: none. Every processor is in France.
- **Last reviewed**: 2026-10-02.

## Processing

| Processing | Purpose | Basis | Data | Recipients | Erased |
| --- | --- | --- | --- | --- | --- |
| Email accounts | sign in by a mailed link and code | contract (6(1)(b)) | email address, account created, last seen, hashed link and code (15 minutes) | OVH (host), Scaleway TEM (sending) | on deletion, or 24 months idle after one warning at 23 months and 30 days more |
| Lichess accounts | sign in with Lichess | contract | Lichess id and username; the token is revoked at once | OVH; Lichess, at the learner's request | on deletion, or 24 months idle, no warning |
| Signed-in history | the drill: steering and progress | contract | position records, round log, daily scores, settings (band, widths, openings, sound, animation, time zone) | OVH; Scaleway (encrypted backups) | with the account |
| Anonymous history and its cookie | the drill before or without signing in | contract | the same history; one cookie holding a random token, stored hashed | OVH; Scaleway (encrypted backups) | on "Forget this browser's history", 12 months idle, or 30 days idle with fewer than 5 rounds |
| Memory-model refitting and usage counting | improve the model; know whether the site is used | legitimate interest (6(1)(f)); only data already held | the round log; a daily counts-only aggregate holding no learner | none | with the learner; the aggregate is not personal data and is kept |
| Error logs | find and fix faults | legitimate interest | the app's error messages; no access logs, never IPs or tokens | OVH | journald, 6 months and 500 MB at most |
| Audience statistics | page views and referring sites | legitimate interest, CNIL audience-measurement exemption; opt-out on `/privacy`, DNT and GPC honoured | path without query, title, referrer cut to its host name; browser, system and country derived by GoatCounter, IP and User-Agent held only in memory for 8 hours | none: GoatCounter self-hosted on the VPS | 760 days |
| Ko-fi tips | voluntary support | not chessop's processing | Ko-fi is its own controller; no donor data reaches chessop (no webhook) | none | n/a |

## Processors (art. 28)

- **OVH SAS** (2 rue Kellermann, 59100 Roubaix): VPS hosting at Gravelines, France. Data processing agreement accepted through OVHcloud's standard terms (its DPA annex to the contract).
- **Scaleway SAS** (Paris): Transactional Email for sign-in and warning emails; Object Storage for the off-site backups. Data processing agreement accepted through Scaleway's standard terms.
- **The backup bucket**: Scaleway Object Storage, Paris region. A nightly copy of the database, encrypted with `age` before upload, sent with a key that can only write; a lifecycle rule deletes each copy after **30 days**. On the VPS: 14 daily copies and the last 3 pre-deploy copies. Deleted data leaves the off-site copies within 30 days.
- Not processors: Lichess (the learner's own request to it), UptimeRobot (checks `/healthz`, sees no personal data), Ko-fi (its own controller).

## Security measures

HTTPS only with HSTS; one `HttpOnly`, `Secure`, `SameSite=Lax` cookie; session, link and code tokens random and stored as SHA-256 hashes; no passwords; Lichess with PKCE, no token kept; data directory readable by the service user only; the environment file root-owned, readable by the service group; off-site backups encrypted, the decryption key kept off the VPS; SSH by key only, firewall open on 22, 80 and 443; unattended security upgrades. A breach is notified to the CNIL within 72 hours (runbook).
