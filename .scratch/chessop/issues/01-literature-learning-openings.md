# Literature: how do people learn chess openings, and what does the evidence say works?

Type: research
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

What does the research and practitioner literature say about learning chess openings: spaced repetition applied to move sequences, chunking and pattern recognition (Chase & Simon, Gobet), deliberate practice, and the design of existing opening trainers (Chessable MoveTrainer, Listudy, Chess Tempo, ChessBase/Lichess studies, open-source repos)? Download the primary material (papers, PDFs, docs pages) into `refs/` with a `refs/README.md` index, and write findings with citations to `docs/research/learning-openings.md`. Surface specifically: evidence on interval schedules for procedural/sequence memory, the case for and against error-driven sampling, and how trainers score a 'success' on a line.

AFK. Fired at charting time.

## Answer

- Experts store openings as recognisable positions ("templates") with attached plans, not as move strings; templates are explicitly tied to opening systems, and opening specialisation shifts recall/problem solving by ~1 SD of skill (Gobet & Simon 1996; Bilalic et al. 2009). Book depth at departure runs 14 ply (Class B) to 18 ply (Master) (Chassy & Gobet 2011).
- Serious solitary study is the best predictor of rating (r ~ .5-.65) but explains only ~25-35% of variance; no study isolates opening drilling.
- No peer-reviewed experiment tests spaced repetition on chess openings; all schedule evidence is imported from verbal memory, where spacing is robust (d ~ 1) and the optimal gap is ~10-40% of the retention interval, but for motor/sequence learning the spacing effect is mixed and the best-powered study finds none. Don't hard-code intervals; fit them from the app's own data.
- Strongest design finding: dropping an item after one success cuts week-later recall from ~80% to ~33% (Karpicke & Roediger 2008). The "never zero" floor is right; count a branch known only after ~3 spaced successes.
- Adaptive selection beats random (Atkinson 1972 +108%; Lindsey 2014 +10-16%), but winning policies target items near a recall threshold using failures AND elapsed time; pure failure-chasing is labour in vain and starves maintenance. Aim for ~80-90% in-session success.
- Random sampling across branches is interleaving, supported for sequence tasks and most useful for confusable lines.
- Every persisted trainer refuses to credit a post-reveal replay; success = first-try whole branch, with retries/hints/engine-equivalent moves as partial outcomes. ChessTempo and chessdriller key by position so transpositions share one record; Chessable keys by (variation, move); neuralpgn/tabia schedule whole lines.
- Always show and replay the correct continuation after a failure; feedback is what makes errors useful.

Findings: [docs/research/learning-openings.md](../../../docs/research/learning-openings.md). Downloads: `refs/learning/`, indexed in `refs/README.md`.
