# Monitoring traffic, health and usage

Type: grilling
Status: resolved
Blocked by: 03, 06
Map: [chessop in public](../map.md)

## Question

Settled at charting: light monitoring on three fronts. Decide the tools and what is measured: a cookieless visitor-analytics tool that meets the CNIL exemption (GoatCounter, Plausible, Matomo, or server logs only; hosted or self-hosted); uptime checks and alerting; error reporting (logs only, or Sentry-like); and which learning-usage figures the owner wants from the round log (daily active learners, rounds per learner, retention) and where they are shown (an admin page, or a query run by hand).

## Answer

Grilled 2026-09-29. No ADR (easy to reverse, no surprising trade-off); no glossary change.

- **Visitor analytics**: GoatCounter, self-hosted on the VPS (one Go binary, SQLite) at `stats.chessop.fr` behind Caddy. Nothing leaves France and there's no processor. The dashboard sits behind GoatCounter's own login.
- **What is counted**: page views only, no custom events. The referrer is reduced to its host, UTM parameters are dropped, and the learner cookie and account id are never sent. The script is served in hosted mode only. Opt-out: a toggle on the privacy page sets GoatCounter's `skipgc` localStorage flag. Do Not Track and Global Privacy Control are honoured.
- **Uptime**: UptimeRobot free tier checks `https://chessop.fr/healthz` every 5 minutes and warns before the TLS certificate expires. Alerts go to the owner by email. `/healthz` returns 200 only when the database answers and the snapshot is loaded. A daily timer on the VPS emails the owner through Scaleway TEM when disk usage passes 80%. No public status page.
- **Errors**: logs in journald. A daily systemd timer emails a digest of the last 24 hours' ERROR lines and tracebacks through TEM, only when there are any. `OnFailure=` on the chessop unit emails the owner when the service fails. No Sentry, no GlitchTip.
- **Learning-usage figures**:
  - active learners per day, week and month (anonymous and signed-in);
  - new learners per day;
  - rounds per day, and per active learner;
  - overall pass rate;
  - sign-ins and adoptions per day;
  - retention (of a week's new learners, how many came back after 1, 7 and 30 days);
  - band and opening choices of active learners;
  - snapshot version in use.

  No per-band pass rate for now.
- **Where shown**: a `chessop stats` command run over SSH, which reads the SQLite file and prints tables. No admin page.
- **Stable history**: a daily aggregate table holds, per finished day (UTC): active learners (anonymous and signed-in), new learners, rounds, passes, sign-ins, adoptions and deletions. It stores counts only, never learner ids, so it isn't personal data and isn't an anonymised copy of the round log. Each finished day is written once. Retention and the band and opening mix are computed live over the learners that remain.
- **Handed on**: how long logs and statistics are kept (at most 25 months for statistics per the CNIL), and the privacy notice's analytics and opt-out wording go to "Legal pages and data rights". Serving the analytics script and `/healthz`, and the TEM and GoatCounter settings, go to "Switching chessop serve into hosted mode". Installing GoatCounter, the timers and the UptimeRobot account is in the Deploying and operating fog.
