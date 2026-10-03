# 38: Shared caches and off-loop builds

**What to build:** Hosted mode holds 300 sessions in memory and never stalls one learner's move on another's build. Band graphs load on first use and stay for the process's life. The repertoire, progress ledger and the repertoire-only steering caches are shared by every learner with the same settings key (band, widths, popularity floor, share, opted-out openings) in a least-recently-used cache of 16 entries. The default key (1500+, default settings) is warmed at startup; any other band graph, repertoire or ledger is built in a worker thread. A learner session keeps only its own records, steering state, faced counts and notices. The single round-end lock stays, with the commit on the event loop. Behaviour seen from outside is unchanged. (Spec §4, §7, ADR 0004.)

**Blocked by:** 28

**Status:** done

- [x] Two learners with the same settings share one repertoire and steering caches; a learner with different settings gets their own
- [x] The 17th distinct settings key evicts the least recently used
- [x] The first move of a learner on default settings waits on no build after startup
- [x] While a non-default repertoire builds, another learner's moves are still answered
- [x] Existing wire, settings and progress tests pass in both modes
