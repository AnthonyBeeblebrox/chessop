# Open-ended rating bands

Type: grilling
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

ADR 0003 fixes five closed bands (below 1200, 1200–1500, 1500–1800, 1800–2100, 2100+) with both players' ratings inside the band, default 1500–1800. The owner wants open-ended bands selectable and **1500+ as the default**. Decide: which open-ended bands are offered (1200+, 1500+, 1800+, …?) and whether the closed bands stay; what "inside" means for an open band (both players ≥ the bound? the learner's side only?); whether an open band's cap of 150,000 games per band is still a fair sample when 1500+ pools very different strengths; and what the repertoire looks like at 1500+ (positions, depth, main moves that differ from 1500–1800). Amends ADR 0003 and the **Rating band** glossary entry.

## Answer

Resolved by grilling, 2026-09-29. Measurements: `docs/research/open-bands.md` on branch `research/open-bands` (commit 9a9e754), 2026-08 prefix, same method as the shipped build (its 1500-1800 and 1800-2100 graphs are byte-identical to the shipped ones).

- **Band set: eight bands.** The five closed bands stay (below 1200, 1200–1500, 1500–1800, 1800–2100, 2100+) and the open bands **1200+, 1500+, 1800+** are added; 2100+ is both the top closed band and an open one. A game now counts toward every band both players fall in, so one game may feed several bands.
- **"Inside" an open band: both players ≥ the bound.** The learner's side alone is impossible: one game feeds both colours' moves.
- **The learner chooses the band directly** in settings, from a list; the **declared rating is removed**. A rating no longer picks one band (1650 fits 1500–1800, 1500+ and 1200+), and a new visitor is never asked their rating.
- **Default 1500+ in both modes.** Migration: a stored declared rating becomes the closed band it maps to today (so a learner who chose is never moved); a learner with none moves to 1500+, the repertoire regenerates, the learner is told, and position records are untouched (ADR 0003's refresh rule).
- **The natural rating mix is accepted.** 1500+ is 54 % 1500–1799, 37 % 1800–2099, 9 % 2100+ by the lower player's rating; 13 % of its games pair players the closed bands would split. Its top move differs from 1500–1800 and from 1800–2100 at only 3 of the 65 positions reached by ≥ 1 % of games. No strength-stratified sampling.
- **Cap stays 150,000 kept games for every band.** Two 150k samples overlap at J = 0.77 (150k vs 300k at 0.87), but the noise is in low-traffic positions near the popularity floor and is not specific to open bands; changing the cap is a question for all bands, not this one.
- **Cost accepted.** 1500+ repertoire: 2,945 positions, depth 17 (1500–1800: 2,695; 1800–2100: 3,074); snapshot band 5,002 positions, 190 KB. The three open bands need no extra dump reading; build peak about 7.9 → 11 GB, time about 9 → 14 min (estimate), snapshot +588 KB. How many bands a hosted server holds in memory at once is left to "From one learner to many".
- **Vocabulary**: **Rating band** keeps its name, gains *closed band* / *open band* and "both players inside it"; "floor band" avoided (Floor is a memory term). Recorded in `CONTEXT.md` and in an amendment to ADR 0003.
