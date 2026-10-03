# 33: Your data: export and forget

**What to build:** `/data` ("Your data"), linked from the footer and the account page, gives every learner their rights without writing to the owner. Download my data returns one JSON file named `chessop-data-YYYY-MM-DD.json`, generated on request, streamed, never stored: format version, export time, snapshot version; the account (kind, email or Lichess username, created date) or `null`; the learner's creation and last-seen times; settings; every position record (FEN, passes, misses, last pass, relearning owed); the full round log; the daily scores. No tokens, hashes or computed estimates. An anonymous learner gets "Forget this browser's history": confirm, hard delete, cookie cleared. A signed-in learner is pointed to account deletion. With no learner yet, the page says nothing is stored. (Spec §10.)

**Blocked by:** 29

**Status:** done

- [x] The export of an anonymous and of a signed-in learner contains exactly the listed fields and matches what they played
- [x] The export contains no session token, hash or estimate
- [x] "Forget this browser's history" deletes the learner and clears the cookie; a later visit has no history
- [x] A visitor with no learner sees that nothing is stored, and no learner is created by visiting
- [x] The page is `noindex` and absent in local mode
