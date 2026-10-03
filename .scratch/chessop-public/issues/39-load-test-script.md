# 39: Load-test script

**What to build:** A kept script starts N scripted WebSocket learners against a running hosted chessop (local or the VPS), each playing rounds as an anonymous learner, and reports the p50 and p95 of the server's move handling and end-to-end reply time, plus the server's resident memory when it can read it. It is the pre-launch gate: under 10 ms p95 with 30 learners playing, and resident memory under 1 GB at 300 sessions. Run by hand, not in CI. (Spec §7.)

**Blocked by:** 38

**Status:** done

- [x] The script takes a target URL, a learner count and a duration, and prints p50, p95 and memory
- [x] Run against a local hosted server with 30 learners it completes and reports figures within the budget
- [x] It does not run in the default test suite
