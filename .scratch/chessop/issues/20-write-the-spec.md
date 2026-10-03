# Spec: write the build-ready v1 spec from the ADRs and the resolved tickets

Type: task
Status: resolved
Blocked by: 
Map: [Chess opening trainer by sampling](../map.md)

## Question

Nothing is left to decide: nineteen tickets, six ADRs with their amendments and the glossary hold every v1 decision. The destination is `.scratch/chessop/spec.md`, a spec a coding agent can implement with no design decision left open. Write it: one document, in the order a builder needs it (glossary pointer, packaging and CLI, `build-snapshot` and the snapshot files, the repertoire rule at load, the memory model and the sampling rule, the Score, persistence and schema including the daily score table, the four socket messages with their schemas and the latency budget, the play page, the progress view's two pages, settings, sounds and licences, tests), each section citing the ADR or ticket it comes from and restating nothing the ADRs already decide at length (link, gist, the numbers). Where two sources disagree, the later amendment wins; list any contradiction found instead of resolving it. AFK: no new decisions; anything that turns out undecided becomes a new ticket, not a choice made in the spec.

## Answer

Written: [`spec.md`](../spec.md), 17 sections in the order the ticket asked for (what is built and the glossary pointer; packaging and CLI; `build-snapshot` and the two snapshot files; the repertoire at load; the memory model, aggregates and the round; the Score; persistence with the five tables; the socket protocol with the four message schemas and the latency budget; the play page; the progress view's two pages and its actions; settings; sounds, assets and licences; tests; deliverables), each citing its ADR or ticket and giving gist plus numbers rather than restating the reasoning.

Two contradictions found and left open (spec §15): **C1** whether a mid-round `moved` still carries the reveal (ADR 0004 says yes, ticket 10 shows nothing mid-round and did not amend the wire); **C2** which position a success reveals (ticket 10's prototype: the position last moved from; ticket 15: "the leaf", which has no main moves to draw).

Three undecided details found (spec §16): **G1** the need aggregation over an empty subtree (stubs, leaf children, moveless learner-to-move leaves), which forced exploration and the opponent's weights depend on, and whether a moveless position is a learner position; **G2** whether forced rounds count in the daily table's rounds and the in-session success rate, given "net of forced exploration" predates the forced outcome; **G3** how the `m` sound toggle is persisted under a four-message protocol.

All five go to ticket 21 (grilling). The spec is blocked on nothing else; §17 lists the readings it made where sources were silent on a detail (aggregation weights are pooled counts, passes applied at round end, `faced` rebuilt from the round log, reset-all deletes records only, and so on), each with the source it follows from, so a reviewer can veto one.

No ADR or glossary change; no decision made here.
