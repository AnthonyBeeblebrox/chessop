# 48: First launch

**What to build:** chessop goes live at `https://chessop.fr`. The owner removes the committed Lichess token from the private history (`git filter-repo`) and revokes it on Lichess; fills in the controller name in the privacy notice; makes the 1200×630 preview image and the README screenshot; then follows the runbook's first-time setup from ordering the VPS to the first deploy, and finishes with the restore rehearsal and the load-test gate against the VPS. Every build ticket (17 to 46) is done first.

**Blocked by:** 46, 47

**Status:** ready-for-human

- [ ] The token is gone from history and revoked
- [ ] The privacy notice names the controller; the real preview image and screenshot replace the placeholders
- [ ] `publish.sh` and `deploy.sh` have shipped a release and `/healthz` is green behind HTTPS
- [ ] A sign-in email arrives from the real mailer, and an owner alert arrives from `notify-owner`
- [ ] A backup has been restored in rehearsal
- [ ] The load test meets the budget: under 10 ms p95 at 30 learners, under 1 GB at 300 sessions
- [ ] UptimeRobot and GoatCounter are reporting
