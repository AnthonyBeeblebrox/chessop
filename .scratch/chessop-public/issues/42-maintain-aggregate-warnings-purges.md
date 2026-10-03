# 42: chessop maintain: aggregate, warnings, purges

**What to build:** One nightly command keeps the site legal with nothing to remember. `chessop maintain` runs in order: write yesterday's aggregate row; send account warnings; run the three purges. Anonymous learners are deleted after 12 months with no request, and after 30 days with no request if they have fewer than 5 rounds. Accounts are deleted after 24 months with no request: email accounts are warned by email at 23 months (`warned_at` set) and deleted only when the warning is at least 30 days old and the account is still unseen; any request clears `warned_at`; Lichess accounts are deleted at 24 months with no warning. Each step is idempotent and logs its counts; a failed step does not stop the later ones but makes the run exit non-zero. (The backup step is ticket 43.) (Spec §10, §13.)

**Blocked by:** 40, 41

**Status:** done

- [x] Each purge boundary holds exactly: a learner one day short is kept, one at the boundary is deleted (injected clock)
- [x] An email account gets one warning at 23 months and is deleted no sooner than 30 days after it; a visit in between clears the warning and keeps the account
- [x] A warning that could not be sent sets no `warned_at`, so deletion waits
- [x] Lichess accounts are deleted at 24 months with no email
- [x] Running `maintain` twice in a day changes nothing the second time
- [x] A failing step yields a non-zero exit while the later steps still run
- [x] Purge deletions are counted in the aggregate
