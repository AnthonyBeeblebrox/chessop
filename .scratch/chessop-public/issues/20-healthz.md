# 20: /healthz

**What to build:** `/healthz` answers 200 only when the database answers and the snapshot is loaded, and a non-200 otherwise, in both modes. It is what the uptime check and the deploy script will poll. (Spec §12.)

**Blocked by:** None (can start immediately)

**Status:** done

- [x] `/healthz` returns 200 on a healthy app, through the test client
- [x] It returns a failing status when the database cannot be queried or no snapshot is loaded
- [x] It is served in local mode too
