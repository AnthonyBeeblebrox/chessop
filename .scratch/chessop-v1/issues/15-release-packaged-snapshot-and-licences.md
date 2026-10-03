# 15: Release: packaged snapshot and licences

**What to build:** a learner installs chessop with `uv tool install` from the repository and drills straight away, offline, on snapshot files built from a recent month that ship inside the package, with every licence obligation met.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §2, §3.3, §4 (expected size), §12, §13 (slow bound test), §14.

**Blocked by:** 03 (`build-snapshot`: the graph file), 08 (Explanations), 09 (Sounds and animation).

**Status:** done

- [x] Graph and explanation files built from a recent whole month, shipped as package data, sharing one version string; `--snapshot` still overrides
- [x] Diagnostics checked against ticket 17's numbers (1800–2100 at the defaults: ~1,104 positions, ~1,985 branches, 17 plies) and recorded in the ticket
- [x] Slow-marked test of the §4 bounds against the packaged snapshot
- [x] `LICENSES/`: GPL-3.0-or-later, AGPL-3.0, CC-BY-SA-4.0, CC-BY-SA-3.0, CC0; README with a Licences section and each attribution
- [x] `uv tool install` from a clean checkout gives a working `chessop` with no network access at runtime
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass

## Release build (2026-09-24)

`uv run chessop build-snapshot --month 2026-08` (August 2026, the latest whole month), copied to
`src/chessop/data/snapshot.graph.json.gz` and `snapshot.explanations.json.gz`, the default of
`--snapshot`. Two runs gave byte-identical graph files. The book commit is the hash of the
`refs/lichess/` TSV files (no `COMMIT` file). The first run's explanation step died on an HTTP 503
from Wikibooks; the API client now waits out 429/502/503/504 and retries.

```
snapshot 2026-08/0-1200,1200-1500,1500-1800,1800-2100,2100+/sha256-9bead1d24689/1
games read 4,769,401, 1,568,972,800 compressed bytes (stopped: every band full)
dropped by the filters: bullet or ultrabullet 1,912,204, players in different bands 448,457, BOT title 21,672
band 0-1200: 150,000 games kept, 293,002 dropped as the band was full, 0 cut at a rejected SAN
  stored 3,761 positions, 3,617 edges; 0 edges dropped closing a cycle; diffuse 1,269 positions, 815 edges
  repertoire at the defaults: 436 positions, 536 edges, 593 branches, 144 leaves, 13 plies deep, 312 book lines covered
band 1200-1500: 150,000 games kept, 402,542 dropped as the band was full, 0 cut at a rejected SAN
  stored 4,349 positions, 4,123 edges; 0 edges dropped closing a cycle; diffuse 1,593 positions, 1,029 edges
  repertoire at the defaults: 599 positions, 755 edges, 1,085 branches, 177 leaves, 13 plies deep, 396 book lines covered
band 1500-1800: 150,000 games kept, 581,795 dropped as the band was full, 0 cut at a rejected SAN
  stored 4,702 positions, 4,451 edges; 0 edges dropped closing a cycle; diffuse 1,801 positions, 1,197 edges
  repertoire at the defaults: 794 positions, 976 edges, 1,097 branches, 250 leaves, 15 plies deep, 513 book lines covered
band 1800-2100: 150,000 games kept, 359,729 dropped as the band was full, 0 cut at a rejected SAN
  stored 5,260 positions, 5,022 edges; 0 edges dropped closing a cycle; diffuse 2,066 positions, 1,450 edges
  repertoire at the defaults: 1,104 positions, 1,326 edges, 1,985 branches, 310 leaves, 17 plies deep, 662 book lines covered
band 2100+: 150,000 games kept, 0 dropped as the band was full, 0 cut at a rejected SAN
  stored 6,549 positions, 6,339 edges; 0 edges dropped closing a cycle; diffuse 2,750 positions, 2,172 edges
  repertoire at the defaults: 1,850 positions, 2,170 edges, 5,189 branches, 418 leaves, 24 plies deep, 956 book lines covered
wrote src/chessop/data/snapshot.graph.json.gz
  explanations: 1,464 titles to fetch
explanations: 1,299 pages for 1,300 positions
wrote src/chessop/data/snapshot.explanations.json.gz
```

At 1800-2100 the repertoire at the defaults is ticket 17's figures exactly: 1,104 positions,
1,326 edges, 1,985 branches, 310 leaves, 17 plies deep, 662 book lines covered.
`tests/test_packaged_snapshot.py` checks the §4 bounds (slow) and the shared version string.
`uv tool install .` from a clean copy of the files this commit tracks installed a `chessop` that served the play
page, the progress view and a round from the packaged 1500-1800 band with its explanations; the
runtime modules make no outbound request (only `build` and `wikibooks` do).
