# Switching chessop serve into hosted mode

Type: grilling
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

With the learner model ("From one learner to many", ADR 0002/0004 amended) and sign-in (ADR 0008) settled: how `chessop serve` is switched into hosted mode (a flag, a config file, environment variables), what hosted mode needs configured (base URL `https://chessop.fr`, Scaleway TEM API key, sender address, secrets for session tokens, data directory, listen address behind Caddy, the owner's alert address for the TEM-sent disk and error emails) and where secrets live on the VPS; and where the code branches between local mode (one implicit learner, no cookie, no sign-in routes, no notices) and hosted mode (cookie learner, sign-in and account routes, legal pages (`/legal`, `/privacy`, `/data` and the footer, set in Legal pages and data rights), analytics snippet (GoatCounter at `stats.chessop.fr`, set in Monitoring traffic, health and usage)), so the branch sits in one place rather than scattered `if hosted` checks. Also whether local mode ever exposes hosted features (e.g. running hosted mode on localhost for development, where Lichess accepts plain http), and whether local mode also serves the web app manifest and service worker (set in Mobile layout and installable app).

## Answer

Grilled 2026-09-29. No ADR (easy to reverse, no surprising trade-off); no glossary change. Settles the "flags that switch `chessop serve` into hosted mode" that ADR 0007 left open.

- **Switch**: `chessop serve --hosted` only (not plain `chessop`). Settings come from environment variables, read only under `--hosted`: `CHESSOP_BASE_URL`, `CHESSOP_DATA_DIR`, `CHESSOP_TEM_SECRET_KEY`, `CHESSOP_TEM_PROJECT_ID`, `CHESSOP_MAIL_FROM` (`login@chessop.fr`), `CHESSOP_OWNER_EMAIL`, `CHESSOP_GOATCOUNTER_URL`. A missing required variable stops startup with every missing name listed. No TOML file, and `CHESSOP_BASE_URL` alone never turns hosted mode on.
- **On the VPS**: systemd's `EnvironmentFile=/etc/chessop/chessop.env`, owned by root, group `chessop`, mode 0640.
- **Secrets**: the TEM key is the only one. Session tokens, magic-link tokens and codes are 32 random bytes stored as SHA-256 hashes; no signing key, nothing to rotate. Lichess uses PKCE with no client secret.
- **One branch, three seams**: `cli.py` builds a `Hosted` settings object (or `None`) and passes it to `create_app`.
  1. A `current_learner` dependency: the implicit learner locally, the cookie learner hosted (created at the first round). Every page route and the WebSocket use it.
  2. A router in `chessop/hosted.py`, mounted only when hosted: Lichess and email sign-in, sign-out, account page, `/legal`, `/privacy`, `/data`.
  3. The base template's `site` value: footer (legal links, Ko-fi, source), GoatCounter snippet, sign-in link. No other template or route tests the mode.
- **Development**: hosted mode runs on `http://localhost` with `CHESSOP_BASE_URL=http://localhost:8000`. The cookie drops `Secure` on an http base URL, and Lichess accepts localhost redirects. With no TEM key, magic-link and owner emails are printed to the console, and the key isn't required.
- **Both modes**: `/help`, the web app manifest, `/sw.js`, the offline page and `/healthz`. Localhost counts as a secure context, so a local chessop is installable; over plain-http LAN it simply isn't.
- **Hosted only**: account routes, legal pages, the footer (legal, Ko-fi, source), analytics. **Local mode has no footer.**
- **Behind Caddy**: host defaults to `127.0.0.1`. The port is fixed (default 8000, no free-port fallback). No browser is opened. uvicorn trusts `X-Forwarded-For`/`-Proto` from `127.0.0.1` only, which the abuse limits will rely on.
- **Base URL**: magic links, the Lichess `redirect_uri` and `client_id`, and the manifest's absolute URLs take it from `CHESSOP_BASE_URL`, never from the request's `Host` (a forged header would otherwise put another domain in a magic-link email).
- **Owner alerts**: `chessop notify-owner --subject …` reads the body on stdin and sends it through the same TEM mailer and env file. The disk timer (`df`), the error digest (`journalctl -p err --since -24h`) and the `OnFailure=` unit pipe their text into it. There is no second copy of the TEM key.
- **Handed on**: writing the env file, the systemd units and the timer scripts goes to the Deploying and operating fog.
