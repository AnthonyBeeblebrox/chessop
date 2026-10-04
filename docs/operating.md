# Operating chessop.fr

The runbook of the hosted site (public spec §14, ADR 0007): how `https://chessop.fr` was set up and how it is kept running, written so that the owner can follow it cold, months later. Every command is meant to be typed as it stands; `<like this>` is a value to fill in, `vX.Y.Z` the release in hand.

Two machines take part. **Here** is the owner's machine, holding the private repository (development, `deploy/publish.sh`, `deploy/deploy.sh`, the `age` key). **The VPS** is `chessop.fr`, reached as the owner's admin user over SSH; everything there that changes the system goes through `sudo`.

## Where things are

| What | Where |
| --- | --- |
| The release running | `/opt/chessop/current`, a symlink to `/opt/chessop/releases/vX.Y.Z` (the last 3 kept), root-owned |
| Its command | `/opt/chessop/current/.venv/bin/chessop` |
| The database | `/var/lib/chessop/chessop.sqlite`, with its `-wal` and `-shm` files; the folder is the `chessop` system user's alone (0700) |
| Nightly backups | `/var/lib/chessop/backups/chessop-YYYY-MM-DD.sqlite`, 14 kept; each also `age`-encrypted in the Scaleway bucket as `chessop-YYYY-MM-DD.sqlite.age`, expired there after 30 days |
| Pre-deploy copies | `/var/lib/chessop/pre-deploy/chessop-vX.Y.Z-<UTC time>.sqlite`, the last 3 |
| The environment | `/etc/chessop/chessop.env`, root:chessop 0640, from `deploy/chessop.env.example` |
| Units and timers | `deploy/*.service`, `deploy/*.timer`, installed in `/etc/systemd/system` by `deploy/provision.sh` |
| The scripts the units run | `deploy/disk-check`, `deploy/error-digest`, `deploy/notify-failure`, `deploy/goatcounter-retention`, installed in `/usr/local/lib/chessop` |
| Caddy | `deploy/Caddyfile`, installed as `/etc/caddy/Caddyfile`; the 502 page `deploy/back-in-a-moment.html` in `/usr/share/chessop` |
| GoatCounter | `/usr/local/bin/goatcounter`, its database `/var/lib/goatcounter/goatcounter.sqlite3` (not backed up off-site) |
| Logs | the journal only, 6 months and 500 MB at most (`deploy/journald.conf`); no access log anywhere |

What runs by itself, all in UTC: `chessop-maintain.timer` at 03:30 runs `/opt/chessop/current/.venv/bin/chessop maintain` (yesterday's usage aggregate, account warnings, the three purges, the backup and its upload); `chessop-disk.timer` at 06:00 mails the owner when a disk is more than 80 % full; `chessop-digest.timer` at 06:15 mails the last 24 hours' errors when there are any. When `chessop.service`, a timer's service or `goatcounter.service` fails, `chessop-notify@.service` mails the owner its status and last 50 journal lines. UptimeRobot mails the owner when `/healthz` stops answering, which still works when the VPS cannot send mail.

To look at the site from the VPS:

```sh
sudo -u chessop /opt/chessop/current/.venv/bin/chessop stats --data-dir /var/lib/chessop
systemctl status chessop.service
sudo journalctl -u chessop.service --since today
systemctl list-timers 'chessop-*'
sudo journalctl -u chessop-maintain.service -n 20   # last night's counts
```

## Before the first publish

Two steps only the owner can do, both on the owner's machine, both before `deploy/publish.sh` runs for the first time.

**Rebuild the packaged snapshot with eight bands** (ticket 47). Done on 2026-10-02: the packaged snapshot holds all eight bands, so the default band, 1500+, loads without a fallback. To rebuild it for a later month, the build needs about 11 GB of memory and about 14 minutes, and streams the month's dump from `database.lichess.org`:

```sh
uv run --extra build chessop build-snapshot --month 2026-08 --out src/chessop/data/snapshot.graph.json.gz
```

It writes `src/chessop/data/snapshot.graph.json.gz` and `src/chessop/data/snapshot.explanations.json.gz`, with a new snapshot version (the month and the band list are in it). Then run `uv run pytest` and `uv run pytest -m slow tests/test_packaged_snapshot.py`, and commit.

**Remove the committed Lichess token from the private history** and revoke it. A personal token (`lip_…`) was once committed in `token.txt`; `publish.sh` never publishes history and leaves `token.txt` out, but the token is revoked regardless and the private history rewritten:

1. On Lichess: lichess.org → Preferences → API access tokens → delete the token.
2. Check the history. The rewrite has already been run once in this repository (`.git/filter-repo/already_ran` exists), so this should print nothing:

```sh
git log --all --oneline -- token.txt
```

3. Only if it prints a commit: move the untracked `token.txt` out of the checkout, then rewrite every branch and tag (it rewrites history, so do it before any release tag exists, with no work left uncommitted), and check again:

```sh
mv token.txt ~/chessop-token.revoked.txt
sudo apt install git-filter-repo
git filter-repo --path token.txt --invert-paths --force
git log --all --oneline -- token.txt     # prints nothing
```

Also before the first publish, the placeholders the site ships with: the controller's first and last name (`CONTROLLER` in `src/chessop/hosted.py` and the first line of `docs/legal/processing-register.md`); the 1200×630 link-preview image `src/chessop/static/preview.png`; the README screenshot `docs/screenshot.png`; the Ko-fi page at the address in `KOFI` (`src/chessop/hosted.py`), or the constant corrected.

## First-time setup

In dependency order: each step needs only the ones above it.

### 1. Order the VPS and the domain

In the OVHcloud control panel (two-factor authentication on for the account: it holds both the host and the domain):

- Bare Metal Cloud → Virtual Private Servers → Order → **VPS-1**, datacentre **Gravelines**, image **Debian 13**, billed monthly without commitment. Paste the owner's SSH public key into the order if it offers to (step 3 makes one otherwise). Note the VPS's IPv4 and IPv6 addresses from its page.
- Web Cloud → Domain names → Order → **`chessop.fr`**, auto-renew on.

### 2. DNS at OVH

In the OVHcloud control panel → Web Cloud → Domain names → `chessop.fr` → DNS zone, so that it holds:

| Name | Type | Value |
| --- | --- | --- |
| `chessop.fr.` (apex) | A / AAAA | the VPS's IPv4 / IPv6 |
| `www` | A / AAAA | the VPS's IPv4 / IPv6 |
| `stats` | A / AAAA | the VPS's IPv4 / IPv6 |
| apex | TXT | SPF: `v=spf1 include:_spf.tem.scaleway.com -all` as the Scaleway console shows it (it read `_spf.scw-tem.cloud` in older guides), the one SPF record (replace OVH's default) |
| `<selector>._domainkey` | TXT | DKIM: the key Scaleway gives |
| `_dmarc` | TXT | DMARC: `v=DMARC1; p=none; rua=mailto:contact@chessop.fr` (tightened to `p=quarantine` once mail has gone well for a while) |
| apex | MX | OVH's own (`mx1.mail.ovh.net` and the rest of the default zone): the `contact@` redirect needs them |

Delete the default zone's A records that point at OVH's parking page. The SPF value and the DKIM name and key come from Scaleway: Scaleway console → create the account and a project `chessop` → Transactional Email → Add a domain → `chessop.fr` (region Paris) → the console lists the SPF, DKIM and DMARC records to add; copy them exactly, they win over the table above.

Then the `contact@` redirect: OVHcloud control panel → Web Cloud → Emails → `chessop.fr` → Redirections → Add a redirection → from `contact@chessop.fr` to the owner's own address, no local copy kept. Data requests and breach reports arrive there.

Check, once the zone has spread (minutes to hours):

```sh
dig +short chessop.fr www.chessop.fr stats.chessop.fr
dig +short TXT chessop.fr
dig +short TXT _dmarc.chessop.fr
```

### 3. SSH key and admin user

Here, a key if the owner has none, then an SSH alias, since `deploy/deploy.sh` connects to `chessop.fr` (`CHESSOP_SSH`) and reads the admin user from it:

```sh
ssh-keygen -t ed25519
ssh-copy-id debian@chessop.fr   # the image's default user; skip if the key was given at the order
cat >> ~/.ssh/config <<'EOF'
Host chessop.fr
    User <admin>
EOF
```

On the VPS, as the image's default user (`debian` on OVH's Debian images), create the owner's admin user with a password (what `sudo` asks for; SSH itself takes the key only) and give it the key:

```sh
ssh debian@chessop.fr
sudo adduser <admin>
sudo usermod --append --groups sudo <admin>
sudo install --directory --mode=0700 --owner=<admin> --group=<admin> /home/<admin>/.ssh
sudo install --mode=0600 --owner=<admin> --group=<admin> ~/.ssh/authorized_keys /home/<admin>/.ssh/authorized_keys
exit
ssh -t chessop.fr sudo true               # as <admin> now: asks the password, then succeeds
ssh -t chessop.fr sudo deluser --remove-home debian
```

### 4. Run `provision.sh`

From the private checkout here, copy `deploy/` up and run it as root. It installs uv and CPython 3.12, Caddy, the firewall (22, 80, 443), unattended upgrades, SSH by key only, the `/opt/chessop`, `/var/lib/chessop` and `/etc/chessop` layout, the journald drop-in, GoatCounter and every unit and timer; it refuses to turn SSH passwords off while no `authorized_keys` exists.

```sh
scp -r deploy chessop.fr:
ssh -t chessop.fr sudo bash deploy/provision.sh
```

It ends with `provision: done`, after printing the GoatCounter command of step 10 and "no release yet". Caddy fetches the certificates now that the DNS points here: `curl -sI https://chessop.fr` answers 502 with the "back in a moment" page until the first deploy. The script is safe to re-run: after any change to `deploy/`, run the same two commands again.

### 5. Scaleway: the mail key, the backup bucket and its write-only key

In the Scaleway console, in the project `chessop`:

- **Mail key.** Transactional Email → `chessop.fr` → wait for the domain to show as verified (step 2's records). IAM → Applications → Create application `chessop-mail` → Policies → Create policy → scope: project `chessop` → permission set `TransactionalEmailEmailApiCreate` (sending only); without this policy Scaleway answers 403 `insufficient permissions` to every send, and the key alone grants nothing. Application `chessop-mail` → API keys → Generate an API key. Keep the **secret key** and the **project ID** (Project → Settings) for step 7.
- **Backup bucket.** Create a second project, `chessop-backup`, holding nothing else. In it: Object Storage → Create bucket → region **Paris** (`fr-par`), private, a name such as `chessop-backup-<random>`. Bucket → Lifecycle rules → Create rule → whole bucket → **Expiration** after **30 days**: this rule is what keeps the privacy notice's promise that deleted data leaves the backups within 30 days.
- **Write-only key.** IAM → Applications → Create application `chessop-backup` → Policies → Create policy → scope: project `chessop-backup` only → permission set `ObjectStorageObjectsWrite` (put objects; no read, list or delete). Application `chessop-backup` → API keys → Generate an API key, preferred Object Storage project `chessop-backup`. Keep the **access key** (`SCW…`) and the **secret key** for step 7.

### 6. The `age` key, in two places off the VPS

Here (Debian: `sudo apt install age`):

```sh
install --directory --mode=0700 ~/.config/chessop
age-keygen --output ~/.config/chessop/backup.key
```

It prints `Public key: age1…`: that goes on the VPS (step 7). The key file itself is the only way to read a backup: copy its whole content into the owner's password manager as well, so it lives in two places, never on the VPS and never in either repository.

### 7. The environment file

```sh
ssh -t chessop.fr sudoedit /etc/chessop/chessop.env
```

`provision.sh` put the example there. Fill in:

- `CHESSOP_OWNER_EMAIL`: the owner's own address, where alerts go (not `contact@chessop.fr`);
- `CHESSOP_TEM_SECRET_KEY` and `CHESSOP_TEM_PROJECT_ID`: step 5's mail key and the project `chessop`'s ID;
- `CHESSOP_BACKUP_BUCKET`, `CHESSOP_BACKUP_ACCESS_KEY`, `CHESSOP_BACKUP_SECRET_KEY`: step 5's bucket name and write-only key;
- `CHESSOP_BACKUP_RECIPIENT`: step 6's `age1…` public key.

`CHESSOP_BASE_URL`, `CHESSOP_DATA_DIR`, `CHESSOP_MAIL_FROM` and `CHESSOP_GOATCOUNTER_URL` already hold the site's values. Lichess sign-in needs nothing here: its client id is the base URL's host. A required variable left blank stops `chessop serve --hosted` at the start, naming it; so does one of the four `CHESSOP_BACKUP_*` left blank while the others are set. All four blank is not an error: `chessop maintain` then skips the upload and only logs it, so the site has no off-site backup. Step 9 checks the upload.

### 8. The public GitHub repository

On github.com as `AnthonyBeeblebrox` (or with `gh`), a public repository `chessop`, empty, with the pitch as its description and the three topics:

```sh
gh repo create AnthonyBeeblebrox/chessop --public \
  --description "Grind chess openings against the moves people at your rating really play, drawn from Lichess games. Free, no sign-up."
gh repo edit AnthonyBeeblebrox/chessop --add-topic chess --add-topic openings --add-topic spaced-repetition
git remote add github git@github.com:AnthonyBeeblebrox/chessop.git
```

`github` is the remote `deploy/publish.sh` pushes to (`CHESSOP_PUBLIC_REMOTE`); `AnthonyBeeblebrox/chessop` is what `deploy/deploy.sh` asks CI about (`CHESSOP_GITHUB`). If the repository lives elsewhere, set both variables, and correct `REPOSITORY` in `src/chessop/app.py`, which the site links.

### 9. The first deploy

Here, from a clean `main` (needs `git`, `curl` and `jq`):

```sh
deploy/publish.sh vX.Y.Z
gh run watch          # or the repository's Actions tab: wait for CI's run on the release commit
deploy/deploy.sh vX.Y.Z
```

`publish.sh` runs ruff and pytest, tags the private commit, pushes one squashed `Release vX.Y.Z` commit and its tag. `deploy.sh` refuses until CI is green, then on the VPS checks the tag out into `/opt/chessop/releases/vX.Y.Z`, installs it, points `current` at it and starts `chessop.service`; it asks for the admin user's `sudo` password. Then check, on the site and in the owner's inbox:

```sh
curl -fsS https://chessop.fr/healthz                          # ok
ssh -t chessop.fr sudo systemctl start chessop-notify@chessop.service.service   # a sample alert ("chessop.service failed": it did not)
ssh -t chessop.fr sudo systemctl start chessop-maintain.service         # the first backup, uploaded
ssh -t chessop.fr sudo journalctl -u chessop-maintain.service -n 20
```

and sign in by email at `https://chessop.fr/signin`: the link and code arrive from `login@chessop.fr`. The maintain run's journal ends with the upload; Scaleway console → Object Storage → the bucket shows `chessop-YYYY-MM-DD.sqlite.age`.

### 10. The GoatCounter site and login

GoatCounter waits for its site before it starts, so no stranger can create one. On the VPS (it asks for the owner's GoatCounter password):

```sh
ssh -t chessop.fr
sudo -u goatcounter /usr/local/bin/goatcounter db create site -createdb \
  -db sqlite+/var/lib/goatcounter/goatcounter.sqlite3 -vhost stats.chessop.fr -user.email <owner email>
sudo systemctl start goatcounter.service
```

Then sign in at `https://stats.chessop.fr` with that address and password; every start of `goatcounter.service` sets its retention to 760 days. Page views appear there once `https://chessop.fr` is visited (with `CHESSOP_GOATCOUNTER_URL` set, as it is).

### 11. UptimeRobot on `/healthz`

uptimerobot.com → create the account with the owner's own address → Add New Monitor → type HTTP(s) → URL `https://chessop.fr/healthz` → interval **5 minutes** → alert contact: the owner's address → Create. `/healthz` answers 200 only while the database answers and the snapshot is loaded. The certificate-expiry reminder is a paid option and is not needed: Caddy renews a month ahead, and the HTTPS check itself fails, and alerts, on an expired certificate.

### 12. The restore rehearsal

Once before launch, and again whenever the backup code (`src/chessop/backup.py`) changes: read last night's off-site copy back on the owner's machine and run the site on it.

Scaleway console → Object Storage → the bucket → `chessop-YYYY-MM-DD.sqlite.age` → Download (the owner's console account can read; the VPS's key cannot). Then here, in the private repository at the deployed release (`git switch --detach vX.Y.Z`; `git switch main` afterwards):

```sh
mkdir -p /tmp/chessop-restore
age --decrypt --identity ~/.config/chessop/backup.key \
  --output /tmp/chessop-restore/chessop.sqlite ~/Downloads/chessop-YYYY-MM-DD.sqlite.age
sqlite3 /tmp/chessop-restore/chessop.sqlite 'PRAGMA integrity_check'   # ok
uv run chessop stats --data-dir /tmp/chessop-restore
CHESSOP_BASE_URL=http://localhost:8000 CHESSOP_MAIL_FROM=login@chessop.fr CHESSOP_OWNER_EMAIL=<owner email> \
  uv run chessop serve --hosted --data-dir /tmp/chessop-restore
```

Hosted mode on `http://localhost` prints sign-in emails to the console instead of sending them. Open `http://localhost:8000/`, sign in with an address that played on the site and see its progress. Then delete the copy: `rm -r /tmp/chessop-restore ~/Downloads/chessop-*.sqlite.age`.

### 13. The load-test gate

Before launch, and after any change to the round-end path: `scripts/loadtest.py` against the VPS's own port, from the VPS, so each scripted learner is a client of its own and the memory can be read. The budget: the server's move handling and the end-to-end reply under 10 ms at p95 with 30 learners playing; resident memory under 1 GB at 300 sessions.

```sh
ssh chessop.fr
pid=$(systemctl show --property=MainPID --value chessop.service)
/opt/chessop/current/.venv/bin/python /opt/chessop/current/scripts/loadtest.py http://127.0.0.1:8000/ --learners 30 --duration 60 --pid "$pid"
/opt/chessop/current/.venv/bin/python /opt/chessop/current/scripts/loadtest.py http://127.0.0.1:8000/ --learners 300 --duration 120 --pid "$pid"
```

Each run prints `server move handling`, `end-to-end reply` and `resident memory` lines with their budgets beside them. The scripted learners are real anonymous learners in the database. Before the site is announced, clear them (and the rehearsal's own rounds) by starting from an empty database:

```sh
sudo systemctl stop chessop.service
sudo rm -f /var/lib/chessop/chessop.sqlite /var/lib/chessop/chessop.sqlite-wal /var/lib/chessop/chessop.sqlite-shm
sudo systemctl start chessop.service
```

## Routine

### Deploy

At a quiet hour: a restart loses rounds in flight, sessions and limit counters, at worst one unscored round per open tab. Here, from a clean `main` with the change committed:

```sh
deploy/publish.sh vX.Y.Z
gh run watch
deploy/deploy.sh vX.Y.Z
curl -fsS https://chessop.fr/healthz
```

- `publish.sh` refuses a dirty `main`, failing checks, an existing tag, or a secret pattern in the public tree (it names the file and line: remove it, or add its path to `deploy/public-exclude`). If only the push failed, it prints the `git push` to retry.
- `deploy.sh` refuses a tag CI has not passed. A new snapshot ships this way too; each learner sees the snapshot notice once.
- If `/healthz` does not answer within 30 s, `deploy.sh` points `current` back at the release before and restarts it. It never restores the database: if the new release migrated it, the old release refuses a schema newer than its own and stays down, so restore the pre-deploy copy it names (next section, source: pre-deploy copy).
- To go back by hand later, to a release still kept in `/opt/chessop/releases`:

```sh
ssh -t chessop.fr
sudo ln -sfn /opt/chessop/releases/<vX.Y.W> /opt/chessop/current.new
sudo mv --no-target-directory /opt/chessop/current.new /opt/chessop/current
sudo systemctl restart chessop.service
```

### Restore from a backup

Whenever the database is lost or broken, or a release must be undone past a migration. Pick the newest good copy (the folders are the `chessop` system user's alone, so list them with `sudo ls -l /var/lib/chessop/backups /var/lib/chessop/pre-deploy`):

- **the VPS is alive**: `/var/lib/chessop/backups/chessop-YYYY-MM-DD.sqlite` (14 nights), or a pre-deploy copy `/var/lib/chessop/pre-deploy/chessop-vX.Y.Z-<UTC time>.sqlite` (taken before that release touched the database);
- **the VPS is gone**: rebuild it (steps 1 to 7, the DNS records given the new addresses, then `deploy/deploy.sh` the last release), decrypt the newest off-site copy here as in step 12, and copy it up: `scp /tmp/chessop-restore/chessop.sqlite chessop.fr:`.

Then on the VPS, with chessop stopped, set the broken database aside (the `-wal` and `-shm` files with it, or SQLite replays them into the restored file) and put the copy in its place:

```sh
ssh -t chessop.fr
sudo systemctl stop chessop.service
sudo mkdir -p /root/chessop-broken
sudo sh -c 'mv /var/lib/chessop/chessop.sqlite* /root/chessop-broken/'
sudo install --mode=0600 --owner=chessop --group=chessop <copy> /var/lib/chessop/chessop.sqlite
sudo systemctl start chessop.service
curl -fsS http://127.0.0.1:8000/healthz
```

(`<copy>` is the backup's path, or `~/chessop.sqlite` for one copied up.) What a restore means for learners:

- **Deleted learners come back**: everyone deleted since the copy was taken, by a purge, "Forget this browser's history" or an account deletion, is in it again. Everything learners did since is lost.
- **The purges re-run** by themselves at 03:30; to run them now: `sudo systemctl start chessop-maintain.service`.
- **Deletion requests received by email are re-applied by hand**: every one answered in `contact@chessop.fr` since the copy's date, with the deletion of the next section. Self-service deletions made in the lost window are not replayed; the purges catch them up in time.

Once the site answers and the requests are re-applied, delete the set-aside files: `sudo rm -r /root/chessop-broken` (they hold learners' data).

### Rotate the mail key

Yearly, or at once if the key may have leaked. Scaleway console → IAM → Applications → `chessop-mail` → API keys → Generate an API key. Then put it in place and check that mail still goes:

```sh
ssh -t chessop.fr
sudoedit /etc/chessop/chessop.env          # CHESSOP_TEM_SECRET_KEY=<the new secret key>
sudo systemctl restart chessop.service
sudo systemctl start chessop-notify@chessop.service.service   # a sample alert arrives through the new key
```

Sign in by email once at `https://chessop.fr/signin` too. Then Scaleway console → IAM → Applications → `chessop-mail` → API keys → delete the old key. The timers read the environment file at each run and need nothing more. The backup bucket's key (`chessop-backup`, `CHESSOP_BACKUP_ACCESS_KEY` and `CHESSOP_BACKUP_SECRET_KEY`) rotates the same way, checked with `sudo systemctl start chessop-maintain.service`.

### Answer a data request by email

Requests arrive at `contact@chessop.fr`. Answer within one month (the privacy notice promises it), and keep the mail: a later restore re-applies deletions from it.

Most rights are self-service, so first point the learner at them: download everything (access, portability) and "Forget this browser's history" on `https://chessop.fr/data`; change the email address (correction) and delete the account on `https://chessop.fr/account`. An objection to the round log's use for refitting and usage counting is answered by deleting their data, as the privacy notice says. A request to restrict is answered by mail: the site has no way to keep a learner's data while not using it, so offer the export and the deletion, and do what they choose.

Do it by hand only for someone who cannot, and only once sure the request is theirs:

- **email account**: the request comes from the account's address, or the owner writes to that address and gets the confirmation back from it;
- **Lichess account**: chessop cannot tie a mail to a Lichess username: ask them to sign in with Lichess and use the pages above;
- **anonymous learner**: only the browser's cookie identifies one; nothing can be found by email. Say so, and that an idle anonymous history is deleted after 12 months (30 days with fewer than 5 rounds).

By hand, on the VPS, with chessop stopped so no live session of theirs writes after the change (`<kind>` is `email` or `lichess`, `<identity>` the address or the Lichess username):

```sh
ssh -t chessop.fr
sudo systemctl stop chessop.service
```

Export, the same JSON file `/data` gives, written in the admin user's home; fetch it with `scp chessop.fr:chessop-data.json .`, mail it to them, then delete both copies:

```sh
sudo -u chessop /opt/chessop/current/.venv/bin/python - <kind> <identity> > chessop-data.json <<'EOF'
import asyncio, sys, time
from pathlib import Path
from chessop.export import export
from chessop.store import Store

kind, identity = sys.argv[1], sys.argv[2].strip().lower()
store = Store.open(Path("/var/lib/chessop"))
account = store.account(kind, identity)
if account is None:
    sys.exit(f"no {kind} account {identity}")

async def write():
    async for piece in export(store.learner(account.learner_id), account, time.time()):
        sys.stdout.write(piece)

asyncio.run(write())
EOF
```

Delete, as the account page's deletion does (everything of theirs, counted in the usage aggregate):

```sh
sudo -u chessop /opt/chessop/current/.venv/bin/python - <kind> <identity> <<'EOF'
import sys, time
from pathlib import Path
from chessop.store import Store

kind, identity = sys.argv[1], sys.argv[2].strip().lower()
store = Store.open(Path("/var/lib/chessop"))
account = store.account(kind, identity)
if account is None:
    sys.exit(f"no {kind} account {identity}")
store.delete_learner(account.learner_id, time.time())
print(f"deleted the learner of the {kind} account {identity}")
EOF
```

Then `sudo systemctl start chessop.service`. Tell them the data leaves the backups within 30 days. Directives about what happens to a learner's data after their death arrive the same way: keep them with the mail and apply them when the time comes.

### A data breach

A breach is any leak, loss or unwanted change of learners' data: the VPS or the OVH, Scaleway or GitHub account taken over, the database or an unencrypted backup copied off, the mail key misused, a secret published.

1. **Contain**, at once. Rotate what may have leaked (the mail key and the backup key as above, the admin user's password, the SSH key); stop `chessop.service` if the VPS itself is in doubt, and rebuild it from step 1 with a restore rather than clean it. Session, link and code tokens are stored hashed and the off-site backups are encrypted, so a stolen database or bucket gives no way in by itself.
2. **Write it down**: what happened, when it was found, which data and how many learners, what was done. Every breach is recorded, notified or not (GDPR art. 33(5)); keep the record with the owner's papers, in neither repository.
3. **Notify the CNIL within 72 hours** of finding it, unless it is unlikely to put anyone at risk: notifications.cnil.fr → "Notifier une violation de données personnelles" → the online form. If not everything is known yet, notify on time with what is known and complete it later.
4. **Tell the learners** when the risk to them is high (art. 34): mail each email account (their addresses are in the `account` table) and say it on the site, in plain words: what happened, what it means for them, what was done, `contact@chessop.fr` for questions.
