# 41: Usage aggregate and chessop stats

**What to build:** The owner can tell whether anyone uses the site. A daily usage aggregate keeps one row per UTC day, counts only, never learner ids: active learners (anonymous and signed-in), new learners, rounds, successes, sign-ins, adoptions, deletions. Sign-ins, adoptions and deletions are incremented in the day's row as they happen; the derived counts for a finished day are filled in once (the nightly call arrives in ticket 42) and rows are kept forever. "Active" means at least one round logged that UTC day; the success rate is net of forced exploration. `chessop stats` reads the database and prints tables: active learners per day, week and month; new learners per day; rounds per day and per active learner; overall success rate; sign-ins and adoptions per day; retention after 1, 7 and 30 days; band and opening choices of active learners; snapshot versions in use. Past days come from the aggregate; retention and the mixes are computed live. No admin page. (Spec §12, G4.)

**Blocked by:** 30, 32, 33

**Status:** done

- [x] A sign-in, an adoption and each kind of deletion increment that day's row
- [x] Writing a finished day's derived counts twice changes nothing
- [x] The aggregate holds no learner id and survives the deletion of every learner
- [x] `chessop stats` over a seeded database prints each listed table with the expected figures
