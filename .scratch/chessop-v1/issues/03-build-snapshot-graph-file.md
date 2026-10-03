# 03: `build-snapshot`: the graph file

**What to build:** the developer runs `chessop build-snapshot --month YYYY-MM` and gets a graph file with all five bands from a capped prefix of one month of the Lichess dump (at most 150,000 kept games per band, ticket 22), then drills a real band with `chessop --snapshot <file>`. The build streams the `.pgn.zst`, filters games, pools counts by position, cuts at the storage cut-off, guarantees a DAG, attaches exact book names, canonical orders and book lines, prints the diagnostics (including the repertoire size under ticket 02's default load rule) and stamps the version string.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §2 (`build-snapshot` flags), §3.1, §3.2 steps 1–5, §3.3 (graph file, version string). ADR 0003 (with its ticket 22 amendment), ADR 0006; [ticket 22](../../chessop/issues/22-capped-month-build.md); `docs/research/pooled-repertoire.md` method section is the reference procedure.

**Blocked by:** 02 (Repertoire rule at load).

**Status:** done

- [x] `chessop build-snapshot --month YYYY-MM [--max-games N] [--book <dir>] [--out <path>]`; the dump streamed through a zstandard decompressor, nothing large written to disk
- [x] Cap of 150,000 kept games per band: a full band drops its further games, reading stops when every band is full or the month ends; peak memory stays in single-digit GB
- [x] `zstandard` in the optional extra `chessop[build]`, not a runtime dependency; the build module imported only when `build-snapshot` runs, so the server never loads it
- [x] Filters: both Elos present and numeric, both in the same band, no BOT title, no Bullet/UltraBullet; five bands, lower bound inclusive
- [x] Walk to ply 36 keyed by `Board.epd()`; rejected SAN drops the rest of the game and is counted
- [x] Pooled position and edge counts; canonical order = most popular node's path (ties first seen); book line stored for exactly-named positions; family = part before the first colon
- [x] Storage cut-off `count >= 0.0002 * N`, unrounded; edges added in BFS order, an edge closing a cycle dropped and counted
- [x] Diagnostics per band: games kept/dropped per filter, positions/edges stored, dropped-cycle edges, diffuse traffic, and repertoire size at the defaults (positions, edges, branches, leaves, max depth, book lines covered)
- [x] Graph file metadata (month, band set, book commit, build revision, cut-off, ply cap, the cap, games read and compressed bytes read, per-band games and diagnostics) and version string `<month>/<band set>/<book commit>/<build revision>`
- [x] The server loads one band from a built file and plays rounds on it
- [x] Tests on a tiny PGN fixture: filters, the per-band cap and stop rule, pooling, cycle dropping on a constructed move-order shuffle, names, canonical orders, diagnostics, version string
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
