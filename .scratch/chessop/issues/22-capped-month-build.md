# Capped month build: the whole-month trie does not fit in memory

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Building v1 reopened one point after the destination was reached. The spec review of build ticket 03 (`.scratch/chessop-v1/issues/03-build-snapshot-graph-file.md`) found that `build-snapshot` as specified cannot run: ADR 0003 and spec §3.1 read **one whole recent month**, and §3.2 walks every game into an in-memory move trie to ply 36. Ticket 17's reference build peaked at 5.2 GB on about 700k kept games (1.6 % of the 2026-08 file); a whole month is about 90 M games, some 45 M kept, about 1.2 billion trie nodes, in the order of 400 GB. Options weighed with the learner on 2026-09-24:

- **Cap games per band** from the start of the month, the scale ticket 17 measured.
- **Walk the Opening Explorer at build time** (pooled by position for free, but a token, 25 requests per minute, hours per band, the explorer's own rating groups, no move orders for the canonical order or diffuse traffic).
- **Two passes over the whole month** (a bounded-memory candidate count, then exact counts): all the data, over an hour and a new method.

## Answer

Decided by the learner on 2026-09-24: **cap at 150,000 kept games per band**. Folded into ADR 0003 (ticket 22 amendment), [`spec.md`](../spec.md) §2, §3.1, §3.3, §14, and build ticket 03.

- **The sample is a capped prefix of one recent month.** The dump is read from its start; once a band holds 150,000 games that passed the filters, its further games are dropped; reading stops when every band is full or the month ends. 2100 and above fills slowest (44k after 1.6 % of 2026-08), so a release build reads about 5–6 % of the file, a few minutes of streaming and about 6 GB of peak memory.
- **Why 150k**: ticket 17 stopped 1800–2100 at exactly 150,000, so its numbers (1,104 positions, 1,985 branches, 17 plies at the defaults) stay valid as the build's sanity bounds, and every band is well above the size ADR 0003 asked for ("well over 100 k games").
- **Unchanged**: the filters, the five bands, the storage cut-off of 0.02 % of the band's kept games (now 30 games in a full band), the ply cap, the files. `--max-games` stays a developer switch on games read.
- **Metadata** records the cap, the games read and the compressed bytes read, beside the month, so a rebuild on the same URL reproduces the same prefix.
- **Call made without asking** (the standards review of the same run): `zstandard` is a build-time dependency, not a runtime one. It lives in an optional extra, `chessop[build]`, and the build module is imported only when `build-snapshot` runs, so spec §2's runtime list stays true.
