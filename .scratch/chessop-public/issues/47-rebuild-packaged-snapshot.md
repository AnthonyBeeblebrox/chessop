# 47: Rebuild the packaged snapshot with eight bands

**What to build:** The packaged snapshot is rebuilt with all eight bands so the shipped default, 1500+, really exists in it. This needs the Lichess dump month and about 11 GB of memory on the owner's machine, about 14 minutes; an agent cannot run it. Until it is done, the app falls back as ticket 18 describes.

**Blocked by:** 18

**Status:** done

- [x] The build is run on the dump with the eight-band build tool
- [x] The packaged snapshot files are replaced and the snapshot version bumped
- [x] The packaged-snapshot test passes and 1500+ loads without the fallback
- [x] File sizes stay within what the repository and the VPS can carry

## Comments

- From ticket 18: until this rebuild, a snapshot without 1500+ falls back to its closed 1500-1800 (`FALLBACK_BANDS` in `cli.py`) so the app still starts. A learner who saves settings meanwhile stores `band=1500-1800` and stays there after the rebuild. Once 1500+ ships, `FALLBACK_BANDS` can shrink to the default alone, and the strict xfail on `test_the_packaged_graph_holds_every_band` must come off.
- Done 2026-10-02, on the owner's machine (121 GB of memory, so an agent could run it after all): 2026-08 dump, 4,769,401 games read, every band full at 150,000; peak about 10 GB, about 15 minutes. Version `2026-08/0-1200,1200-1500,1500-1800,1800-2100,2100+,1200+,1500+,1800+/sha256-9bead1d24689/1`: the band list changed, the build revision stayed 1. Graph file 1,533,880 bytes (was 945,694), explanation file 436,023 bytes (was 431,852). 1500+ at the defaults: 2,945 positions, 3,296 edges, 1,045 leaves, 17 plies deep. `FALLBACK_BANDS` is the default alone, so a snapshot holding neither the stored band nor 1500+ now exits at startup instead of drilling 1500-1800.
