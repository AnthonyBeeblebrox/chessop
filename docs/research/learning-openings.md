# Learning chess openings: what the literature says

Ticket: `.scratch/chessop/issues/01-literature-learning-openings.md`. Downloads indexed in `refs/README.md` under "Learning chess openings (ticket 01)"; file names below refer to `refs/learning/`.

## Summary

1. Chess expertise is recognition of stored positions ("chunks", later "templates"), and templates are explicitly tied to opening systems; experts store opening knowledge as positions with attached plans, not as move strings (Chase & Simon 1973; Gobet & Simon 1996).
2. Opening knowledge is large and rating-graded: average departure from book rises from 14.3 ply (Class B) to 18.0 ply (Master); masters may hold tens of thousands of opening moves (Chassy & Gobet 2011).
3. Deliberate practice, especially serious solitary study, is the best single predictor of rating (r ~ .5-.65) but explains only ~25-35% of variance; no study isolates opening drilling as a predictor.
4. No peer-reviewed experiment tests spaced repetition on chess openings. All schedule evidence is imported from verbal-memory work.
5. In that work the spacing effect is robust (d ~ 1 at long retention), the optimal gap is ~10-40% of the retention interval, and expanding vs uniform schedules barely differ at long delay.
6. For procedural/motor sequence learning the spacing evidence is mixed and the best-powered study finds no benefit, so verbal numbers should not be hard-coded for move sequences.
7. The strongest single finding for this design: dropping an item from testing after one success cuts a week later recall from ~80% to ~33% (Karpicke & Roediger 2008). "Never zero" is correct.
8. Adaptive selection beats random (Atkinson 1972: +108%), but the winning policies target items near a recall threshold, not the most-failed ones; pure failure-chasing is "labour in vain" (Metcalfe & Kornell 2005) and starves maintenance.
9. Random sampling across lines is interleaving, which the sequence-learning literature supports (Shea & Morgan 1979), most strongly for confusable lines.
10. Existing trainers split on unit (move vs line) and keying (variation vs position); nearly all refuse to count a post-reveal replay as a success, and ChessTempo and chessdriller key by position so transpositions share one record.

## 1. Chunking, templates and what "knowing an opening" is

- De Groot found that masters and weaker players differ little in search statistics; the dramatic difference is 5-second recall of game positions (masters replace ~23-24 of 25 pieces). Chase & Simon 1973 quantified it: beginner 33%, Class A 49%, master 81% recall of master-game positions, and no skill effect on random positions (`chase-simon-1973-perception-in-chess.pdf`).
- The chunking estimate (~50,000 patterns, range 10k-100k) comes from Simon & Gilmartin's MAPP simulation, restated in Gobet & Simon 1996; CHREST simulations later put grandmaster-level recall at ~300,000 chunks (`gobet-charness-2006-expertise-in-chess-cambridge-handbook.pdf`).
- Template theory (Gobet & Simon 1996, `gobet-simon-1996-templates-in-chess-memory.pdf`) defines templates as "patterns of the chess board found in familiar openings and lines of play" with slots for "the opening such a position is likely to come from, the potential plans and moves in the position" and links to "a possible type of position after 10 additional moves". Recognition "is more likely to happen when the opening leading to the stimulus position belongs to the subject's repertoire" (footnote 5). Slots fill in 1-2 s; building a template takes years.
- The specialisation effect is the experimental test: French vs Sicilian specialists matched on rating recalled in-speciality positions and solved in-speciality problems at the level of players ~1 SD above them in general skill, and out-of-speciality ~1 SD below (Bilalic, McLeod & Gobet 2009, `bilalic-mcleod-gobet-2009-specialization-effect.pdf`, interaction eta-p2 = .23).
- Openings are the paradigm case of what Chassy & Gobet 2011 call "monochrestic" (single-use, rote) knowledge, versus polychrestic chunks that transfer across positions (`chassy-gobet-2011-single-use-sequence-knowledge-openings-plos-one.pdf`). Gobet & Jansen 2006 add that template theory implies two "sad" facts about rote material: "learning is time consuming and forgetting will inevitably occur" (`gobet-jansen-2006-training-in-chess-scientific-approach.pdf`).
- Sequence vs position: Chase & Simon's recognition-without-recall result and the template slots imply experts retrieve positions (transposition-tolerant), not serial chains. No experiment directly tests transposition awareness or sequence-vs-position retrieval of openings; the only serial-order study (Krivec, Bratko & Guid 2021, paywalled) reports procedural chunks tagged with conditions. This area is thin.
- Cost side: strongly trained patterns can block better moves (Einstellung; `bilalic-mcleod-gobet-2008-einstellung-cognition.pdf`).

## 2. Deliberate practice in chess

- Ericsson, Krampe & Tesch-Romer 1993 define deliberate practice as effortful, goal-directed, feedback-rich activity designed to improve performance, distinct from play (`ericsson-krampe-tesch-romer-1993-role-of-deliberate-practice.pdf`).
- Charness et al. 2005 (n=200 and 164): log cumulative serious study alone correlated r=.65 / .47 with rating; tournament play r=.31 / .14; adding play to study did not raise R^2, adding study to play did. Grandmasters logged ~5,000 h of serious study in their first decade. The questionnaire did not separate opening study, so there is no direct correlation for openings (`charness-etal-2005-deliberate-practice-chess-expertise.pdf`).
- Gobet & Campitelli 2007: mean practice to reach 2200 was 11,053 h (SD 5,538), range 3,016-23,608; some players with >25,000 h never made master (`gobet-campitelli-2007-domain-specific-practice-handedness-starting-age.pdf`). Campitelli & Gobet 2008: individual practice r=.42, group practice r=.54; books and databases predict rating; they list memorising opening variations as normal individual practice (`campitelli-gobet-2008-role-of-practice-in-chess-longitudinal.pdf`).
- Contested: Howard 2012 (paywalled) found games, not study hours, predicted growth; Hambrick et al. 2014 reanalysis puts deliberate practice at 34% of reliable variance across six chess studies (range 15-66%); Macnamara et al. 2014 meta-analysis gives 26% for games (`hambrick-etal-2014-deliberate-practice-is-that-all-it-takes.pdf`, `macnamara-hambrick-oswald-2014-deliberate-practice-meta-analysis.pdf`).
- Southwick et al. 2026 (Chess.com logs, N=44,213, paywalled): structured activities (puzzles, lessons, game review) were 3.61x as efficient per unit time as playing for rating gain, but "not all deliberate practice-aligned activities were equally effective"; whether opening drills were a category is unknown.
- Gobet & Jansen 2006 turn template theory into training prescriptions: keep a small repertoire and expand later (raises the chance that trained templates recur in games), balance rote learning and understanding, repeat from varied viewpoints, link openings to typical middlegames to "speed up the creation of templates", keep a central reviewable repertoire file because "memory is fallible".

## 3. Spaced repetition and interval schedules

### 3a. Verbal / declarative evidence (strong)

- Cepeda et al. 2006 meta-analysis (317 experiments): optimal inter-study interval grows with retention interval; expanding beats fixed only tentatively (`cepeda-2006-spacing-metaanalysis.pdf`).
- Cepeda et al. 2008 (N>1,350, gaps to 105 d, retention to 350 d): the optimal gap vs a zero gap gave +64% recall (d=1.1). Optimal gaps for retention intervals of 7/35/70/350 days were ~3/8/12/27 days, i.e. 43%/23%/17%/8% of the retention interval (`cepeda-2008-temporal-ridgeline.pdf`). Mozer & Lindsey 2016 fit optimal ISI = 0.097 * RI^0.812 days (`mozer-lindsey-2016-dash-big-data.pdf`).
- Expanding vs uniform: Landauer & Bjork 1978 favoured expanding because it "keeps the probability of a successful test relatively high"; Karpicke & Roediger 2007 found equal beat expanding at 2 days (45% vs 33%) and that delaying the first retrieval is the active ingredient; Kang et al. 2014 found equivalence at 8 weeks but higher accessibility during training for expanding; Latimier et al. 2021 meta-analysis: spaced vs massed retrieval g=0.74, expanding vs uniform g=0.03 n.s. (`landauer-bjork-1978-optimum-rehearsal-patterns.pdf`, `karpicke-roediger-2007-expanding-vs-equal-spaced-retrieval.pdf`, `kang-2014-expanding-vs-equal-interval.pdf`).
- Retrieval beats restudy: Karpicke & Roediger 2008 (Swahili pairs, 1-week test) — keep testing after first success: ~80%; drop after first success: 36% and 33%; extra restudy added nothing (`karpicke-roediger-2008-science-retrieval.pdf`). Kornell & Bjork 2008: learner-driven dropping of flashcards is consistently harmful (`kornell-bjork-2008-dropping-flashcards.pdf`).
- Criterion: Rawson & Dunlosky 2011/2012 — learn to 3 correct recalls, then relearn ~3 times at wide spacing; returns per extra correct recall diminish (Pyc & Rawson 2009) (`rawson-dunlosky-2012-when-is-practice-testing-most-effective.pdf`, `pyc-rawson-2009-retrieval-effort-hypothesis.pdf`).

### 3b. Procedural / motor / sequence evidence (weak and mixed)

- Donovan & Radosevich 1999 (63 studies): spaced > massed d=0.46 overall, but d=0.97 for simple psychomotor tasks and ~0.1 (n.s.) for complex tasks; much of it is within-session rest, not day-scale spacing (`donovan-radosevich-1999-distribution-of-practice-meta.pdf`).
- Small positive results: Kwon et al. 2015 (serial reaction-time task, N~30), Shea et al. 2000, Dail & Christina 2004 (golf), Simmons 2012 (piano; gains only with a 24 h gap, i.e. consolidation), Stafford & Dewar 2014 (game, N=854,064, d=0.11) (`kwon-2015-distributed-vs-massed-motor-sequence.pdf`, `stafford-dewar-2014-skill-learning-online-game.pdf`).
- Best-powered null: Gupta & Rickard 2026 (finger-tapping sequences, N=163 and 186, practice equated): spaced groups faster at end of training but equivalent after rest (BF01 ~ 2.5-2.8, d ~ 0.15); "spacing mechanisms identified in declarative memory do not generalize to motor sequence learning" (`gupta-rickard-2026-spacing-no-effect-motor-sequence.pdf`).
- Interleaving does extend to sequences: Shea & Morgan 1979 random-order practice of arm-movement sequences was slower to acquire but better at 10-day retention and transfer (`shea-morgan-1979-contextual-interference.pdf`).
- No study of day-scale spacing for serial recall of symbolic sequences, and none for chess lines, was found. Opening recall (cue = position, response = move) is plausibly closer to fact memory than to finger tapping, which favours applying section 3a, but this is an inference.

### 3c. Practical algorithms

- Anki SM-2: starting ease 2.5, ease floor 1.3, lapse resets interval; learning-stage failures decoupled from ease to avoid "low interval hell" (`anki-faq-sm2-algorithm.html`).
- FSRS: retrievability R(t,S) = (1 + factor * t/S)^(-w) with R(S,S)=0.9; difficulty in [1,10] with mean reversion; stability gain shrinks as D and S grow; desired retention default 0.90 (allowed 0.70-0.99), and going 0.85 -> 0.90 costs ~35% more reviews (`fsrs-algorithm-wiki.md`, `fsrs-abc-of-fsrs-wiki.md`). Benchmark on ~350M Anki reviews: FSRS-7 log-loss 0.340 / AUC 0.717 vs DASH 0.368 / 0.631, HLR and Ebisu lower (`fsrs-srs-benchmark-readme.md`).
- Duolingo half-life regression p = 2^(-delta/h), h = 2^(theta . x): 45% lower prediction error, +12% daily engagement (`settles-meeder-2016-half-life-regression.pdf`). Ebisu: Beta prior on recall probability with exponential decay and an exact Bayesian update on pass/fail (`ebisu-readme.md`).

## 4. Error-driven sampling: the case for and against

For:
- Atkinson 1972 (84 German words, 1-week test): random order baseline; learner choice +53%; Markov-model adaptive scheduler +108%. The adaptive condition deliberately produced high error rates during instruction (`atkinson-1972-optimizing-vocabulary-learning.pdf`).
- Lindsey et al. 2014 (semester Spanish course): personalised review +16.5% over massed and +10.0% over generic spaced on a delayed exam. The policy reviews the item whose predicted recall is closest to a threshold T ~ 0.33 (`lindsey-2014-personalized-review.pdf`).
- Errors with feedback help: unsuccessful retrieval followed by feedback beats study (Kornell, Hays & Bjork 2009); errorful learning with corrective feedback beats error avoidance, and high-confidence errors are hypercorrected (Metcalfe 2017); deliberately erring then correcting beats errorless elaboration, d ~ 0.5 (Wong 2023) (`kornell-hays-bjork-2009-unsuccessful-retrieval.pdf`, `metcalfe-2017-learning-from-errors.pdf`, `wong-2023-deliberate-erring-far-transfer.pdf`).
- Wilson et al. 2019 derive ~85% training accuracy (15.87% error) as optimal for gradient-descent-like learners; theoretical, about category learning, suggestive only (`wilson-2019-eighty-five-percent-rule.pdf`).

Against (or rather, against pure failure-chasing):
- Removing successes from testing is the costliest policy found (Karpicke & Roediger 2008; Kornell & Bjork 2008). A sampler that drives known branches to zero would reproduce it.
- Metcalfe & Kornell 2005 "region of proximal learning": efficient learners study the easiest unlearned items first and abandon items that are not yielding; chasing the hardest items is "labour in vain" (`metcalfe-kornell-2005-region-proximal-learning.pdf`).
- Landauer & Bjork 1978 and Kang et al. 2014 both argue for schedules that keep success probability high; FSRS's 0.9 default embodies the same. Atkinson's high-error regime was a 1-week vocabulary test, not months of sustained motivation.
- The winning adaptive policies (Atkinson, Lindsey/DASH, FSRS) weight by predicted retrievability, not raw failure count. Failure count is one input to that estimate; time since last visit is the other.

## 5. How existing trainers score a success

| Trainer | Unit scheduled | Success criterion | Schedule | On error | Transpositions |
|---|---|---|---|---|---|
| Chessable MoveTrainer | Own move within a specific variation | Exact move; engine-equivalent alternatives within 0.3 eval = "Try Again" (soft fail), not a fail | Fixed 8-level ladder: 4h, 1d, 3d, 1w, 2w, 1m, 3m, 6m; custom or cyclical (Woodpecker) optional | That move to Level 1; other moves in the line untouched; overstudy wrong also resets | None: same move in another variation is a separate item |
| Listudy | Move node in PGN tree, Leitner value 0-5 | Any repertoire child move; retry in place; arrows shown when value < 2 | Leitner boxes with no time component; values drive hints/progress, not order | All candidate replies at that node reset to 0 | None (per-chapter tree) |
| ChessTempo | Own move at a position | Exact enabled move; replaying the revealed move after a miss "will not be considered a correct response"; previewed moves rescheduled at 1 min | Multiplicative: initial 1 day, x2.0 growth, cap 1095 d, all user-editable; mistake rescheduled at 0.5 min | Surfaces again after the current due set; "resistant" moves need several correct-in-a-row | Full: "positions as the primary entity", one record across move orders and repertoires |
| Lichess interactive lesson | none | Mainline move; per-move error messages; hint | none | Retry | none |
| Lichess Tools Explorer Practice | none | none (engine eval at end) | none | n/a | Explorer is FEN-keyed |
| Chess.com Practice > Openings | none | none documented | none (bot play) | n/a | n/a |
| Chessbook | unverified | unverified | FSRS since 2024 (was custom "supermemo-ish") | unverified | Claims transposition handling (unverified) |
| chessdriller | Own move at a position | Exact move or any sibling own move; first attempt is recorded; retry in place; show-answer after 2 wrongs | Anki-like SM-2: steps 10m/1h/8h then 1d, x ease (2.5, floor 1.3), cap 100 d, fuzz | > 1 d interval -> back to 1 d, else -> 10 min; ease -0.2 | Full: unique on (fromFen, toFen), FEN minus ep/clocks |
| neuralpgn | Whole line (FSRS card) | One retry per step; second miss = fail; any retry or hint caps grade at Hard | FSRS via ts-fsrs | Line -> Again; misses also feed a position-keyed "weak points" deck | Lines are sequences; weak points and game check are FEN-keyed |
| tabia | Whole line (Leitner box 0-6) | First-try only: any mistake fails the line; hints don't count | Fixed [0,1,3,7,16,35,90] days | box - 1 (not reset) | None |

Sources: `chessable-help-*.html`, `listudy-study.js`, `listudy-tree_utils.js`, `chesstempo-manual-ch17-opening-training.txt` (sections 17.4, 17.11, 17.15), `chessdriller-api-study-move-server.js`, `chessdriller-scheduler.ts`, `chessdriller-prisma-schema.prisma`, `neuralpgn-LineScheduler.ts`, `tabia-store.js`, `lichess-blog-interactive-lessons.html`, `lichess-tools-siderite-learn-opening-blog.html`, `chesscom-help-practice.html`, `chessbook-mbuffett-year-review-2024.html`.

Patterns worth noting:
- Per-move schedulers (Chessable, ChessTempo, chessdriller) all need a second policy for "which line do I play to reach the due moves": Chessable whole-variation vs randomized, ChessTempo context moves auto-played at a speed proportional to how well known plus a skip threshold, chessdriller BFS to the nearest due move then padding with non-due moves so the user plays a full line.
- Per-line schedulers (neuralpgn, tabia) are simpler and match this project's "branch" unit, at the cost of re-testing the well-known prefix on every visit; neuralpgn compensates with a position-keyed weak-point deck.
- Every trainer that persists state refuses to count a post-reveal replay as success; they differ on retries (ChessTempo/tabia: first try only; chessdriller: first attempt recorded but retry allowed; neuralpgn: retry demotes to Hard; Chessable: engine-equivalent moves are neither pass nor fail).
- Chessable's "Learn" mode replays a move immediately after showing it (default 3 reps), justified as implicit learning; ChessTempo previews first-seen moves with an arrow and reschedules them at 1 minute because a preview "has basically given you the correct solution".
- Lichess Tools "Explorer Practice" is the closest existing thing to this project's play loop (opponent replies sampled from the explorer database by rating band and speed) but has no memory of the learner at all.

## Implications for the trainer

Confidence tags: [strong] = replicated experimental evidence, [moderate] = single study or theory with indirect data, [thin] = extrapolation.

1. Keep the "never zero" floor and do not treat one success as learned. [strong] Dropping items after one success is the most damaging policy in the literature (80% -> 33%). Count a branch as "known" only after ~3 successes across separate sessions, and keep sampling known branches at a maintenance rate.
2. Weight by predicted retrievability, not raw failure count. [moderate] The policies that beat random (Atkinson, Lindsey/DASH, FSRS) target items near a recall threshold and include time since last visit. A branch's weight should decay with success but grow back with elapsed time; an Ebisu-style Beta-on-recall or an FSRS-style stability model maps directly onto per-branch pass/fail evidence. Ticket 04 should pick the model; the literature does not favour a specific formula for chess.
3. Aim for a high but not saturated in-session success rate, roughly 80-90%. [moderate] Landauer & Bjork, Kang 2014 and FSRS's 0.9 default all point there; the 85% rule is a theoretical result from a different regime. A sampler that drives the learner to 50% success is the Atkinson regime, effective in a one-week study but untested for months of motivation. Log the realised rate and make the target tunable.
4. Do not hard-code verbal spacing intervals for move sequences. [thin] The day-scale spacing effect is robust for facts and mixed-to-absent for motor sequences; opening recall is probably fact-like (cue = position, response = move) but nobody has tested it. Fit the forgetting curve from the app's own success-by-gap data rather than importing Chessable's ladder or Cepeda's percentages as settled.
5. Random sampling across branches is interleaving and is supported for sequence tasks. [moderate] It pays most for confusable branches (similar positions, different correct moves), so sample transpositions and sibling lines together; for a brand-new branch a short blocked burst before it enters the random pool is consistent with the acquisition-phase pattern.
6. Always end a failed round with the correct continuation shown and, ideally, replayed once. [strong] The benefit of errorful retrieval depends on immediate corrective feedback; a failure without feedback is the one condition the error-learning literature does not support. Chessable's replay-after-reveal and ChessTempo's "revealed move does not count" are both consistent with this.
7. Define success at the branch level as first-try, whole-branch. [moderate, practitioner consensus] Every persisted trainer refuses to credit a post-reveal replay; a retry, hint or engine-equivalent alternative is a partial outcome (neuralpgn's Hard, Chessable's soft fail) and should not count as full success. Whether to accept engine-equivalent alternatives is a product choice; the memory literature is silent on it.
8. Key branches by position, or at least merge on transposition, if the data source allows it. [moderate, theory] Template theory says experts store openings as positions with attached plans, and the Lichess explorer is FEN-keyed anyway. ChessTempo and chessdriller show position keying is practical. The sampling weight of a position reached by two move orders should be one number.
9. Start with a deliberately narrow repertoire and expand. [moderate] Gobet & Jansen's strongest prescription, backed by the ~1 SD specialisation effect. Depth can be rating-calibrated: book depth at departure runs 14-18 ply from Class B to Master, so drilling to target-rating depth plus a few plies is more defensible than uniformly deep lines.
10. Measure the app's own effectiveness. [thin but cheap] Since no chess-specific spacing study exists, the trainer should record per-branch success against gap and session count so the schedule can be fitted (FSRS/HLR style) and the "Evaluation of the learning method" item in the map has data to work with.

## Sources

All downloaded files are listed with source URLs in `refs/README.md` ("Learning chess openings (ticket 01)"). Key primary sources cited above:

- Chase & Simon 1973, Perception in chess, Cognitive Psychology 4:55-81. https://andymatuschak.org/prompts/Chase1973.pdf
- Gobet & Simon 1996, Templates in chess memory, Cognitive Psychology 31:1-40. https://bura.brunel.ac.uk/bitstream/2438/1339/1/Multiple_boards.pdf
- Gobet & Simon 1998, Expert chess memory: revisiting the chunking hypothesis, Memory 6:225-255.
- Gobet & Simon 2000, Five seconds or sixty?, Cognitive Science 24:651-682.
- Bilalic, McLeod & Gobet 2009, Specialization effect and its influence on memory and problem solving in expert chess players, Cognitive Science 33:1117-1143.
- Chassy & Gobet 2011, Measuring chess experts' single-use sequence knowledge, PLoS ONE 6(11):e26692. https://doi.org/10.1371/journal.pone.0026692
- Gobet & Jansen 2006, Training in chess: a scientific approach, in Redman (ed.) Chess and Education. http://chrest.info/fg/preprints/Training_in_chess.PDF
- Ericsson, Krampe & Tesch-Romer 1993, The role of deliberate practice, Psychological Review 100:363-406.
- Charness et al. 2005, The role of deliberate practice in chess expertise, Applied Cognitive Psychology 19:151-165.
- Gobet & Campitelli 2007, Developmental Psychology 43:159-172; Campitelli & Gobet 2008, Learning and Individual Differences 18:446-458.
- Hambrick et al. 2014, Intelligence 45:34-45; Macnamara, Hambrick & Oswald 2014, Psychological Science 25:1608-1618.
- Howard 2012, Applied Cognitive Psychology 26:359-369 (paywalled). Southwick et al. 2026, Psychological Science 37(7):514-523 (paywalled). https://pubmed.ncbi.nlm.nih.gov/42335356/
- Cepeda et al. 2006, Psychological Bulletin 132:354-380; Cepeda et al. 2008, Psychological Science 19:1095-1102. https://www.yorku.ca/ncepeda/publications/CVRWP2008.pdf
- Landauer & Bjork 1978; Karpicke & Roediger 2007, JEP:LMC 33:704-719; Kang et al. 2014, PB&R 21:1544-1550; Latimier, Peyre & Ramus 2021, Ed Psych Review 33:959-987 (paywalled).
- Karpicke & Roediger 2008, Science 319:966-968; Kornell & Bjork 2008, Memory 16:125-136; Pyc & Rawson 2009, JML 60:437-447; Rawson & Dunlosky 2011, JEP:General 140:283-302 (paywalled) and 2012, Ed Psych Review 24:419-435.
- Donovan & Radosevich 1999, J Applied Psychology 84:795-805; Shea & Morgan 1979, JEP:HLM 5:179-187; Kwon, Kwon & Lee 2015, J Phys Ther Sci 27:769-772; Gupta & Rickard 2026, Scientific Reports. https://www.nature.com/articles/s41598-026-52702-5 ; Stafford & Dewar 2014, Psychological Science 25:511-518.
- Atkinson 1972, JEP 96:124-129; Lindsey, Shroyer, Pashler & Mozer 2014, Psychological Science 25:639-647; Metcalfe & Kornell 2005, JML 52:463-477; Kornell, Hays & Bjork 2009, JEP:LMC 35:989-998; Metcalfe 2017, Annual Review of Psychology 68:465-489; Wong 2023, Ed Psych Review; Wilson et al. 2019, Nature Communications 10:4646.
- Settles & Meeder 2016, ACL. https://aclanthology.org/P16-1174.pdf ; Mozer & Lindsey 2016 (DASH). http://rob-lindsey.com/papers/2016/bigdata.pdf ; FSRS wiki https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm ; srs-benchmark https://github.com/open-spaced-repetition/srs-benchmark ; Anki FAQ https://faqs.ankiweb.net/what-spaced-repetition-algorithm ; Ebisu https://github.com/fasiha/ebisu
- Kornell & Bjork 2008, Psychological Science 19:585-592; Rohrer, Dedrick & Burgess 2014, PB&R 21:1323-1330; Brunmair & Richter 2019, Psychological Bulletin 145:1029-1052.
- Chessable help centre: https://support.chessable.com/en/articles/9043598 , 9043243, 9047490, 9043806, 9044168, 9043230, 9039667, 9034645; blog https://www.chessable.com/blog/using-spaced-repetition-intelligently/
- Listudy: https://listudy.org/en/blog/spaced-repetition-for-chess ; https://github.com/ArneVogel/listudy
- ChessTempo User Guide ch. 17: https://chesstempo.com/manual/en/manual.pdf
- chessdriller: https://github.com/gtim/chessdriller ; neuralpgn: https://github.com/kfunezc204/neuralpgn ; tabia: https://github.com/daxaur/tabia ; Chessbook: https://mbuffett.com/posts/chessbook-year-review-2024/
- Lichess: https://lichess.org/blog/WtDErSQAADJfhJJs/interactive-lessons ; explorer API https://github.com/lichess-org/api/tree/master/doc/specs/tags/openingexplorer ; Lichess Tools https://siderite.dev/blog/how-to-learn-and-test-any-opening-in-hours-with-li ; Chess.com https://support.chess.com/en/articles/8724749-what-is-practice-on-chess-com
