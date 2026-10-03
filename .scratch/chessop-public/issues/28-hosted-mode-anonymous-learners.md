# 28: Hosted mode with anonymous learners

**What to build:** `chessop serve --hosted` turns the server into a site many learners can use at once, while `chessop` and `serve` without the flag stay local mode. The CLI builds one hosted-settings object from the `CHESSOP_*` environment and hands it to the app factory; a missing required variable stops startup listing every missing name; `CHESSOP_BASE_URL` alone never turns hosted mode on. Hosted binds `127.0.0.1` on a fixed port (default 8000), opens no browser, writes no access log, and trusts forwarded headers from `127.0.0.1` only. The mode is tested at three seams only: the current-learner dependency, a hosted-only router, and the base template's `site`.

A visitor plays at once as an anonymous learner: a server-side learner is created at their first round, or when they first save settings or toggle an opening, never on a page view. It is keyed by a random token, stored hashed, in one cookie (`HttpOnly`, `Secure` unless the base URL is `http`, `SameSite=Lax`, 12 months, sliding). Each learner has their own history and settings; a settings change regenerates only that learner's repertoire and restarts only their tabs; several tabs and devices work at once. A learner session loads on first connect or page request and is dropped after 30 minutes with no socket and no request. After their first round the anonymous learner is told once that progress lives in this browser. Model parameters are server-wide and not shown in hosted settings. Every hosted page gets the footer "Legal notice · Privacy · Source · Ko-fi" through `site` (targets arrive in ticket 34). The clock is injected. (Spec §1, §3, §4, G1, ADR 0002, 0004.)

**Blocked by:** 19, 22

**Status:** done

- [x] `serve --hosted` with variables missing exits non-zero and names every missing one; with them set it starts on the fixed port without opening a browser
- [x] Viewing pages sets no cookie and creates no learner; the first round, a settings save or an opening toggle does
- [x] Two clients with two cookies have isolated histories and settings; one learner's settings change does not restart the other's tabs
- [x] The cookie has the stated attributes and drops `Secure` on an `http` base URL
- [x] The "progress lives in this browser" notice shows once, after the first round
- [x] A learner session is dropped after 30 idle minutes (injected clock) and reloads from the store on return; "this session" counts from its start
- [x] Model parameters are absent from hosted settings
- [x] Hosted pages carry the footer; local pages do not
- [x] Local mode is unchanged: no cookie, and hosted-only routes answer 404
- [x] The mode is branched on only at the three seams
