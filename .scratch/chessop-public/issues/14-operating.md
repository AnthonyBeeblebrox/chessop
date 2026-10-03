# Operating the hosted site

Type: grilling
Status: resolved
Blocked by: 13
Map: [chessop in public](../map.md)

## Question

Once deploying is set (Deploying chessop to the VPS): the standing jobs and one-off setup that keep the site legal and alive. Decide backups of the SQLite file beyond OVH's daily VPS backup (where, how often, and how deleted data leaves them within 30 days, per Legal pages and data rights); installing GoatCounter at `stats.chessop.fr`; the daily jobs and their timers (12-month anonymous purge, 30-day quick purge of learners with under 5 rounds, 24-month account purge with its warning email, daily usage aggregate) and the disk and error-digest timers piping into `chessop notify-owner`; journald's `MaxRetentionSec=6month`; the UptimeRobot account; the `contact@chessop.fr` redirect; and noting the OVH and Scaleway processor agreements in the register. Output may be a runbook the spec links, or a `wizard` for the human-only steps. Also from Deploying chessop to the VPS: the human-only setup steps (ordering the VPS, DNS at OVH, the SSH key, filling in `/etc/chessop/chessop.env`, creating the public GitHub repo) and the notify-owner unit that `chessop.service`'s `OnFailure=` points at.

## Answer

Grilled 2026-10-02. No ADR (every choice here is easy to reverse); no glossary change. Amends Switching chessop serve into hosted mode on one point: the TEM key is no longer the only secret, the backup bucket's write-only key joins it in the env file.

- **Backups**: nightly `sqlite3 .backup` to `/var/lib/chessop/backups`, 14 days kept on the VPS. The same file, encrypted with `age` (public key on the VPS), is uploaded to a Scaleway Object Storage bucket in Paris whose lifecycle rule expires objects after 30 days; that rule is what keeps the "leaves backups within 30 days" promise. OVH's daily image and the pre-deploy copies stay as they are.
- **Bucket key**: a separate Scaleway IAM application allowed only to write objects to that one bucket (no read, delete or list), in `/etc/chessop/chessop.env` as `CHESSOP_BACKUP_*`. With the variables unset, the upload is skipped and logged, so localhost development works.
- **`age` private key**: on the owner's machine and in the owner's password manager; never on the VPS, never in either repo.
- **Restore brings deleted learners back**: accepted. After a restore the nightly purges re-run on their own, and the owner re-applies by hand the deletion requests received at `contact@chessop.fr`. Self-service deletions made in the lost window are not replayed. No tombstone list outside the database.
- **Restore rehearsal**: once before launch (decrypt last night's off-site copy on the owner's machine, start hosted mode on localhost against it), then only when the backup script changes. No scheduled drill.
- **Daily jobs**: one `chessop maintain` command run by `chessop-maintain.timer` at 03:30 UTC (`Persistent=true`) as user `chessop`. In order: write yesterday's aggregate row; send account warnings; run the three purges (anonymous at 12 months idle, anonymous with under 5 rounds at 30 days idle, accounts at 24 months idle); take the backup and upload it. Each step is idempotent and logs its counts; a failed step does not stop the later ones but makes the run exit non-zero.
- **Account warning**: `warned_at` on the account. Email accounts are warned at 23 months idle and deleted only when `warned_at` is at least 30 days old and the account is still unseen; any request clears `warned_at`. A TEM outage therefore delays deletion. Lichess accounts are deleted at 24 months with no warning.
- **Disk and error digest**: two separate small timers (daily), shell only, piping `df` (over 80%) and `journalctl -p err --since -24h` (only when non-empty) into `chessop notify-owner`.
- **Notify-owner unit**: template `chessop-notify@.service`, which pipes `systemctl status %i` and the last 50 journal lines into `chessop notify-owner`. `OnFailure=chessop-notify@%n` on `chessop.service`, the maintain, disk and digest services, and GoatCounter. Alerts go to the owner's personal address (`CHESSOP_OWNER_EMAIL`), not through `contact@chessop.fr`. UptimeRobot is the channel that still works when TEM does not.
- **GoatCounter**: `provision.sh` downloads a pinned release binary and checks its SHA-256; own `goatcounter` user and unit, SQLite in `/var/lib/goatcounter`, behind Caddy at `stats.chessop.fr`, retention 760 days. Creating the site and the owner's login is a manual one-off in the runbook. Its database is not in the off-site backup.
- **Journald**: a drop-in with `MaxRetentionSec=6month` and `SystemMaxUse=500M`, installed by `provision.sh`.
- **No contact form**: `contact@chessop.fr` as a mail link on `/legal`, `/privacy`, `/data`, and now `/help` ("Questions or a bug? Write to contact@chessop.fr, or open an issue on GitHub").
- **Runbook, no wizard**: `docs/operating.md`, linked from the spec.
  - First-time setup, in dependency order: order the VPS; DNS at OVH (apex, `www`, `stats`, the TEM SPF/DKIM records, the `contact@` redirect to the owner's inbox); SSH key and admin user; run `provision.sh`; Scaleway TEM key, backup bucket with its 30-day lifecycle rule and write-only key; generate the `age` key and store it in two places; register the Lichess OAuth app; fill in `/etc/chessop/chessop.env`; create the public GitHub repo; first deploy; create the GoatCounter site and login; UptimeRobot account on `/healthz` alerting the owner's address; restore rehearsal.
  - Routine sections: deploy; restore from backup; rotate the TEM key; answer a data request by email; a data breach (CNIL notification within 72 hours).
- **Units and timers** live in `deploy/` and are installed by `provision.sh`.
- **Processing register** (`docs/legal/processing-register.md`): notes the OVH and Scaleway processor agreements, plus a line for the Scaleway bucket (encrypted backups, Paris, 30 days).
