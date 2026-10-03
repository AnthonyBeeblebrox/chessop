# Sampling and scheduling algorithms for opening-branch drilling

Ticket: [04-sampling-scheduling-algorithms](../../.scratch/chessop/issues/04-sampling-scheduling-algorithms.md).
Downloaded sources are indexed in [`refs/README.md`](../../refs/README.md) under "Sampling and scheduling algorithms (ticket 04)"; local copies live in `refs/algorithms/`.

Notation used throughout: a **branch** is a root-to-leaf path in the repertoire tree; a leaf `ℓ` carries the learner's history `(s_ℓ, f_ℓ, t_ℓ)` = successes, failures, time of last visit. `Δ` is time since last visit. `n(v, m)` is the Lichess explorer game count for move `m` at position `v` (white + draws + black), `N(v) = Σ_m n(v, m)`.

## Summary

- Every spaced-repetition family reviewed keeps, per item, a *strength* that grows with successes and collapses with failures, then turns strength plus elapsed time into a recall probability `R`. The trainer's "sampling weight" is just `1 − R` (the need to review) plus a floor.
- Leitner and half-life regression (HLR) give the simplest closed form: half-life `h = h0 · 2^(s − f)`, `R = 2^(−Δ/h)`. Success halves the need geometrically; a failure doubles it back. Duolingo clips `h` to `[15 min, 9 months]` so nothing ever reaches 0 or 1.
- SM-2 and Anki multiply intervals by an ease factor floored at 1.3 and reset the interval (not the ease) on failure. FSRS models stability `S` and difficulty `D` with a power-law forgetting curve `R = (1 + F·t/S)^(−decay)`; post-lapse stability is a separate formula, `D ∈ [1,10]`, `S ≥ 0.001`.
- ACT-R replaces the single strength with a sum of power-decaying traces, `m = ln Σ t_i^(−d)`, `R = 1/(1 + e^((τ − m)/s))`: frequency and recency enter through one formula, and Anderson & Schooler show real-world "need odds" follow the same power laws.
- Softmax/Boltzmann turns any score into probabilities that are never zero; ε-greedy gives a hard floor `ε/K`; UCB and Boltzmann-Gumbel add an uncertainty bonus that is a clean way to say "rarely visited branches deserve extra weight".
- Over a tree, weights compose by subtree sums: sampling the opponent's move with probability `W(child)/W(node)` at every opponent node draws each leaf with probability exactly `w_ℓ / W(root)`, and a visit updates only the `O(depth)` ancestors. Per-node alias tables (Vose 1991) give `O(1)` draws if branching is large.
- Recommended default (hedged, to be settled in ticket 06): leaf weight `w_ℓ = pop_ℓ · (ε + 1 − R_ℓ)` with Leitner/HLR `R_ℓ`, subtree-sum composition, `ε ≈ 0.05–0.1`.

## Leitner box system

Leitner (1972) is the classic box scheme: boxes correspond to review intervals 1, 2, 4, 8, 16 days; a card that is recalled moves up a box, a card that is missed moves down [Settles & Meeder 2016, §3.2 and Fig. 3]. Two primary formalisations are useful:

**As a half-life model.** Settles & Meeder show the Leitner variant in their Fig. 3 is HLR (below) with fixed weights `Θ = {x⊕: 1, x⊖: −1}`, "where x⊕ is the number of past correct responses (i.e., doubling the interval), and x⊖ is the number of incorrect responses (i.e., halving the interval)" [Settles & Meeder 2016, Appendix A.2]. So

```
h_Leitner = 2^(s − f)          (in days; Duolingo code: h = hclip(2 ** (right − wrong)))
R(Δ)      = 2^(−Δ / h_Leitner)
```

with `hclip` bounding `h` to `[15 min, 9 months]` (`MIN_HALF_LIFE = 15/(24·60)`, `MAX_HALF_LIFE = 274`) [duolingo-hlr-experiment.py, lines 20–21, 61–67, 180–182]. Pimsleur's fixed schedule is the same form with `Θ = {x_n: 2.4, bias: −16.5}` (`h = 2^(2.35·n − 16.46)` in code), i.e. it grows with total practices regardless of outcome [Settles & Meeder 2016, App. A.2; experiment.py line 70].

**As a queueing network.** Reddy, Labutov, Banerjee & Joachims (KDD 2016) fit Mnemosyne logs and adopt the recall model

```
P[recall] = exp(−θ · d / s)                                       (their eq. 1)
```

"where θ ∈ R+ is the item difficulty, d ∈ R+ is the time elapsed since previous review, and s ∈ R+ is the memory strength", and after comparing `s = n_reviews`, `s = 1`, and `s = deck position q`, settle on `P[recall] = exp(−θ · d_i / q_i)` (eq. 2) [Reddy et al. 2016, §2]. In their Leitner Queue Network an item in deck `k` reviewed after delay `D_k` moves up with probability `exp(−θ·D_k/k)` and otherwise down to `max{k−1, 1}`; deck 1 "reflects" (a failed item stays in deck 1), and items recalled at deck `n` (they use `n = 5`) are declared mastered [Reddy et al. 2016, §3]. Each deck is served at rate `μ_k`, new items arrive at rate `λ_ext`, subject to a review budget `λ_ext + Σ_k μ_k ≤ U`, and the scheduler maximises the mastery throughput `λ_out`. Their main qualitative result is a **sharp phase transition**: above a threshold arrival rate `λ_t`, the lowest decks blow up and `λ_out → 0` [Reddy et al. 2016, §3.3, Fig. 5]. For the trainer this is the formal warning against introducing too many new lines at once.

Relevance: Leitner is the minimum viable rule for "probability decreasing in success count": need `1 − R` shrinks roughly like `2^(−s)` at fixed `Δ`; a failure undoes one doubling. The reflecting deck 1 and the `hclip` floor are the "never zero / never one" guards.

## SM-2 (SuperMemo 2) and the Anki variant

Wozniak's SM-2 (1987, published 1990) schedules by interval and an easiness factor `EF` [supermemo-sm2.html]:

```
I(1) := 1
I(2) := 6
I(n) := I(n−1) · EF            for n > 2       (days)

EF' := EF + (0.1 − (5 − q) · (0.08 + (5 − q) · 0.02))     q ∈ {0..5} = response quality
if EF' < 1.3 then EF' := 1.3
```

"If the quality response was lower than 3 then start repetitions for the item from the beginning without changing the E-Factor", and within a session "repeat again all items that scored below four ... until all of these items score at least four" [supermemo-sm2.html]. Initial `EF = 2.5`; Wozniak notes items with `EF < 1.3` "were repeated annoyingly often and always seemed to have inherent flaws in their formulation", which is why the floor exists.

Anki's scheduler keeps these constants as options [anki-deck-options.md]: starting ease 2.50; Hard multiplies the previous interval by 1.20; Easy bonus 1.30; on Again (a lapse) the "New Interval" multiplier defaults to 0.00, i.e. the delay resets and the minimum interval of 1 day applies; and an "Interval Modifier" applied to all intervals, with the SuperMemo rule of thumb `modifier = log(desired retention) / log(current retention)` (e.g. `log 0.90 / log 0.85 = 0.65`). Anki also "forces a new interval to be at least 1 day longer than it was previously".

Relevance: SM-2 is interval-based, not probability-based, so to use it for sampling one converts the interval into a due-ness, e.g. `need = clamp(Δ / I(n), 0, 1)` or the exponential `R = 0.9^(Δ/I)` that FSRS v3 used (see below). The `EF ≥ 1.3` floor and "reset interval, keep EF" on failure are the two rules worth borrowing.

## FSRS (open-spaced-repetition)

FSRS models each item by **Difficulty `D ∈ [1, 10]`**, **Stability `S`** ("interval when R = 90%") and **Retrievability `R`** [fsrs-algorithm-wiki.md, Symbol section]. Formulas, with `G ∈ {1 again, 2 hard, 3 good, 4 easy}`:

Forgetting curve (FSRS-4.5 and later; FSRS-6 makes the decay a trainable parameter `w20`, default 0.1542):

```
R(t, S) = (1 + FACTOR · t / S)^DECAY,   R(S, S) = 0.9
  FSRS-4.5: DECAY = −0.5, FACTOR = 19/81
  FSRS-6:   DECAY = −w20, FACTOR = 0.9^(−1/w20) − 1
Next interval for requested retention r:
I(r, S) = (S / FACTOR) · (r^(1/DECAY) − 1),   I(0.9, S) = S
```

(FSRS v3 and earlier used the exponential `R = 0.9^(t/S)`, `I(r,S) = S · ln r / ln 0.9`.) [fsrs-algorithm-wiki.md, FSRS-4.5 / FSRS-6 / v3 sections]

Stability after a successful review (FSRS v4 form, still the core of later versions):

```
S'_r(D, S, R, G) = S · ( e^{w8} · (11 − D) · S^{−w9} · (e^{w10·(1−R)} − 1) · w15[G=2] · w16[G=4] + 1 )
```

The wiki states the four properties: larger `D` → smaller increase; larger `S` → smaller increase ("the higher the stability of the memory, the harder it becomes to make the memory even more stable"); smaller `R` at review time → larger increase (the spacing effect); and `S'_r / S ≥ 1` always for a successful review [fsrs-algorithm-wiki.md, FSRS v4].

Stability after forgetting (post-lapse):

```
S'_f(D, S, R) = w11 · D^{−w12} · ((S + 1)^{w13} − 1) · e^{w14·(1−R)}
```

With default parameters, `S'_f(S=100) ≈ 3` and `S'_f(S=1) ≈ 0.3` — a lapse collapses stability to a few days regardless of how large it was, but not to zero [fsrs-algorithm-wiki.md, FSRS v4].

Difficulty (FSRS-5/6): initial `D0(G) = w4 − e^{w5·(G−1)} + 1`; update with linear damping and mean reversion

```
ΔD(G) = −w6 · (G − 3)
D'    = D + ΔD · (10 − D) / 9
D''   = w7 · D0(4) + (1 − w7) · D'
```

"to avoid 'ease hell'" [fsrs-algorithm-wiki.md, FSRS-5]. The reference implementation clamps `D` to `[1, 10]`, `S ≥ STABILITY_MIN = 0.001`, the next interval to `[1, maximum_interval]` days, and applies random "fuzz" (±15% below 7 days, ±10% to 20 days, ±5% beyond) to review intervals [py-fsrs-scheduler.py, lines 56, 109–123, 187–188, 232–234, 642–658, 679–693, 806–851].

Relevance: FSRS is the best-fitted general model here, and the trainer can use `1 − R(t, S_ℓ)` directly as a leaf need. The cost is 21 parameters fit on Anki review logs (defaults listed in the wiki) that have no chess validation; what transfers cleanly is the *shape*: multiplicative growth of `S` on success that slows as `S` grows, a collapse-not-reset on failure, explicit floors on every state variable, and jitter on intervals so items do not clump.

## Half-life regression (Duolingo; Settles & Meeder, ACL 2016)

HLR generalises Leitner and Pimsleur by learning the half-life from features [Settles & Meeder 2016, §3.3]:

```
p = 2^(−Δ / h)                                      (1)  Ebbinghaus forgetting curve, Δ = lag in days
ĥ_Θ = 2^(Θ · x)                                     (2)  half-life is exponential in a linear score
Θ* = argmin_Θ Σ_i ℓ(⟨p, Δ, x⟩_i; Θ)                  (3)
ℓ(⟨p, Δ, x⟩; Θ) = (p − p̂_Θ)^2 + α (h − ĥ_Θ)^2 + λ‖Θ‖²₂,   h = −Δ / log₂ p   (observed half-life)
```

Features `x`: interaction counters `x_n` (total practices), `x⊕` (correct), `x⊖` (incorrect) plus sparse lexeme-tag indicators and a bias; the released code actually feeds `sqrt(1 + right)` and `sqrt(1 + wrong)` rather than raw counts, noting that the transformed counts "yielded better results" [Settles & Meeder 2016, §3.4 fn. 5; experiment.py lines 240–245]. Implementation guards: `p̂ ∈ [0.0001, 0.9999]`, `ĥ ∈ [15 min, 9 months]` [Settles & Meeder 2016, App. A.3; experiment.py `pclip`, `hclip`].

Results on 12.9 M Duolingo traces (Table 2): HLR MAE 0.128 vs Leitner 0.235, Pimsleur 0.445, constant baseline 0.175; AUC 0.538 (HLR) vs 0.542 (Leitner) — all AUCs are low because 86% of observations are correct recalls. In a live A/B test, HLR "cut MAE nearly in half" versus the Leitner meters previously deployed [Settles & Meeder 2016, §4].

Relevance: HLR is the natural "trainable Leitner" for the trainer. With just the two counters and a bias the per-branch model is

```
h_ℓ = 2^(θ⊕ · sqrt(1 + s_ℓ) + θ⊖ · sqrt(1 + f_ℓ) + θ_0)
R_ℓ = 2^(−Δ_ℓ / h_ℓ)
```

which reduces to Leitner at `θ⊕ = 1, θ⊖ = −1` on raw counts and can be re-fitted once the app has logs. Per-branch difficulty (the analogue of lexeme tags) could be the branch's ECO code or depth.

## ACT-R memory activation

ACT-R's base-level activation sums power-decaying traces from every past presentation and turns activation into recall probability with a logistic [Pavlik & Anderson 2005, eqs. 1–2]:

```
m_n(t_1..t_n) = ln( Σ_{i=1..n} t_i^(−d) )           (1)   t_i = time since the i-th presentation, d = decay (0.5 in standard ACT-R)
p_r(m)        = 1 / (1 + e^((τ − m)/s))              (2)   τ = threshold, s = noise
```

"when τ = m, the probability of recall is .5", and `s` sets the sharpness of the transition. To capture the spacing effect, Pavlik & Anderson make the decay of each trace depend on activation at the time of presentation:

```
d_i(m_{i−1}) = c · e^{m_{i−1}} + a                   (4)
m_n           = ln( Σ_i t_i^(−d_i) )                 (5)
```

"higher activation at the time of a trial will result in the gains from that trial decaying more quickly" — massed repetitions of an already-known item are cheap, spaced ones are durable. Fitted parameters for their vocabulary experiment: `a = 0.177`, `c = 0.217`, `τ = −0.704`, `s = 0.255` [Pavlik & Anderson 2005, Table 1]. Anderson & Schooler's earlier variant was `d_i = max[d, b · (t_i − t_{i−1})^(−d)]` [Pavlik & Anderson 2005, eq. 3, quoting Anderson & Schooler 1991].

Anderson & Schooler (1991) motivate the power law by showing that the "need odds" of an item in the environment (New York Times headlines, child-directed speech, e-mail) follow power laws in frequency and recency: retention in the NYT window "satisfies a power function with exponent .73", and log need odds are linear in log frequency with slopes around 1.2–1.3 [Anderson & Schooler 1991, Figs. 6–7]. Ebbinghaus's own forgetting data fit `P = 47.56 · T^(−0.126)` [Anderson & Schooler 1991, eq. 5].

Relevance: ACT-R gives the only model here where *every* visit, not just the last one, contributes, and where frequency and recency enter through one sum. Per branch, `m_ℓ = ln Σ_visits (Δ_i)^(−d)` and `need_ℓ = 1 − p_r(m_ℓ)`. It costs storing visit timestamps (or an incremental approximation) and does not by itself distinguish successes from failures — failures must be modelled as *not* adding a trace (or adding a negative one), which is a departure from the published model. Power-law decay of need with success count (`~ s^(−d)`) is gentler than Leitner's geometric `2^(−s)`; Anderson & Schooler's data argue the power form is the empirically right one.

## Softmax / Boltzmann sampling, ε-greedy, UCB

Sutton & Barto define soft-max action selection over per-action preferences `H_t(a)` [Sutton & Barto 2020, eq. 2.11]:

```
π_t(a) = e^{H_t(a)} / Σ_b e^{H_t(b)}
```

with the gradient-bandit preference update `H_{t+1}(A_t) = H_t(A_t) + α (R_t − R̄_t)(1 − π_t(A_t))` and `H_{t+1}(a) = H_t(a) − α (R_t − R̄_t) π_t(a)` for `a ≠ A_t` (eq. 2.12). ε-greedy picks the greedy action except "with small probability ε, instead select randomly from among all the actions with equal probability", so every action keeps probability at least `ε/K` [Sutton & Barto 2020, §2.2]. UCB selects `argmax_a [Q_t(a) + c · sqrt(ln t / N_t(a))]`, where the square-root term "is a measure of the uncertainty ... Each time a is selected the uncertainty is presumably reduced" [Sutton & Barto 2020, eq. 2.10].

Cesa-Bianchi, Gentile, Lugosi & Neu (NeurIPS 2017) analyse Boltzmann exploration `p_{t,i} ∝ exp(η_t μ̂_{t,i})` and show "the Boltzmann exploration strategy with any monotone learning-rate sequence will induce suboptimal behavior" (Theorem 1), because it "does not reason about the uncertainty of the empirical reward estimates". Their fix, Boltzmann-Gumbel exploration (BGE), samples

```
I_{t+1} = argmax_i { μ̂_{t,i} + β_{t,i} · Z_{t,i} },   β_{t,i} = sqrt(C² / N_{t,i}),   Z_{t,i} ~ Gumbel(0,1) i.i.d.
```

i.e. a softmax whose temperature per arm shrinks with its visit count `N_{t,i}` [Cesa-Bianchi et al. 2017, §4, eq. 4, Theorem 3]. The same paper states the Gumbel-max identity: sampling `p ∝ exp(η μ̂)` equals `argmax_j {η μ̂_j + Z_j}` with standard Gumbel noise — which lets you draw from a softmax in one pass without normalising.

Relevance: for the trainer, "score" is not reward but *need*; softmax over `score(m) = α · ln n(v,m) + γ · need(m)` is a clean way to blend popularity with history at each opponent node, and its probabilities are strictly positive by construction (though they can be astronomically small — a hard floor still needs ε-mixing or a clamp). BGE's per-arm temperature `1/sqrt(N)` is a principled version of "moves the learner has rarely faced get extra randomness". The regret theory itself does not transfer: the trainer is not trying to identify a best arm.

## Weighted-tree sampling with Lichess popularity, and fast sampling

**Popularity source.** The Lichess opening explorer returns, for a position, `white/draws/black` totals and a `moves` array where each move carries its own `white`, `draws`, `black` counts (plus `averageRating`, `topGames`), for the `/masters`, `/lichess` (rated games, filterable by `speeds` and `ratings`) and `/player` databases [refs/lichess/lila-openingexplorer-README.md, lines 158–230; refs/lichess/lichess-api-openapi.yaml "Opening Explorer" tag]. So at opponent node `v` the empirical move distribution is `P_pop(m | v) = n(v,m) / N(v)`; the popularity of a whole branch is the product of these along the path, which is the probability a random database game follows that line.

**Fast discrete sampling.** Walker's alias method draws from an arbitrary discrete distribution over `n` outcomes with "at most two memory references and a comparison" per draw; Vose (1991) reduced table construction from `O(n log n)` to `O(n)` [Vose 1991, abstract and §III; Stratos notes, Lemma]. The Duolingo and FSRS implementations are relevant for a different reason: they show that clipping (`pclip`, `hclip`, `STABILITY_MIN`, `D ∈ [1,10]`) is how production systems keep every item's weight in a bounded, non-zero range.

## Composing weights over an opening tree

A branch is a path, so the learner's history attaches to leaves (or, if the learner may stop mid-line, to the deepest repertoire node reached). The opponent chooses only at *opponent nodes*; at learner nodes the learner's own move selects the child. The composition question is: given per-leaf need `u_ℓ ∈ [ε, 1]` and per-move popularity `n(v,m)`, what probability does the opponent assign to each move at `v`?

Three candidate rules, all with `O(depth)` updates and `O(depth · branching)` draws.

### Rule 1 — product of popularity and need, subtree-sum composition

Define a leaf weight and propagate sums upward:

```
pop_ℓ  = Π_{(v,m) opponent moves on the path to ℓ}  n(v,m) / N(v)
u_ℓ    = ε + (1 − R_ℓ)                         need, floored at ε > 0
w_ℓ    = pop_ℓ · u_ℓ
W(v)   = Σ_{children c of v} W(c),   W(ℓ) = w_ℓ for leaves
Opponent at v plays m with probability  W(child(v,m)) / W(v)
```

Property: because the ratios telescope, each leaf is drawn with probability exactly `w_ℓ / W(root)`, so the rule is equivalent to sampling a whole branch proportional to `popularity × need` — it is a per-branch rule, not a per-node one. Learner nodes contribute `W(v) = Σ W(c)` too, which makes `W` at an opponent node the expected need over everything below it. (At a learner node the learner picks the child, so the sum is only used for bookkeeping; if the learner has a single repertoire move, `W(v) = W(that child)`.)

Need model: Leitner/HLR is the simplest choice that already has a floor,

```
h_ℓ = clip( h0 · 2^(s_ℓ − f_ℓ),  h_min, h_max )        h0 ≈ 1 day; Duolingo clips [15 min, 9 months]
R_ℓ = 2^(−Δ_ℓ / h_ℓ)                                    Δ_ℓ = time since last visit; R = 0 if never visited
```

Failures raise weight by halving `h` (one failure undoes one success); time raises weight continuously; a fresh success at `Δ ≈ 0` drives `u_ℓ` to `ε` for the rest of the session. Alternative need models drop in without changing composition: FSRS `R(t, S_ℓ)` with its `S'_r/S'_f` updates (collapse-not-reset on failure, difficulty-aware), or ACT-R `1 − p_r(m_ℓ)` if visit times are stored.

Update after visiting leaf `ℓ`: recompute `w_ℓ`, then add `Δw` to every ancestor — `O(depth)`. Sampling: at each opponent node pick a child proportionally — `O(branching)` per node, `O(depth · branching)` per game; with typical repertoire branching (≤ 10) this is microseconds. If some node has many moves, keep a per-node alias table rebuilt lazily on change (`O(branching)` build, `O(1)` draw).

Floor guarantee: `w_ℓ ≥ ε · pop_ℓ > 0` as long as every repertoire move has `n(v,m) ≥ 1` (use `n + 1` Laplace smoothing for moves absent from the database). The popularity exponent can be tempered, `pop_ℓ^α` with `α ∈ (0,1]`, to stop a single main line from dominating; `α = 0` gives pure need-driven sampling.

### Rule 2 — per-node softmax of log-popularity and subtree-max need

Aggregate need by maximum rather than sum, and sample with a tempered softmax at each opponent node:

```
U(v)   = max_{children c} U(c),   U(ℓ) = u_ℓ                    "the weakest line below this move"
score(v, m) = α · ln(n(v,m) + 1) + γ · U(child(v,m))
P(m | v) = exp(score(v,m) / T) / Σ_{m'} exp(score(v,m') / T)
```

`α` sets how much realism (popularity) matters, `γ` how much the learner's gaps matter, `T` is temperature. Max-aggregation means a move is "well known" only when every line under it is well known, so a single weak sub-line keeps the whole branch alive; sum-aggregation (Rule 1) instead dilutes a weak sub-line by its siblings. Update cost is `O(depth · branching)` (recompute the max at each ancestor). Probabilities are strictly positive but can be tiny; add an explicit floor by mixing: `P' = (1 − ε) P + ε · P_pop` (the ε-greedy trick with popularity as the "random" component), which guarantees `P'(m|v) ≥ ε · n(v,m)/N(v)`.

A BGE-style variant replaces `T` with a per-move temperature `β(v,m) = C / sqrt(1 + visits(v,m))`, so moves the learner has rarely faced get more perturbation: draw `Z_m ~ Gumbel`, play `argmax_m [score(v,m) + β(v,m) Z_m]` — one pass, no normalisation [after Cesa-Bianchi et al. 2017, eq. 4].

### Rule 3 — ε-mixture of "realistic opponent" and "targeted opponent"

The simplest rule that satisfies the never-zero clause outright:

```
with probability ε:      m ~ P_pop(· | v) = n(v,m) / N(v)                (play like the database)
with probability 1 − ε:  m ~ Rule 1 (or Rule 2) restricted to lines with U(child) > ε_need
```

so every game has an `ε` chance of ignoring history altogether. This also handles the cold start (no history → everything is need 1 → Rule 1 reduces to popularity anyway) and gives the learner "realistic" games as a by-product. The choice of `ε` is directly interpretable ("one game in twenty is a random-book game").

### How the three differ on the ticket's criteria

| Criterion | Rule 1 (Σ, product) | Rule 2 (max, softmax) | Rule 3 (ε-mix) |
|---|---|---|---|
| Decay with success count | geometric via `2^(s−f)` inside `R` | same, but a weak sibling line blocks decay | inherits from the inner rule |
| Forgetting / time | `R` falls with `Δ`; `u → 1` as `Δ ≫ h` | same | same |
| Failure raises weight | halves `h` (or FSRS collapse) | same | same |
| Floor | `ε · pop_ℓ` | softmax > 0; add `ε · P_pop` mix for a hard floor | `ε · P_pop` by construction |
| Cost per game / per update | `O(depth·b)` / `O(depth)` | `O(depth·b)` / `O(depth·b)` | as inner rule |
| Free parameters | `ε, h0, h_min, h_max, α` | `α, γ, T, ε` | `ε` + inner |

## Implications for the trainer

- **Recommendation (hedged; the sampling rule is the subject of ticket 06 and its ADR):** start with Rule 1 with a Leitner/HLR need, `ε ≈ 0.05–0.1`, `h0 = 1 day`, `h ∈ [15 min, 9 months]` as in Duolingo, popularity from the Lichess explorer with `+1` smoothing, `α = 1`. It is the only rule whose per-branch probability is a closed form (`pop_ℓ · u_ℓ / W`), so it is easy to explain in the progress view, trivially `O(depth)`, and every ingredient has a primary source. Swap the need model for FSRS later if logs show geometric decay is too aggressive; nothing else changes.
- **Do not let time alone drive sampling.** Within a fast session `Δ` is minutes, so a purely time-based `R` treats a line played once as known. The count term `2^(s − f)` (or FSRS's `S` growth) is what makes repeated successes matter; the `h_min` clip is what stops a line from vanishing for the whole session after one success.
- **Failures should collapse, not reset.** SM-2 resets the interval but keeps `EF`; Anki's default "New Interval 0%" resets fully; FSRS's `S'_f` collapses to a few days with a floor. For the trainer, halving `h` (one failure ≈ one success undone) is the gentlest and keeps history; a "leech" guard (FSRS: mean reversion of `D`; SM-2: reformulate items with `EF < 1.3`) is the analogue of flagging a line the learner keeps failing for review of the repertoire itself.
- **Introduce new lines slowly.** Reddy et al.'s phase transition says throughput collapses when new items arrive faster than the low decks can be served; the trainer's equivalent is a cap on the number of leaves with `s_ℓ = 0` active at once, or seeding sub-trees progressively by popularity.
- **Add jitter.** FSRS fuzzes intervals ±5–15% so items do not clump; in a sampler the randomness is already there, but a deterministic "most needed line" mode should add noise (Gumbel or BGE) for the same reason.
- **Measure before tuning.** Every quoted parameter (`h0`, `α`, FSRS weights, ACT-R `a, c, τ, s`) was fitted on vocabulary or flashcard logs, not on chess lines; treat them as priors. Log `(leaf, Δ, s, f, outcome)` from day one so `θ⊕, θ⊖` can be re-fitted HLR-style; HLR's own paper shows the gain from fitting is large (MAE 0.235 → 0.128).
- **Transpositions and "a branch is a path".** All three rules attach history to leaves; if ticket 05/06 decide that a position reached by two paths is one item, the need must live on the position and the leaf weight becomes `pop_ℓ · u(position(ℓ))` — the composition is unchanged, only the key is.

## Sources

Primary sources, with local copies under `refs/algorithms/`:

- Wozniak, P. A. (1990/1998). *Application of a computer to improve the results obtained in working with the SuperMemo method* (SM-2). https://super-memory.com/english/ol/sm2.htm — `supermemo-sm2.html`.
- Anki manual, *Deck Options* (SM-2 variant constants and FSRS settings). https://github.com/ankitects/anki-manual/blob/main/src/deck-options.md — `anki-deck-options.md`.
- open-spaced-repetition, *The Algorithm* (FSRS v1–v6 formulas and default parameters). https://github.com/open-spaced-repetition/awesome-fsrs/wiki/The-Algorithm — `fsrs-algorithm-wiki.md`.
- open-spaced-repetition, *py-fsrs* `fsrs/scheduler.py` (reference implementation: clamps, fuzz, interval). https://github.com/open-spaced-repetition/py-fsrs/blob/main/fsrs/scheduler.py — `py-fsrs-scheduler.py`.
- Settles, B. & Meeder, B. (2016). *A Trainable Spaced Repetition Model for Language Learning*. ACL, pp. 1848–1858. https://aclanthology.org/P16-1174.pdf — `settles-meeder-2016-half-life-regression.pdf`.
- Duolingo, *halflife-regression* README and `experiment.py` (HLR, Leitner, Pimsleur baselines with clipping constants). https://github.com/duolingo/halflife-regression — `duolingo-hlr-README.md`, `duolingo-hlr-experiment.py`.
- Reddy, S., Labutov, I., Banerjee, S. & Joachims, T. (2016). *Unbounded Human Learning: Optimal Scheduling for Spaced Repetition*. KDD. https://arxiv.org/abs/1602.07032 — `reddy-2016-leitner-queue-network.pdf`.
- Anderson, J. R. & Schooler, L. J. (1991). *Reflections of the Environment in Memory*. Psychological Science 2(6), 396–408. https://users.cs.northwestern.edu/~paritosh/papers/KIP/AndersonSchooler1991ReflectionsOfEnvironmentOnMemory.pdf — `anderson-schooler-1991-reflections.pdf`.
- Pavlik, P. I. & Anderson, J. R. (2005). *Practice and Forgetting Effects on Vocabulary Memory: An Activation-Based Model of the Spacing Effect*. Cognitive Science 29, 559–586. http://act-r.psy.cmu.edu/wordpress/wp-content/uploads/2012/12/409s15516709cog0000_14.pdf — `pavlik-anderson-2005-activation-spacing.pdf`.
- Sutton, R. S. & Barto, A. G. (2020). *Reinforcement Learning: An Introduction*, 2nd ed., ch. 2 (ε-greedy §2.2, UCB eq. 2.10, soft-max eqs. 2.11–2.12). http://incompleteideas.net/book/RLbook2020.pdf — `sutton-barto-2020-rlbook.pdf`.
- Cesa-Bianchi, N., Gentile, C., Lugosi, G. & Neu, G. (2017). *Boltzmann Exploration Done Right*. NeurIPS. https://arxiv.org/abs/1705.10257 — `cesa-bianchi-2017-boltzmann-done-right.pdf`.
- Vose, M. D. (1991). *A Linear Algorithm for Generating Random Numbers with a Given Distribution*. IEEE TSE 17(9), 972–975. https://web.archive.org/web/20131029203736/http://web.eecs.utk.edu/~vose/Publications/random.pdf — `vose-1991-alias-linear.pdf`.
- Stratos, K. *The Alias Method* (formal note on Walker/Vose). https://karlstratos.com/notes/alias_method.pdf — `stratos-alias-method-notes.pdf`.
- Lichess, *lila-openingexplorer* README and OpenAPI spec (explorer response format), already downloaded by ticket 02 under `refs/lichess/`.

Referenced but not downloaded (paywalled or secondary): Walker, A. J. (1977), *An Efficient Method for Generating Discrete Random Variables with General Distributions*, ACM TOMS 3(3), 253–256, https://doi.org/10.1145/355744.355749; Leitner, S. (1972), *So lernt man lernen*; Wozniak's two-component (stability/retrievability) model pages at supermemo.guru, which are behind a bot challenge.
