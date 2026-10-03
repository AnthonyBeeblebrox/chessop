# 45: Publish, CI and deploy scripts

**What to build:** A release ships only when the owner chooses. `publish.sh vX.Y.Z` refuses a dirty `main`, runs ruff and pytest, tags the private commit, copies its tree onto the local `public` branch minus the paths in a public-exclude list (the third-party PDF and HTML copies under the references folder, the loop script, the first wayfinder prompt, the token file), scans for secret patterns (Lichess tokens, TEM keys) and refuses on a hit, commits `Release vX.Y.Z`, tags and pushes. The references README becomes a bibliography of links. A GitHub Actions workflow on the public repo runs `uv sync --frozen`, ruff and pytest on the pinned Python on every push and tag, and never deploys. `deploy.sh vX.Y.Z`, run by hand over SSH, requires a public tag whose CI run is green, checks it out into its release directory, runs `uv sync --frozen --no-dev`, takes a pre-deploy SQLite backup (last 3 kept), switches the symlink, restarts, polls `/healthz` for 30 s and on failure switches back and restarts. The database is never restored automatically; the last 3 releases are kept. (Spec §14.)

**Blocked by:** 17, 20

**Status:** done

- [x] `publish.sh` refuses on a dirty tree, on failing checks and on a planted secret pattern (tried against a scratch clone, pushing nowhere)
- [x] The public tree lacks every excluded path and contains source, tests, docs, `.scratch`, prototypes and licences
- [x] The references README lists links in place of the removed copies
- [x] The workflow runs lint and tests on push and tag and has no deploy step
- [x] `deploy.sh` refuses a tag without a green CI run and rolls the symlink back when the health check fails (read through; exercised for real in ticket 48)
- [x] Both scripts pass `shellcheck`
