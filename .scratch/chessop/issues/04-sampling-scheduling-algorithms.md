# Algorithms: how should a branch's sampling probability decay with its success count?

Type: research
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Survey scheduling/sampling algorithms that fit 'opponent plays a branch with probability decreasing in its success count, never zero': SM-2, FSRS, Leitner, softmax/Boltzmann sampling over a weight, half-life regression (Duolingo), and weighted-tree sampling where the opponent's move choice at each node combines Lichess popularity with the learner's per-branch history. Cover how weights compose down a tree (a branch is a path, not a node), how forgetting/time-since-last-visit enters, and how to keep sampling fast. Write findings with formulas and citations to `docs/research/sampling-algorithms.md`.

AFK. Fired at charting time.

## Answer

Every spaced-repetition family reviewed (Leitner, SM-2/Anki, FSRS, Duolingo half-life regression, ACT-R) keeps a per-item strength that grows with successes and collapses on failure, then turns strength plus elapsed time into a recall probability R; the trainer's sampling weight is just need = eps + (1 - R). The simplest closed form is Leitner/HLR: h = h0 * 2^(s - f), R = 2^(-delta/h), with h clipped to [15 min, 9 months] as Duolingo does, so nothing reaches zero. FSRS gives a difficulty-aware alternative with the same shape (multiplicative stability growth, collapse-not-reset on lapse, D in [1,10], S >= 0.001); ACT-R gives power-law rather than geometric decay in success count. Softmax never gives zero probability, epsilon-greedy gives a hard floor eps/K, and Boltzmann-Gumbel adds a 1/sqrt(visits) uncertainty bonus.
Over the tree, weights compose by subtree sums: leaf weight w = popularity(path) * need, W(node) = sum over children, opponent plays a move with probability W(child)/W(node); each leaf is then drawn with probability exactly w/W(root), updates touch only O(depth) ancestors, and draws cost O(depth * branching) (alias tables if branching is large). Two alternatives are written out: a per-node softmax over alpha*log(popularity) + gamma*subtree-max need, and an eps-mixture with the pure Lichess move distribution.
Hedged recommendation: Rule 1 (product, subtree-sum) with Leitner/HLR need, eps ~ 0.05-0.1, Lichess explorer counts with +1 smoothing; cap the number of unvisited lines active at once (Reddy et al.'s phase transition); log (leaf, delta, s, f, outcome) so the weights can be refitted HLR-style. Parameters from the literature are vocabulary-fitted priors, not chess results. The rule itself is to be settled in ticket 06.
Findings: ../../../docs/research/sampling-algorithms.md
