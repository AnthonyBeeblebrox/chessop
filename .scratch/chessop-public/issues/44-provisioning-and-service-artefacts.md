# 44: Provisioning and service artefacts

**What to build:** The repository can rebuild the box. A deploy directory holds: an idempotent `provision.sh` for a fresh Debian 13 VPS (system user, pinned uv, uv-managed CPython 3.12, Caddy, firewall on 22/80/443, unattended upgrades, SSH password login off, the `/opt/chessop` release layout with a `current` symlink, `/var/lib/chessop`, `/etc/chessop/chessop.env` at root:chessop 0640, the journald drop-in capped at 6 months and 500 MB, GoatCounter from a pinned release binary with its SHA-256 checked, own user, unit and 760-day retention); the hardened `chessop.service`; the `chessop-maintain` timer at 03:30 UTC, persistent; the daily disk check above 80 % and the daily error digest sent only when non-empty, both through `notify-owner`; the `chessop-notify@` template wired as `OnFailure=` from the chessop, maintain, disk, digest and GoatCounter units; the Caddyfile (automatic HTTPS, `www` and http redirected to the apex, HSTS, WebSockets proxied, access logging off, a static "back in a moment" page on 502, `stats.chessop.fr` proxied to GoatCounter with a disallow-all `robots.txt`); and an environment-file example listing every variable. None of it runs in CI. (Spec §14, ADR 0007.)

**Blocked by:** 20, 43

**Status:** done

- [x] Every artefact listed in the spec's §14 up to the Caddyfile and the environment-file example exists
- [x] `provision.sh` is written to be re-runnable and passes `shellcheck`; the units pass `systemd-analyze verify` and the Caddyfile `caddy validate` where those tools are available
- [x] The service unit carries the stated hardening, restart policy and `OnFailure=`
- [x] The environment-file example names every variable of the spec's table and no secret value
