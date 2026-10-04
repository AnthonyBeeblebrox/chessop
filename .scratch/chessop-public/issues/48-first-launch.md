# 48: First launch

**What to build:** chessop goes live at `https://chessop.fr`. The owner removes the committed Lichess token from the private history (`git filter-repo`) and revokes it on Lichess; fills in the controller name in the privacy notice; makes the 1200×630 preview image and the README screenshot; then follows the runbook's first-time setup from ordering the VPS to the first deploy, and finishes with the restore rehearsal and the load-test gate against the VPS. Every build ticket (17 to 46) is done first.

**Blocked by:** 46, 47

**Status:** done

- [x] The token is gone from history and revoked
- [x] The privacy notice names the controller; the real preview image and screenshot replace the placeholders
- [x] `publish.sh` and `deploy.sh` have shipped a release and `/healthz` is green behind HTTPS
- [x] A sign-in email arrives from the real mailer, and an owner alert arrives from `notify-owner`
- [x] A backup has been restored in rehearsal
- [x] The load test meets the budget: under 10 ms p95 at 30 learners, under 1 GB at 300 sessions
- [x] UptimeRobot and GoatCounter are reporting

## Comments

- 2026-10-03/04, launch log. Token revoked, history already clean. Controller named; screenshot and preview card taken from the app in a headless browser. Branch `spec/chessop-public` fast-forwarded into `main`. VPS-1 at Gravelines (`57.131.199.69`, `2001:41d0:601:1100::3063`), Debian 13; DNS at OVH; admin user `anthony`, `debian` removed. `provision.sh` stopped once on a pipefail bug in its sshd check (fixed, bb9916c). Scaleway: domain verified (SPF host is `_spf.tem.scaleway.com`), mail sent nothing until the IAM policy existed (403 `insufficient permissions`), bucket with 30-day expiry, write-only key; `age` key in `~/.config/chessop/backup.key` and the password manager. Public repository is `AnthonyBeeblebrox/chessop` (renamed from `afillion0`, 31a1f90), one commit `Release v0.1.0`. CI ran for the branch push only, the tag was pushed again on its own; `deploy.sh` now accepts any green push run of the commit (77857bb). `v0.1.0` live 22:24 UTC, `/healthz` ok, pages about 150 ms. Alert mail, sign-in mail and the first encrypted upload (82,167 bytes) all arrived; restore rehearsal read it back and served it. GoatCounter site created; UptimeRobot monitor up (certificate reminder is paid, skipped). Load test left for the owner to run: an agent may not load a live server.
- Load test, run by the owner on the VPS against v0.1.0: 30 learners for 60 s, move handling p95 6.7 ms, end-to-end p95 7.8 ms, 104 MB; 300 learners for 120 s, 267 played and 33 refused (`LIVE_SESSIONS` with the earlier sessions still counted), move handling p95 7.1 ms, end-to-end p95 16.9 ms, 153 MB peak; 0 illegal, 0 dropped. Database wiped afterwards, `/healthz` ok. chessop.fr is live; the ticket is done.
