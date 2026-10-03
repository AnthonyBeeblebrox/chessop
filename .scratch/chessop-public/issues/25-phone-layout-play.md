# 25: Phone layout: play

**What to build:** Below about 40em wide the play page is Stacked: one compact header row (side badge, Score and its change, three 44 px icon buttons for sound, progress and settings), the opening name and "not X this time" on their own line, the board as wide as the screen capped at 72vh with `touch-action: none`, the verdict strip wrapping to two lines, a full-width green Next round button at least 52 px tall shown only once the round is over, and the Explanation below. Drag and tap-to-move both work, and dragging never scrolls or zooms the page. In landscape on a narrow screen the board sits on the left at full height with the rest in a column beside it. The desktop layout and keys are unchanged. Port from branch `prototype/mobile`, variant Stacked. (Spec §8.)

**Blocked by:** 19

**Status:** done

- [x] Portrait and landscape narrow layouts match the prototype (verified by hand at phone widths)
- [x] Tap-to-move and drag both play a move; dragging does not scroll or zoom
- [x] The sound icon toggles and shows 🔊/🔇; progress and settings icons navigate
- [x] Next round appears only after the round ends; tapping the verdict still starts the next round; the "space" hint is hidden on touch
- [x] The desktop layout, keys and existing tests are unchanged

## Comments

- Verified by hand in headless chromium with touch emulation at 390x844, 320x640 (portrait), 844x390 and 740x360 (landscape): tap-to-move and touch drag each played a move with no scroll or zoom, Next round appeared only after the round ended and started the next one, the sound icon toggled 🔊/🔇, and the "space" hint was hidden. With scripts off, the desktop page was pixel-identical to the previous commit at 1280x800, 1000x700, 700x900, 1400x480 and 900x400.
- Chessground remembers where the board is until a scroll or resize. On a phone the banner grows when a long opening name wraps, which moves the board without either, and taps then missed (reproduced at 320 px). `play.js` now clears chessground's cached bounds (`cg.state.dom.bounds.clear()`) when the banner or the notice changes size. That field belongs to the vendored chessground's state, so check it when chessground is upgraded.
- The landscape split applies to `(orientation: landscape) and (max-height: 32em) and (pointer: coarse)`, so a short desktop window keeps the desktop layout.
- On a phone the corner "help" link (§9) goes with the other corner links, as §8 says, so help is reachable only from the post-round "what does this mean?" line. A fourth header icon would fix this if that is wanted.
