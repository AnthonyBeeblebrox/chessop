# Opening explanations: can the text Lichess shows on its opening pages be used, and how?

Type: research
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

The learner asked, while reacting to the play-loop prototype: *"In lichess there are some documentation explaining openings, can we use this documentation?"* Lichess's opening pages (`https://lichess.org/opening/<name>`) show a prose explanation of each opening alongside the explorer. Establish, from primary sources:

- **What the text is and where it comes from.** It is believed to be the "Chess Opening Theory" wikibook on English Wikibooks, which Lichess embeds per move sequence; confirm, and find how Lichess maps an opening (the chess-openings TSV name / move sequence) to a page or section of it (the lila source is public: https://github.com/lichess-org/lila).
- **Licence.** The wikibook is believed to be CC BY-SA; confirm the exact licence and version and what attribution and share-alike mean for text shown inside a GPL-3.0-or-later local app (ADR 0004) that ships a CC0 openings list (ADR 0003). Say plainly whether it can be bundled in the snapshot, and what the attribution line must say.
- **How to fetch it.** The MediaWiki API on en.wikibooks.org (page title pattern for move sequences such as `Chess Opening Theory/1. e4/1...c5`), any dump, and whether Lichess exposes it through its own API. Rate limits, formats (wikitext / HTML / plain extract), and whether a whole-book pull for a snapshot build is feasible offline afterwards (ADR 0002: the app runs offline from the snapshot).
- **Coverage.** How many of the chess-openings TSV's 3,810 named lines (and of the 235-position 1800+ repertoire, `prototype/play-loop/tree.json`) have a page or section with real prose, how long the texts typically are, and whether pages exist for positions rather than move orders (transpositions, ticket 11).
- **Alternatives**, briefly: any other freely licensed opening explanations (Wikipedia opening articles, other wikibooks, the ECO codes' own descriptions), only to say whether one is a better fit.

Findings go to `docs/research/opening-explanations.md`; downloads (licence texts, a sample page in raw and rendered form, the lila mapping code) to `refs/openings-text/` with an index section in `refs/README.md`. No decision here: what the drill would *do* with the text (show it at the end of a round with the reveal, in the progress view, or not at all) is fog on the map until this comes back.

## Answer

Findings: [docs/research/opening-explanations.md](../../../docs/research/opening-explanations.md); sources in `refs/openings-text/`.

- **What it is.** Two texts. The prose on `lichess.org/opening/<name>` is Lichess's own user-written Markdown, stored in Lichess's MongoDB (`OpeningWiki.scala`, editors need an `OpeningWiki` permission, since Oct 2022), with no licence and no API: unusable. Only where Lichess has no description (placeholder "No description of the opening, yet.") does the browser fetch the Wikibooks "Chess Opening Theory" page — the same fetch the analysis board's Wikibooks box makes since 2021. Mapping is by move order: `Chess_Opening_Theory/1._e4/1...c5/2._Nf3` (`N._SAN` / `N...SAN`, `+!#?` stripped, ≤ 30 plies), `prop=extracts&redirects`, then Theory table / All possible replies / External links sections are cut and a "Read more on WikiBooks" link appended.
- **Licence.** CC BY-SA 4.0 (siteinfo, `Wikibooks:Copyrights`, page footer; GFDL dual-licence where applicable). It can be bundled in the snapshot as a separate CC BY-SA 4.0 data file next to the CC0 tree inside the GPL-3.0-or-later app (aggregation, not adaptation; CC declared GPLv3 one-way compatible in 2015 for the adaptation case, which does not arise if the text stays data). Obligations: a licence notice with the licence URL or a copy, a link to each Wikibooks page used (the attribution the Terms of Use accept), and a note that the text was trimmed.
- **Fetch.** MediaWiki API at `en.wikibooks.org/w/api.php`, no auth for reads; whole book in wikitext = 52 batched requests (2,563 pages, ~4.6 MB); Lichess-style whole-page extracts are one request per page; mandatory descriptive `User-Agent` with contact, serial requests, `maxlag=5`, < 5 req/s; a 203 MB whole-wiki dump also exists. Lichess's API exposes nothing. Pulled once at snapshot build, it is offline afterwards.
- **Coverage.** Book: 2,563 pages + 464 redirects. Repertoire `tree.json` (288 non-root nodes as the file stands): 208 (72.2%) have a page (16 via transposition redirects), 175 (60.8%) with ≥ 200 chars of prose, and 100% have such a text at self or an ancestor; median text ~870 chars, q3 ~2,000. TSV (3,810 lines): 944 (24.8%) any page, 762 (20.0%) with ≥ 200 chars, falling with depth (0 beyond ply 22), best in ECO C, worst in E. Pages are per move order; transpositions only via the redirects.
- **Alternatives.** None better: Wikipedia is the same licence but per family (no per-line text); chess-openings/ECO carry names only; Lichess's own text is unlicensed.
