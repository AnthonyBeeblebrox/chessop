# refs

The bibliography behind the research in `docs/research/`: one section per research ticket, one line per source, saying what it is, where it came from, and why it matters.

The third-party papers and web pages are cited by their links only: their PDF and HTML copies are not published with chessop. A line that names a file names one that is here: API specifications, source excerpts and wikitext kept as evidence under their own licences, and our own analysis scripts and measurements.

## Web/board stack (ticket 03)

Saved 2026-09-11 into `stack/`; findings in `docs/research/web-board-stack.md`.

- `stack/chessground-README.md`: Lichess chessground README (features, GPL-3.0-or-later terms, wrappers). Source: https://raw.githubusercontent.com/lichess-org/chessground/master/README.md. Why: licence statement and feature list for the most polished JS board.
- `stack/chessground-config.ts`: chessground Config type (movable.dests, movable.events.after, animation.duration). Source: https://raw.githubusercontent.com/lichess-org/chessground/master/src/config.ts. Why: the exact input/callback contract.
- `stack/chessground-api.ts`: chessground Api type (set, move, getFen, setShapes, cancelMove). Source: https://raw.githubusercontent.com/lichess-org/chessground/master/src/api.ts. Why: what the app can drive programmatically.
- `stack/chessground-examples-play.ts`, `stack/chessground-examples-util.ts`: official "play vs random" example with chess.js dests. Source: https://github.com/lichess-org/chessground-examples/tree/master/src. Why: canonical client-side move loop pattern.
- `stack/chessboardjs-README.md`: chessboard.js README (MIT, jQuery dependency, Dec 2022 status note). Source: https://raw.githubusercontent.com/oakmac/chessboardjs/master/README.md. Why: maturity/maintenance status.
- The chessboard.js docs (onDrop snapback, moveSpeed, jQuery version). Source: https://chessboardjs.com/docs.html. Why: input contract and animation timings.
- `stack/chessboard2-README.md`: chessboard2 README (ISC, ClojureScript, "development in progress" since April 2023). Source: https://raw.githubusercontent.com/oakmac/chessboard2/master/README.md. Why: shows it is unfinished.
- The chessboard2 download page. Source: https://chessboardjs.com/v2/download. Why: CDN availability of 0.5.0.
- `stack/cm-chessboard-README.md`: cm-chessboard README (MIT, no deps, SVG, enableMoveInput event types, animationDuration). Source: https://raw.githubusercontent.com/shaack/cm-chessboard/master/README.md. Why: recommended board's full API.
- `stack/python-chess-README.rst`: python-chess README (GPL-3.0+, features). Source: https://raw.githubusercontent.com/niklasf/python-chess/master/README.rst. Why: licence and scope of the server-side chess library.
- python-chess chess.svg docs (board() signature: lastmove, check, arrows, fill, size, style). Source: https://python-chess.readthedocs.io/en/latest/svg.html. Why: what server-rendered boards can show.
- `stack/python-chess-svg.py`: chess.svg source (ElementTree-based rendering). Source: https://raw.githubusercontent.com/niklasf/python-chess/master/chess/svg.py. Why: basis for the render-cost benchmark.
- `stack/nicegui-README.md`: NiceGUI README incl. Architecture section (FastAPI + Vue/Quasar, socket.io, single uvicorn worker, outbox batching). Source: https://raw.githubusercontent.com/zauberzeug/nicegui/main/README.md. Why: transport and worker model.
- NiceGUI ui.run reference (native, reload, port, host). Source: https://nicegui.io/documentation/run. Why: deployment switches.
- NiceGUI configuration & deployment section (Docker image, nicegui-pack, custom FastAPI app). Source: https://nicegui.io/documentation/section_configuration_deployment. Why: deployment simplicity.
- NiceGUI generic events (.on with throttle, attribute filtering, js_handler). Source: https://nicegui.io/documentation/generic_events. Why: per-move event cost controls.
- NiceGUI @ui.page per-client instances. Source: https://nicegui.io/documentation/page, https://nicegui.io/documentation/section_pages_routing. Why: multi-user isolation.
- `stack/nicegui-custom-vue-component-README.md`: custom Vue/JS component example. Source: https://raw.githubusercontent.com/zauberzeug/nicegui/main/examples/custom_vue_component/README.md. Why: how a JS board would be embedded.
- `stack/reflex-README.md`: Reflex README. Source: https://raw.githubusercontent.com/reflex-dev/reflex/main/README.md. Why: overview and licence.
- Reflex architecture blog (Next.js frontend, FastAPI backend, WebSocket events, state deltas, Redis). Source: https://reflex.dev/blog/2024-03-21-reflex-architecture/. Why: round-trip model.
- Reflex events overview. Source: https://reflex.dev/docs/events/events-overview/. Why: event handler semantics.
- Reflex self-hosting (ports 3000/8000, api_url, static export, Docker). Source: https://reflex.dev/docs/hosting/self-hosting/. Why: deployment complexity.
- Reflex: wrapping React components (library/tag/event triggers). Source: https://reflex.dev/docs/wrapping-react/overview/. Why: how react-chessboard would be wrapped.
- Streamlit main concepts (script reruns top to bottom). Source: https://docs.streamlit.io/get-started/fundamentals/main-concepts. Why: the rerun model.
- Streamlit architecture (Tornado WebSockets, session per tab). Source: https://docs.streamlit.io/develop/concepts/architecture/architecture. Why: transport and sessions.
- Streamlit custom components (iframe, setComponentValue triggers rerun). Source: https://docs.streamlit.io/develop/concepts/custom-components/intro. Why: board embedding cost.
- Streamlit fragments (partial reruns since 1.37). Source: https://docs.streamlit.io/develop/concepts/architecture/fragments. Why: mitigation of full reruns.
- `stack/streamlit-chess-README.md`: streamlit-chess/stchess README (2021, chessboardjsx). Source: https://raw.githubusercontent.com/TheoLvs/streamlit-chess/main/README.md. Why: the only existing Streamlit chess component.
- Panel JSComponent reference (_esm, _importmap, send_event, param sync). Source: https://panel.holoviz.org/reference/custom_components/JSComponent.html. Why: how a JS board would be embedded in Panel.
- Panel server how-to (Bokeh/Tornado, sessions). Source: https://panel.holoviz.org/how_to/server/index.html. Why: transport and deployment.
- htmx home (~16k min.gz, dependency-free) and docs (hx-trigger/target/swap). Source: https://htmx.org/, https://htmx.org/docs/. Why: SSR swap model.
- htmx ws extension (ws-connect, ws-send, OOB swaps). Source: https://htmx.org/extensions/ws/. Why: WebSocket variant of SSR.
- `stack/htmx-LICENSE.txt`: htmx licence (Zero-Clause BSD). Source: https://raw.githubusercontent.com/bigskysoftware/htmx/master/LICENSE. Why: licence check.
- FastAPI WebSockets guide. Source: https://fastapi.tiangolo.com/advanced/websockets/. Why: the per-session socket endpoint pattern.
- Flask-SocketIO requirements (threading/gevent/eventlet, message queue for multiple workers) and deployment. Source: https://flask-socketio.readthedocs.io/en/latest/. Why: what Flask needs for WebSockets.

## Sampling and scheduling algorithms (ticket 04)

Findings: `docs/research/sampling-algorithms.md`. Files live in `refs/algorithms/`.

- Wozniak's original SM-2 description (interval, EF update, EF >= 1.3 floor, reset on q < 3). Source: https://super-memory.com/english/ol/sm2.htm. The baseline interval-based scheduler every later system compares to.
- `algorithms/anki-deck-options.md` — Anki manual "Deck Options" (starting ease 2.5, hard 1.2, easy bonus 1.3, new interval 0, minimum interval, interval modifier, FSRS settings). Source: https://github.com/ankitects/anki-manual/blob/main/src/deck-options.md. The production SM-2 variant's constants and failure handling.
- `algorithms/fsrs-algorithm-wiki.md` — FSRS "The Algorithm" wiki, v1 through FSRS-6: forgetting curve, stability after recall/lapse, difficulty damping and mean reversion, default parameters. Source: https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm. The best-fitted general memory model; its formulas are the DSR need model candidate.
- `algorithms/py-fsrs-scheduler.py` — py-fsrs reference scheduler. Source: https://github.com/open-spaced-repetition/py-fsrs/blob/main/fsrs/scheduler.py. Shows the clamps (D in [1,10], S >= 0.001), interval bounds and fuzz a production FSRS applies.
- Settles & Meeder, "A Trainable Spaced Repetition Model for Language Learning", ACL 2016. Source: https://aclanthology.org/P16-1174.pdf. Half-life regression p = 2^(-d/h), h = 2^(theta.x); shows Leitner = weights (+1, -1) and reports MAE/AUC against baselines.
- `algorithms/duolingo-hlr-README.md` — Duolingo halflife-regression repo README (dataset columns, citation). Source: https://github.com/duolingo/halflife-regression. Documents the learning-trace schema the trainer should log.
- `algorithms/duolingo-hlr-experiment.py` — Duolingo HLR reference code with Leitner and Pimsleur baselines and clipping constants (h in [15 min, 9 months], p in [0.0001, 0.9999]). Source: https://raw.githubusercontent.com/duolingo/halflife-regression/master/experiment.py. The exact floors and sqrt(1+count) features used in production.
- Reddy, Labutov, Banerjee & Joachims, "Unbounded Human Learning: Optimal Scheduling for Spaced Repetition", KDD 2016. Source: https://arxiv.org/abs/1602.07032. Formal Leitner model P[recall] = exp(-theta d/q), reflecting deck 1, and the phase transition when new items arrive too fast.
- Anderson & Schooler, "Reflections of the Environment in Memory", Psychological Science 1991. Source: https://users.cs.northwestern.edu/~paritosh/papers/KIP/AndersonSchooler1991ReflectionsOfEnvironmentOnMemory.pdf. Evidence that need odds follow power laws in frequency and recency; the rationale for ACT-R's activation sum.
- Pavlik & Anderson, "Practice and Forgetting Effects on Vocabulary Memory", Cognitive Science 2005. Source: http://act-r.psy.cmu.edu/wordpress/wp-content/uploads/2012/12/409s15516709cog0000_14.pdf. ACT-R activation m = ln sum t^-d, logistic recall, activation-dependent decay, fitted parameters.
- Sutton & Barto, "Reinforcement Learning: An Introduction" 2nd ed. (ch. 2 used). Source: http://incompleteideas.net/book/RLbook2020.pdf. Canonical statements of epsilon-greedy, UCB (eq. 2.10) and soft-max/Boltzmann selection (eqs. 2.11-2.12).
- Cesa-Bianchi, Gentile, Lugosi & Neu, "Boltzmann Exploration Done Right", NeurIPS 2017. Source: https://arxiv.org/abs/1705.10257. Why plain softmax ignores uncertainty, the Gumbel-max sampling identity, and the per-arm temperature 1/sqrt(N) variant.
- Vose, "A Linear Algorithm for Generating Random Numbers with a Given Distribution", IEEE TSE 1991. Source: https://web.archive.org/web/20131029203736/http://web.eecs.utk.edu/~vose/Publications/random.pdf. O(n) alias-table build, O(1) draw, for per-node sampling when branching is large.
- Stratos, "The Alias Method" (short formal proof). Source: https://karlstratos.com/notes/alias_method.pdf. Compact correctness argument for the alias construction.

## Lichess data (ticket 02)

All in `lichess/`. Findings: [docs/research/lichess-data.md](../docs/research/lichess-data.md).

- `lichess/lichess-api-openapi.yaml` — root Lichess OpenAPI spec (rate limiting, auth, OAuth2 scheme, explorer tag text). Source: https://raw.githubusercontent.com/lichess-org/api/master/doc/specs/lichess-api.yaml. The authoritative statement of API-wide rules.
- `lichess/openapi-explorer-masters.yaml` — `/masters` endpoint spec (params, defaults, `security: OAuth2`). Source: https://github.com/lichess-org/api/blob/master/doc/specs/tags/openingexplorer/masters.yaml. Exact parameter names/defaults for the masters tree.
- `lichess/openapi-explorer-lichess.yaml` — `/lichess` endpoint spec (ratings groups, speeds, topGames/recentGames caps, history). Source: same dir, `lichess.yaml`. The endpoint the trainer would actually query.
- `lichess/openapi-explorer-player.yaml` — `/player` endpoint spec (ND-JSON stream, on-demand indexing). Source: same dir, `player.yaml`. Basis for seeding from the learner's own games.
- `lichess/openapi-explorer-masters-pgn-gameId.yaml` — `/masters/pgn/{gameId}` spec. Source: same dir, `masters-pgn-gameId.yaml`. Marked OAuth2 but observed to serve without a token.
- `lichess/openapi-schema-OpeningExplorerMasters.yaml` — JSON schema of `/masters` response. Source: https://github.com/lichess-org/api/tree/master/doc/specs/schemas. Field names for the parser.
- `lichess/openapi-schema-OpeningExplorerLichess.yaml` — JSON schema of `/lichess` response (adds recentGames, history). Source: same. Field names for the parser.
- `lichess/openapi-schema-OpeningExplorerPlayer.yaml` — JSON schema of `/player` rows (queuePosition, performance, averageOpponentRating) with a full example. Source: same. Field names for the parser.
- `lichess/openapi-schema-OpeningExplorerMastersGame.yaml` — game object in masters responses. Source: same. Sub-schema.
- `lichess/openapi-schema-OpeningExplorerLichessGame.yaml` — game object in lichess responses (speed, month nullable). Source: same. Sub-schema.
- `lichess/openapi-schema-OpeningExplorerPlayerGame.yaml` — game object in player responses (mode). Source: same. Sub-schema.
- `lichess/openapi-schema-OpeningExplorerGamePlayer.yaml` — `{name, rating}` player object. Source: same. Sub-schema.
- `lichess/openapi-schema-OpeningExplorerOpening.yaml` — `{eco, name}` opening object. Source: same. Sub-schema.
- `lichess/openapi-example-openingExplorer-masters.json.yaml` — real captured `/masters` response body used as the doc example. Source: https://github.com/lichess-org/api/tree/master/doc/specs/examples. Stand-in for a live call (API needs a token).
- `lichess/openapi-example-openingExplorer-lichess.json.yaml` — real captured `/lichess` response body (12 moves, games, counts in the millions). Source: same. Stand-in for a live call; shows size (~5 KB).
- `lichess/openapi-example-openingExplorer-player.json.yaml` — real captured `/player` ND-JSON row. Source: same. Stand-in for a live call.
- `lichess/openapi-commit-ac27c30-explorer-auth.diff.txt` — diff of spec commit ac27c30 (2026-03-03) switching hosts to explorer.lichess.org and adding OAuth2 to the explorer endpoints. Source: https://github.com/lichess-org/api/commit/ac27c30086a66ba6bd00b399341e5e6ca0906eec. Proof of when/why anonymous access ended.
- Thibault's 3 Mar 2026 post: token required, 25 req/min, 50 plies max, DDoS rationale. Source: https://lichess.org/@/thibault/blog/the-opening-explorer-now-requires-authentication/FSWh9Zg3. The only published rate limit for the explorer.
- The Lichess feedback-forum thread reacting to the change, links the blog and lila commit. Source: https://lichess.org/forum/lichess-feedback/why-this-change-using-the-opening-explorer-now-requires-being-logged-in. Context only.
- `lichess/explorer-401-no-token.headers` — HTTP response headers from `curl https://explorer.lichess.org/masters` without a token on 2026-09-11 (401). Source: live call. Evidence that anonymous access is refused.
- `lichess/masters-pgn-sample.pgn` — PGN returned by `/masters/pgn/aAbqI4ey` without a token (Carlsen–Chadaev 2012). Source: live call to https://explorer.lichess.ovh/masters/pgn/aAbqI4ey. Shows the masters game format and that this endpoint is not token-gated in practice.
- `lichess/lichess-api-example-README.md` — Lichess guide to auth methods (personal token vs Login with Lichess). Source: https://github.com/lichess-org/api/blob/master/example/README.md. Decides token handling for local vs hosted deployment.
- `lichess/lila-openingexplorer-README.md` — explorer server README: built from database dumps, `/player` query/response docs, AGPL. Source: https://github.com/lichess-org/lila-openingexplorer. Confirms the dumps are the same data as the explorer.
- `lichess/chess-openings-README.md` — ECO dataset README: columns, dist/ generation, naming conventions, CC0. Source: https://github.com/lichess-org/chess-openings. Licence and how names are structured.
- `lichess/chess-openings-a.tsv` — ECO volume A (flank openings), 817 lines `eco\tname\tpgn`. Source: https://raw.githubusercontent.com/lichess-org/chess-openings/master/a.tsv. Opening names for tree nodes.
- `lichess/chess-openings-b.tsv` — ECO volume B (semi-open, Sicilian, Caro-Kann), 772 lines. Source: .../b.tsv. Opening names.
- `lichess/chess-openings-c.tsv` — ECO volume C (open games, French), 1,250 lines. Source: .../c.tsv. Opening names.
- `lichess/chess-openings-d.tsv` — ECO volume D (closed, QGD, Grünfeld), 614 lines. Source: .../d.tsv. Opening names.
- `lichess/chess-openings-e.tsv` — ECO volume E (Indian defences), 357 lines. Source: .../e.tsv. Opening names.
- The Lichess open-database page: CC0, per-month sizes and game counts, PGN format notes (%eval, %clk, Glicko-2 Elo, BOT tags). Source: https://database.lichess.org/. Sizes and licence of the offline route.
- `lichess/dump-2013-01-tree-stats.txt` — our measurement of tree width/depth at popularity cut-offs on the 2013-01 dump (121,332 games), three rating buckets. Source: generated from https://database.lichess.org/standard/lichess_db_standard_rated_2013-01.pgn.zst. Sizes "main opening" trees.
- `lichess/tree-width-analysis.py` — our script for the popularity cut-off vs reply-width trade-off (streams a `.pgn.zst`, builds one move-sequence trie per rating bucket, aggregates top-1..5 reply mass per ply and counts capped leaf paths). Source: written here. Why: reproduces every number in [docs/research/tree-width-measurements.md](../docs/research/tree-width-measurements.md) from the CC0 dump in one command.
- `lichess/berserk-opening_explorer.py` — berserk's explorer client source (method signatures, old .ovh host, `/master/pgn/` path bug). Source: https://github.com/lichess-org/berserk/blob/master/berserk/clients/opening_explorer.py. What the SDK actually does.
- `lichess/berserk-README.md` — berserk README (install, TokenSession usage). Source: https://github.com/lichess-org/berserk/blob/master/README.rst. SDK overview.
- berserk API reference (all clients incl. OpeningExplorer). Source: https://berserk.readthedocs.io/en/master/api.html. Method docs.
- `lichess/berserk-LICENSE.txt` — berserk licence (GPL-3.0-or-later). Source: https://github.com/lichess-org/berserk/blob/master/LICENSE. Stack licence decision.
- The python-chess `chess.pgn` reference (game tree, visitors, exporters). Source: https://python-chess.readthedocs.io/en/latest/pgn.html. How to read/represent lines.
- python-chess `chess.polyglot` reference (`weighted_choice`, Entry, zobrist_hash; no writer). Source: https://python-chess.readthedocs.io/en/latest/polyglot.html. Ready-made popularity sampler.
- `lichess/python-chess-LICENSE.txt` — python-chess licence (GPL-3.0-or-later). Source: https://github.com/niklasf/python-chess/blob/master/LICENSE.txt. Stack licence decision.

## Learning chess openings (ticket 01)

All files live in `refs/learning/`. Findings: `docs/research/learning-openings.md`. Format: file | what it is | source | why it matters, or, for a source cited by its link only: what it is — link — why it matters.

### Chess expertise: chunking, templates, opening knowledge

- Chase & Simon 1973, Cognitive Psychology 4:55-81 — https://andymatuschak.org/prompts/Chase1973.pdf — Origin of chunking; game-vs-random recall (beginner 33% / Class A 49% / master 81%).
- Gobet & Simon 1996, Cognitive Psychology 31:1-40 (preprint) — https://bura.brunel.ac.uk/bitstream/2438/1339/1/Multiple_boards.pdf — Defines templates as "patterns of the chess board found in familiar openings"; positions, not sequences, are the unit of expert memory.
- Gobet & Simon 1998, Memory 6:225-255 — http://www.chrest.info/Fribourg_Cours_Expertise/Articles-www/II%20Donnees%20empiriques/Gobet%20&%20Simon-1998-Memory.pdf — Replication; masters' chunks much larger than 1973 estimate.
- Gobet & Simon 2000, Cognitive Science 24:651-682 — https://bura.brunel.ac.uk/bitstream/2438/811/1/Five%20Seconds%20or%20Sixty%20.pdf — CHREST computational template theory.
- Gobet & Simon 1996, Psychological Research 61:204-208 — https://gwern.net/doc/psychology/chess/1996-gobet-2.pdf — Small skill effect even on random positions.
- Gobet & Simon 1996, Psychonomic Bulletin & Review 3:159-163 — https://bura.brunel.ac.uk/bitstream/2438/1346/1/FullText.pdf — Same point, different method.
- Gobet 1998, Cognition 66:115-152 — https://cognitivearchaeologyblog.wordpress.com/wp-content/uploads/2015/11/1996-gobet.pdf — Compares chunking, template, LT-WM and skilled-memory theories.
- Gobet & Charness 2006, Cambridge Handbook of Expertise ch. 30 (preprint) — https://bura.brunel.ac.uk/bitstream/2438/1475/1/Gobet-Charness-CUP-chess%20expertise.pdf — Survey; 10k-100k pattern estimate; CHREST 300k chunks.
- Gobet 2009 encyclopedia entry "Chess" — http://chrest.info/fg/chapters/Gobet%20--%20Chess%20--%20final.pdf — One-page summary of the field.
- Gobet & Jansen 2006, in Redman (ed.) Chess and Education pp. 81-97 (preprint) — http://chrest.info/fg/preprints/Training_in_chess.PDF — The one paper turning template theory into opening-training prescriptions (small repertoire, repetition, rote + understanding).
- Chassy & Gobet 2011, PLoS ONE 6(11):e26692 — https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0026692&type=printable — Only quantitative study of opening knowledge by rating: book depth 14.3 ply (Class B) to 18.0 ply (Master).
- Bilalic, McLeod & Gobet 2009, Cognitive Science 33:1117-1143 (preprint) — http://bura.brunel.ac.uk/bitstream/2438/2965/1/Bilalic-Specialisation-CogSci-final.pdf — Opening specialisation shifts recall and problem solving by ~1 SD of skill.
- Bilalic, McLeod & Gobet 2008, Cognition 108:652-661 — https://bura.brunel.ac.uk/bitstream/2438/2276/1/Einstellung-Cognition.pdf — Cost of over-trained patterns (Einstellung).
- Gong, Ericsson & Moxley 2015, PLoS ONE 10(3):e0118756 — https://journals.plos.org/plosone/article/file?id=10.1371/journal.pone.0118756&type=printable — Modern chunk-identification replication.
- Campitelli & Gobet, blindfold-chess chapter — https://bura.brunel.ac.uk/bitstream/2438/819/1/Gobet_Campitelli_Minds%20eye.pdf — Visualising move sequences.
- CHREST project page — https://chrest.info/fg/papers/ModelChessMem/Chess%20Memory.html — Model description.
- Gobet's topic bibliography — http://chrest.info/fg/bibliography-by-topic.html — Index to further preprints.

### Deliberate practice in chess

- Ericsson, Krampe & Tesch-Romer 1993, Psychological Review 100:363-406 — https://gwern.net/doc/psychology/1993-ericsson.pdf — The deliberate-practice framework (goal-directed, feedback, repetition).
- Charness et al. 2005, Applied Cognitive Psychology 19:151-165 — http://www.chrest.info/Fribourg_Cours_Expertise/Articles-www/II%20Donnees%20empiriques/CharnessEtal2005ACP.pdf — Serious solitary study is the strongest correlate of rating (r=.65/.47).
- Gobet & Campitelli 2007, Developmental Psychology 43:159-172 (preprint) — https://bura.brunel.ac.uk/bitstream/2438/611/1/Gobet_DevPsyc_Final.pdf — Hours-to-master mean 11,053 h, 8x spread.
- Campitelli & Gobet 2008, Learning and Individual Differences 18:446-458 (preprint) — http://bura.brunel.ac.uk/bitstream/2438/1335/1/The%20role%20of%20practice%20in%20chess.pdf — Books/databases and group practice both predict rating; names opening memorisation as practice.
- Hambrick et al. 2014, Intelligence 45:34-45 — https://gwern.net/doc/psychology/chess/2014-hambrick.pdf — Reanalysis: DP explains 34% of reliable variance in chess.
- Hambrick et al. 2014, Frontiers in Psychology 5:751 — https://www.frontiersin.org/journals/psychology/articles/10.3389/fpsyg.2014.00751/pdf — Reply in the DP debate.
- Macnamara, Hambrick & Oswald 2014, Psychological Science 25:1608-1618 — https://gwern.net/doc/psychology/2014-macnamara.pdf — Meta-analysis: DP explains 26% of variance in games.
- Burgoyne et al. 2016, Intelligence 59:72-83 — https://artscimedia.case.edu/wp-content/uploads/sites/141/2016/12/22143817/Burgoyne-Sala-Gobet-Macnamara-Campitelli-Hambrick-2016.pdf — The "not just practice" side.
- Chessable blog literature review — https://www.chessable.com/blog/cognitive-skill-studies-and-chess/ — Industry summary; cites no chess-specific spacing experiment.

### Spacing, interval schedules, procedural/sequence memory

- Cepeda, Pashler, Vul, Wixted & Rohrer 2006, Psych Bulletin (317 expts) — https://augmentingcognition.com/assets/Cepeda2006.pdf — Optimal gap scales with retention interval; verbal recall only.
- Cepeda et al. 2008, Psych Science — https://www.yorku.ca/ncepeda/publications/CVRWP2008.pdf — Optimal gap as fraction of retention interval (43%->8% as RI grows 7->350 d); +64% recall vs no gap.
- Landauer & Bjork 1978 — https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/Landauer.Bjork_.1978.pdf — Origin of expanding retrieval; keep success probability high.
- Karpicke & Roediger 2007, JEP:LMC — https://learninglab.psych.purdue.edu/downloads/2007/2007_Karpicke_Roediger_JEPLMC.pdf — Expanding beats equal only short-term; delaying the first retrieval is what matters.
- Kang, Lindsey, Mozer & Pashler 2014, PB&R — https://www.cs.colorado.edu/~mozer/Research/Selected%20Publications/reprints/KangLindseyMozerPashler2014.pdf — Expanding = equal at 8 weeks but higher accessibility during training.
- Mozer & Lindsey 2016 chapter (DASH model) — http://rob-lindsey.com/papers/2016/bigdata.pdf — Power law optimal ISI = 0.097 * RI^0.812 days.
- Donovan & Radosevich 1999, J Applied Psychology (63 studies) — https://gwern.net/doc/psychology/spaced-repetition/1999-donovan.pdf — Spacing benefit d=0.46 overall, collapses to ~0.1 for complex tasks.
- Shea & Morgan 1979, JEP:HLM — https://gwern.net/doc/psychology/spaced-repetition/1979-shea.pdf — Random-order practice of motor sequences hurts acquisition, helps retention/transfer.
- Kwon, Kwon & Lee 2015, J Phys Ther Sci — https://europepmc.org/articles/PMC4395711?pdf=render — Positive spacing effect for a motor sequence (small N).
- Gupta & Rickard 2026, Scientific Reports (N=163+186) — https://www.nature.com/articles/s41598-026-52702-5.pdf — Best-powered null: no spacing benefit for motor sequences; caution against generalising verbal results.
- Stafford & Dewar 2014, Psych Science (N=854,064) — https://eprints.whiterose.ac.uk/83582/1/stafford_and_dewar_postprint.pdf — In-the-wild spacing effect in a game, d=0.11.

### Retrieval practice, testing effect, criterion of learning

- Karpicke & Roediger 2008, Science — http://psychnet.wustl.edu/memory/wp-content/uploads/2018/04/Karpicke-Roediger-2008_Sci.pdf — Dropping items from testing after one success: 80% -> 33-36% recall. Basis for the "never zero" weight.
- Kornell & Bjork 2008, Memory — https://web.williams.edu/Psychology/Faculty/Kornell/Publications/Kornell.Bjork.2008b.pdf — Learner-driven dropping is consistently harmful.
- Pyc & Rawson 2009, JML — https://andymatuschak.org/prompts/Pyc2009.pdf — Harder successful retrievals are better; diminishing returns past a few correct recalls.
- Rawson & Dunlosky 2012, Ed Psych Review — https://static.artofmemory.com/files/rawson-dunlosky-2012.pdf — "3 correct recalls, then 3 spaced relearnings" prescription.
- Bjork & Bjork 2011 chapter — https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/EBjork_RBjork_2011.pdf — Framing for spacing/interleaving/testing.

### Error-driven and adaptive scheduling

- Atkinson 1972, JEP — http://rca.ucsd.edu/reprints/Optimizing%20the%20Learning%20of%20a%20Second%20Language%20Vocabulary%20Journal%20of%20Experimental%20Psychology_1972.pdf — Model-based adaptive selection beat random by 108%.
- Lindsey, Shroyer, Pashler & Mozer 2014, Psych Science — https://scottbarrykaufman.com/wp-content/uploads/2014/01/Lindsey-et-al.-2014.pdf — Review the item nearest a recall threshold (T~0.33): +16.5% vs massed, +10% vs generic spaced.
- Metcalfe & Kornell 2005, JML — https://web.williams.edu/Psychology/Faculty/Kornell/Publications/Metcalfe.Kornell.2005.pdf — Why chasing the hardest items is labour in vain.
- Kornell, Hays & Bjork 2009, JEP:LMC — https://web.williams.edu/Psychology/Faculty/Kornell/Publications/Kornell.Hays.Bjork.2009.pdf — Failed retrieval + feedback still helps.
- Metcalfe 2017, Annual Review of Psychology — https://files.eric.ed.gov/fulltext/ED574569.pdf — Errorful learning with corrective feedback beats error avoidance.
- Wong 2023, Ed Psych Review — https://www.sarahshihuiwong.com/_files/ugd/8b1a2f_bac9b3e68f954bcf8bad07d724c63fc4.pdf — Deliberate errors + correction beat errorless study.
- Wilson, Shenhav, Straccia & Cohen 2019, Nature Communications — https://www.nature.com/articles/s41467-019-12552-4.pdf — ~85% training accuracy optimal for gradient-descent learners (theory, different regime).
- Settles & Meeder 2016, ACL — https://aclanthology.org/P16-1174.pdf — Duolingo half-life regression; trainable forgetting model.
- `fsrs-algorithm-wiki.md` | FSRS "The Algorithm" wiki (raw markdown) | https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm | DSR model formulas.
- `fsrs-abc-of-fsrs-wiki.md` | FSRS "ABC of FSRS" wiki | https://github.com/open-spaced-repetition/awesome-fsrs/wiki/ABC-of-FSRS | Retrievability/stability/difficulty and desired retention, plain language.
- `fsrs-srs-benchmark-readme.md` | open-spaced-repetition/srs-benchmark README | https://github.com/open-spaced-repetition/srs-benchmark | FSRS vs HLR, DASH, Ebisu, SM-2 on ~350M Anki reviews.
- Anki FAQ on its SM-2 variant — https://faqs.ankiweb.net/what-spaced-repetition-algorithm — Anki's lapse/ease modifications.
- `ebisu-readme.md` | Ebisu literate README (Fasih) | https://github.com/fasiha/ebisu | Bayesian Beta-on-recall model; natural fit for per-branch pass/fail evidence.

### Interleaving

- Kornell & Bjork 2008, Psych Science — https://bjorklab.psych.ucla.edu/wp-content/uploads/sites/13/2016/07/Kornell_Bjork_2008_PsychScience.pdf — Interleaving helps induction; learners misjudge it.
- Rohrer, Dedrick & Burgess 2014, PB&R — https://gwern.net/doc/psychology/spaced-repetition/2014-rohrer.pdf — Interleaving 72% vs blocked 38% (d=1.05) for choosing which procedure applies.
- Brunmair & Richter 2019, Psych Bulletin meta-analysis — https://www.psychologie.uni-wuerzburg.de/fileadmin/06020400/2019/Brunmair_Richter_in_press__2019_META-ANALYSIS_OF_INTERLEAVED_LEARNING.pdf — g=0.42 overall; benefit depends on similarity of material.

### Existing opening trainers: docs and source

- Chessable help — https://support.chessable.com/en/articles/9043598-how-does-the-spaced-repetition-scheduling-work — The 8-level interval ladder; per-move timers; wrong -> Level 1.
- Chessable help — https://support.chessable.com/en/articles/9043243-what-is-the-schedule-setting — Default / custom / cyclical (Woodpecker) schedules.
- Chessable help — https://support.chessable.com/en/articles/9047490-review-whole-variation-vs-randomized — Whole-line vs due-moves-only review; overstudy.
- Chessable help — https://support.chessable.com/en/articles/9043806-what-are-soft-fail-moves — Engine-margin rule (0.3 eval) for "Try Again" instead of fail.
- Chessable help — https://support.chessable.com/en/articles/9044168-what-are-difficult-moves-and-how-can-they-help-me — Definition of a "difficult move" (leech surfacing).
- Chessable help — https://support.chessable.com/en/articles/9043230-what-is-the-default-review-option — Four review-ordering policies.
- Chessable help — https://support.chessable.com/en/articles/9039667-why-am-i-not-prompted-to-review-variations-from-move-1 — Shows scheduling is per (variation, move), not per position.
- Chessable help — https://support.chessable.com/en/articles/9034645-what-is-the-learn-setting-what-are-priority-lines — New-material ordering from rating-banded game DB.
- Chessable science blog 2021 — https://www.chessable.com/blog/using-spaced-repetition-intelligently/ — Official rationale; reviews before new material; leech handling.
- Listudy blog — https://listudy.org/en/blog/spaced-repetition-for-chess — Each move is a Leitner card; wrong -> reset to 0.
- `listudy-study.js` | Listudy trainer client source | https://raw.githubusercontent.com/ArneVogel/listudy/master/assets/js/study.js | Actual success/fail handling and opponent-move selection.
- `listudy-tree_utils.js` | Listudy source | https://raw.githubusercontent.com/ArneVogel/listudy/master/assets/js/modules/tree_utils.js | `update_node_value` (0-5 box), subtree-size-weighted random choice.
- `chesstempo-manual-ch17-opening-training.txt` | ChessTempo User Guide ch. 17, extracted from the PDF manual | https://chesstempo.com/manual/en/manual.pdf | Most detailed public trainer spec: position-keyed, all SRS parameters, context moves, resistant moves.
- `chessdriller-README.md` | chessdriller README | https://raw.githubusercontent.com/gtim/chessdriller/main/README.md | Open-source SRS trainer on Lichess studies.
- `chessdriller-scheduler.ts` | chessdriller source | https://raw.githubusercontent.com/gtim/chessdriller/main/src/lib/scheduler.ts | Line selection: BFS from FEN to nearest due move.
- `chessdriller-api-study-move-server.js` | chessdriller source | https://raw.githubusercontent.com/gtim/chessdriller/main/src/routes/api/study/move/+server.js | SM-2-style state machine (learning steps, ease, lapses).
- `chessdriller-prisma-schema.prisma` | chessdriller DB schema | https://raw.githubusercontent.com/gtim/chessdriller/main/prisma/schema.prisma | Moves keyed by (fromFen, toFen): position keying.
- `chessdriller-notes.md` | chessdriller dev notes | https://raw.githubusercontent.com/gtim/chessdriller/main/notes.md | FEN canonicalisation (drops ep/clocks).
- `chessdriller-faq-page.svelte` | chessdriller FAQ | https://raw.githubusercontent.com/gtim/chessdriller/main/src/routes/faq/+page.svelte | User-facing statement of intervals.
- `neuralpgn-README.md` | neuralpgn README | https://raw.githubusercontent.com/kfunezc204/neuralpgn/main/README.md | Line-level FSRS trainer; grading and Game Check design.
- `neuralpgn-LineScheduler.ts` | neuralpgn source | https://raw.githubusercontent.com/kfunezc204/neuralpgn/main/src/lib/LineScheduler.ts | Outcome -> FSRS grade mapping (first-try Good, retry Hard, fail Again).
- `tabia-store.js` | tabia source | https://raw.githubusercontent.com/daxaur/tabia/main/src/store.js | Complete Leitner line scheduler in 90 lines; failure = box-1, not reset.
- Chessbook founder's blog — https://mbuffett.com/posts/chessbook-year-review-2024/ — Only primary statement that Chessbook moved to FSRS.
- Chess.com help — https://support.chess.com/en/articles/8724749-what-is-practice-on-chess-com — Chess.com openings practice is bot play, no SRS.
- `lichess-api-opening-explorer-spec.yaml` | Lichess opening-explorer OpenAPI fragments | https://github.com/lichess-org/api/tree/master/doc/specs/tags/openingexplorer | Exact query params and response shape; endpoint is explorer.lichess.org.
- Lichess blog — https://lichess.org/blog/WtDErSQAADJfhJJs/interactive-lessons — Lichess's native "play the line" mode: mainline correct, per-move error messages, no scheduling.
- Lichess Tools extension author's post — https://siderite.dev/blog/how-to-learn-and-test-any-opening-in-hours-with-li — "Explorer Practice": opponent moves sampled from the explorer DB by rating band; no SRS.

### Paywalled or unavailable (citation only)

- Simon & Gilmartin 1973, "A simulation of memory for chess positions", Cognitive Psychology 5:29-46 — https://www.sciencedirect.com/science/article/abs/pii/0010028573900248 (source of the 10k-100k chunk estimate).
- De Groot 1946/1965, Thought and Choice in Chess — https://archive.org/details/thoughtchoiceinc0000groo (lending only).
- Howard 2012, "Longitudinal effects of different types of practice on the development of chess expertise", Applied Cognitive Psychology 26:359-369 — https://onlinelibrary.wiley.com/doi/abs/10.1002/acp.1834
- Southwick et al. 2026, "Not all practice is created equal: longitudinal evidence from over 40,000 chess players", Psychological Science 37(7):514-523 — https://pubmed.ncbi.nlm.nih.gov/42335356/
- Krivec, Bratko & Guid 2021, "Identification and conceptualization of procedural chunks in chess", Cognitive Systems Research 69:22-40 — https://doi.org/10.1016/j.cogsys.2021.05.001
- Roediger & Karpicke 2006, "Test-enhanced learning", Psych Science 17:249-255 — https://pubmed.ncbi.nlm.nih.gov/16507066/
- Rawson & Dunlosky 2011, "Optimizing schedules of retrieval practice for durable and efficient learning: how much is enough?", JEP:General 140:283-302 — https://pubmed.ncbi.nlm.nih.gov/21707204/
- Rohrer & Taylor 2007, "The shuffling of mathematics problems improves learning", Instructional Science 35:481-498 — https://link.springer.com/article/10.1007/s11251-007-9015-8
- Shea, Lai, Black & Park 2000, "Spacing practice sessions across days benefits the learning of motor skills", Human Movement Science 19:737-760 — https://www.sciencedirect.com/science/article/abs/pii/S016794570000021X
- Dail & Christina 2004, RQES 75:148-155 — https://www.tandfonline.com/doi/abs/10.1080/02701367.2004.10609146
- Simmons 2012, "Distributed practice and procedural memory consolidation in musicians' skill learning", JRME 59:357-368 — https://eric.ed.gov/?id=EJ951332
- Latimier, Peyre & Ramus 2021, meta-analytic review of spacing out retrieval practice, Ed Psych Review 33:959-987 — https://eric.ed.gov/?id=EJ1310148
- Wong & Lim 2022, "Deliberate errors promote meaningful learning", J Ed Psych 114:1817-1831 — https://link.springer.com/article/10.1007/s10648-023-09739-z (2023 follow-up downloaded instead).
- Pan & Rickard 2018, "Transfer of test-enhanced learning", Psych Bulletin 144:710-756 — https://sc-pan.github.io/pdf/PR_2018W.pdf (free; not saved).
- Chessable "science" and MoveTrainer marketing pages, ChessTempo HTML manual, Chessbook site — JS shells or bot-blocked; not saved.

## Opening explanations (ticket 14)

Saved 2026-09-12 into `openings-text/`; findings in `docs/research/opening-explanations.md`. Everything under `wikibooks-*` is CC BY-SA 4.0 text from en.wikibooks.org (see the licence files); it is here as evidence, not as app data.

- `openings-text/lila-OpeningWiki.scala`: lila's server-side opening wiki (MongoDB revisions, `Granter.opt(_.OpeningWiki)` editors, markdown render, `popularOpeningsWithShortWiki`). Source: https://raw.githubusercontent.com/lichess-org/lila/master/modules/opening/src/main/OpeningWiki.scala. Why: proves the text on `/opening/<name>` is Lichess's own, not Wikibooks.
- `openings-text/lila-OpeningApi.scala`, `openings-text/lila-OpeningPage.scala`, `openings-text/lila-OpeningQuery.scala`: how an opening page is assembled (`query.closestOpening.traverse(wikiApi.apply)`, `sans`, `pgnUnderscored`). Source: same directory. Why: the page's data model that the client-side Wikibooks fetch reads.
- `openings-text/lila-ui-WikiUi.scala`, `openings-text/lila-ui-OpeningUi.scala`, `openings-text/lila-ui-OpeningBits.scala`: the server-rendered wiki box ("No description of the opening, yet." placeholder that the client fills from Wikibooks, editor form, no licence notice). Source: https://github.com/lichess-org/lila/tree/master/modules/opening/src/main/ui. Why: what is shown and under which wording.
- `openings-text/lila-ui-lib-wikiBooks.ts`: shared client code: `apiArgs` (`redirects&origin=*&action=query&prop=extracts&formatversion=2&format=json&stable=1`) and `transformWikiHtml` (strips H1, Theory table, All possible replies / Black's moves, External links, the contributing line; appends "Read more on WikiBooks"). Source: https://raw.githubusercontent.com/lichess-org/lila/master/ui/lib/src/wikiBooks.ts. Why: the exact fetch and rendering rule.
- `openings-text/lila-ui-opening-wiki.ts`, `openings-text/lila-ui-analyse-wiki.ts`: the title builder (`N._SAN` / `N...SAN`, `[+!#?]` stripped, 30-ply and 234-char caps) used on opening pages and the analysis board. Source: https://raw.githubusercontent.com/lichess-org/lila/master/ui/opening/src/wiki.ts and `ui/analyse/src/wiki.ts`. Why: the move-sequence to page-title mapping.
- `openings-text/lila-commit-083e6152a0-wikibooks-on-opening-pages.diff`, `openings-text/lila-commit-2b826bec21-resolve-wikibooks-redirects.diff`, `openings-text/lila-commit-69bfaa48e5-stable-arg.diff`: the commits that added the Wikibooks fallback to opening pages (2022-12-29), redirect resolution (2021-10-31) and `stable=1` (2024-10-09). Source: https://github.com/lichess-org/lila/commit/<sha>. Why: dates and intent of the mapping.
- `openings-text/lila-routes-opening.txt`: the `/opening` routes from `conf/routes` (HTML pages and `POST /opening/wiki/:key/:moves`; no JSON/API route). Source: https://raw.githubusercontent.com/lichess-org/lila/master/conf/routes. Why: Lichess does not expose the text through its API.
- `openings-text/lila-COPYING.md`: lila's licence (AGPL, code only). Source: https://raw.githubusercontent.com/lichess-org/lila/master/COPYING.md. Why: the in-house descriptions have no stated content licence.
- Two served Lichess opening pages, one with an in-house description, one with the empty placeholder and `"sans":["Nh3"]` page data; CSP `connect-src` lists `wikibooks.org`. Source: https://lichess.org/opening/Sicilian_Defense, https://lichess.org/opening/Amar_Opening. Why: what the learner actually sees.
- `openings-text/wikibooks-api-siteinfo-rightsinfo.json`: en.wikibooks `meta=siteinfo&siprop=rightsinfo|general` (CC BY-SA 4.0, MediaWiki 1.47). Source: https://en.wikibooks.org/w/api.php. Why: the wiki's own licence declaration.
- `openings-text/wikibooks-Copyrights.wikitext`, `openings-text/wikibooks-api-Copyrights.json`: `Wikibooks:Copyrights` (dual CC BY-SA 4.0 / GFDL, reuser obligations, "4.0 or later" share-alike). Source: https://en.wikibooks.org/wiki/Wikibooks:Copyrights. Why: the licence page the ticket asks for.
- `openings-text/wikimedia-Terms_of_Use.wikitext`: WMF Terms of Use (section 7: CC BY-SA 4.0, the three accepted attribution forms, licensing notice, modification marking). Source: https://foundation.wikimedia.org/wiki/Policy:Terms_of_Use. Why: the binding attribution rule.
- `openings-text/cc-by-sa-4.0-legalcode.txt`: CC BY-SA 4.0 legal code. Source: https://creativecommons.org/licenses/by-sa/4.0/legalcode.txt. Why: sections 3(a) attribution and 3(b) ShareAlike.
- CC's compatible-licence list (GPLv3 one-way compatible since 2015-10-08) and analysis; GNU's `#ccbysa` entry. Source: https://creativecommons.org/share-your-work/licensing-considerations/compatible-licenses/, https://wiki.creativecommons.org/wiki/ShareAlike_compatibility:_GPLv3, https://www.gnu.org/licenses/license-list.html. Why: CC BY-SA text inside a GPL-3.0-or-later app.
- `openings-text/wikibooks-Chess_Opening_Theory.wikitext`, `openings-text/wikibooks-api-Chess_Opening_Theory.json`: the book's root page (starting position) in wikitext and parsed HTML. Source: https://en.wikibooks.org/wiki/Chess_Opening_Theory. Why: the book's structure and tone.
- `openings-text/wikibooks-sample-1e4-c5.wikitext`, `openings-text/wikibooks-api-sample-1e4-c5-*.json`: the `1. e4/1...c5` page as wikitext (`{{Chess Position}}` template), `action=parse` HTML and the exact extract Lichess requests (with the `stable` warning); the full served page (footer licence line) is at the source link. Source: https://en.wikibooks.org/wiki/Chess_Opening_Theory/1._e4/1...c5. Why: the sample page in raw and rendered form.
- `openings-text/wikibooks-api-sample-najdorf-extract-plaintext.json`: a ply-10 page as `explaintext` extract. Source: same API. Why: shows the plain-text format and a deep page's length.
- `openings-text/wikibooks-api-transposition-redirects.json`: `redirects=1` resolution of `1. Nf3/1...Nf6/2. d4` and the QGD `...e6/...d5` order. Source: same API. Why: transpositions are handled by redirects only.
- `openings-text/wikibooks-Chess_Opening_Theory--How_to_navigate_this_wikibook.wikitext`, `openings-text/wikibooks-Template-Chess_Position.wikitext`: the book's own statement that one page = one position keyed by move order, redirects for other orders, FEN derived by Lua and searchable. Source: https://en.wikibooks.org/wiki/Chess_Opening_Theory/How_to_navigate_this_wikibook, https://en.wikibooks.org/wiki/Template:Chess_Opening_Theory/Position. Why: pages exist per move order, positions only via redirect/FEN search.
- `openings-text/wikibooks-api-allpages-Chess_Opening_Theory.json`: every page (2,563) and redirect (464) under `Chess Opening Theory/` from `list=allpages`. Source: same API. Why: the offline existence check.
- `openings-text/wikibooks-api-redirect-targets.json`: the 464 redirects resolved to targets. Source: same API, `redirects=1`. Why: which transposition orders land on a page.
- `openings-text/wikibooks-Chess_Opening_Theory-pages.json.gz`: wikitext, size and last-edit timestamp of all 2,563 pages (52 batched requests). Source: same API, `prop=revisions`. Why: prose-length measurement for the whole book; also shows a whole-book pull is ~50 requests.
- `openings-text/wikibooks-api-extracts-sample.json.gz`: Lichess-style whole-page HTML extracts for every matched repertoire page plus 60 sampled TSV pages, one request each. Source: same API, `prop=extracts`. Why: what Lichess would display, to calibrate the local measure.
- `openings-text/coverage-analysis.py`, `openings-text/coverage-stats.txt`, `openings-text/coverage-lines.tsv`, `openings-text/coverage-tree.tsv`: the measurement script, its verbatim report, and per-line / per-node status (page, redirect, missing, prose chars). Why: the coverage numbers in the findings.
- `openings-text/mediawiki-API-Etiquette.wikitext`, `openings-text/mediawiki-Extension-TextExtracts.wikitext`: API etiquette (no hard read limit, serial requests, `maxlag`, User-Agent) and the TextExtracts extension (exlimit 20, one whole-page extract per request, caveats). Source: https://www.mediawiki.org/wiki/API:Etiquette, https://www.mediawiki.org/wiki/Extension:TextExtracts. Why: fetch rules and formats.
- `openings-text/wikimedia-User-Agent_policy.wikitext`, `openings-text/wikitech-Robot_policy.wikitext`, `openings-text/wikibooks-robots.txt`: the User-Agent policy (403 without one), the robot policy (prefer dumps; unauthenticated <5 req/s, concurrency 3), and en.wikibooks robots.txt. Source: https://foundation.wikimedia.org/wiki/Policy:Wikimedia_Foundation_User-Agent_Policy, https://wikitech.wikimedia.org/wiki/Robot_policy, https://en.wikibooks.org/robots.txt. Why: rate limits.
- The en.wikibooks dump listing (`enwikibooks-latest-pages-articles.xml.bz2`, 203 MB, 2026-09-01). Source: https://dumps.wikimedia.org/enwikibooks/latest/. Why: the offline whole-wiki option.
- `openings-text/wikipedia-api-rightsinfo-and-opening-articles.json`: en.wikipedia licence (CC BY-SA 4.0) and sizes of `Sicilian Defence` (80 KB) and `Encyclopaedia of Chess Openings`. Source: https://en.wikipedia.org/w/api.php. Why: the alternative source's licence and shape.
