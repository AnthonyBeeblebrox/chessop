# Exploration bonus: the Gumbel noise swamps popularity, so the no-history opponent is not the database opponent

Type: grilling
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Building v1 reopened a second point. The spec review of build ticket 06 (`.scratch/chessop-v1/issues/06-steering-by-need.md`) found that ADR 0001's opponent rule contradicts itself. It weights each drawable move by `pop(m)^alpha * mean_need(m) + (C / sqrt(1 + faced(m))) * g`, `g` a standard Gumbel draw, and claims that "with no history, this is exactly the database opponent restricted to the repertoire". With no history `mean_need = 1`, so the weight is `pop + C * g`; `pop` is a share in [0, 1] while `g` has mean 0.58 and standard deviation 1.28, so at `C = 1` the noise dominates: a 70/30 split plays about 58/42 and a 5 % sideline about as often as the main move. The test of spec §13 ("with no history the opponent's frequencies match renormalised popularity") passes only at `C = 0`. The prototype used the same formula but never measured its frequencies. Options put to the learner on 2026-09-24:

- **A. The bonus inside the product**: `pop^alpha * (mean_need + C / sqrt(1 + faced))`, drawn proportionally, no noise term.
- **B. Textbook Boltzmann-Gumbel**: `argmax_m [log(pop^alpha * mean_need) + C / sqrt(1 + faced) * g]`; exact with no history, but the noise shrinks with visits so the opponent drifts to always playing the single most-needed move.
- **C. No exploration bonus**: need already favours what is unlearnt; simplest, but nothing favours rarely faced replies.

## Answer

Decided by the learner on 2026-09-24: **A**. Folded into ADR 0001 (ticket 23 amendment), [`spec.md`](../spec.md) §5.3, §5.4, §13, §17, the glossary (Sampling weight) and build ticket 06.

- `weight(m) = pop(m)^alpha * (mean_need(m) + C / sqrt(1 + faced(m)))`, the move drawn with probability proportional to its weight.
- **With no history** every drawable move has `mean_need = 1` and `faced = 0`, so each weight is `pop * (1 + C)` and the draw is exactly renormalised popularity: ADR 0001's claim now holds at any `C`, and the §13 test holds at the default `C = 1`.
- **The bonus still favours rarely faced replies**, in proportion to their popularity, and fades as they are faced (1 at first, 0.5 after three times, 0.1 after 99 at `C = 1`); a move onto a leaf is weighted by popularity times the floor plus that bonus.
- **No noise term and no clamp**: the proportional draw is the randomness, and every weight is at least `pop * floor > 0`. `C = 1` and `faced` (rebuilt from the round log) are unchanged.
