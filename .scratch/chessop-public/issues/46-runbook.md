# 46: Runbook

**What to build:** The owner can operate the site months later without rediscovering it. The operating docs gain a runbook. First-time setup in dependency order: order the VPS; DNS at OVH (apex, `www`, `stats`, the mail SPF/DKIM/DMARC records, the `contact@` redirect); SSH key and admin user; `provision.sh`; the Scaleway mail key, the backup bucket with its 30-day lifecycle rule and write-only key; the `age` key stored in two places off the VPS; the environment file; the public GitHub repo with its topics and description; first deploy; the GoatCounter site and login; UptimeRobot on `/healthz` every 5 minutes with certificate-expiry warning; the restore rehearsal; the load-test gate. Routine sections: deploy; restore from backup (deleted learners come back, purges re-run, emailed deletion requests re-applied by hand); rotate the mail key; answer a data request by email; a data breach (CNIL within 72 hours). It also covers the two steps before first publish: rebuilding the snapshot and removing the committed token from history. Every command matches the real scripts and unit names. (Spec §14, Further Notes.)

**Blocked by:** 39, 44, 45

**Status:** done

- [x] The first-time checklist lists every step in the stated order, each with the exact command or console action
- [x] Each routine procedure is present and complete enough to follow cold
- [x] Every script, unit, variable and path named exists in the repository under that name
- [x] The docs use the glossary's terms
