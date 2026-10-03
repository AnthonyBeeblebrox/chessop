# 26: Phone layout: progress

**What to build:** On a narrow screen the progress table shows only opening name, Score, White and Black; ECO, positions and the known/learning bar are hidden; the in/out and reset actions appear when a row is opened; move chips gain about 6 px of tap padding. Settings needs no change. Desktop is unchanged. Port from branch `prototype/mobile`, variant Condensed table. (Spec §8.)

**Blocked by:** 19

**Status:** done

- [x] The narrow table shows the four columns and fits a phone width without horizontal scroll (verified by hand)
- [x] Opening a row reveals its in/out and reset actions, which work as on desktop
- [x] Move chips have the larger tap area
- [x] The desktop progress view and existing progress tests are unchanged

## Comments

- Verified by hand in headless chromium (CDP, touch emulation, fresh profile) at 390x844 and 320x640: the progress page's width equals the viewport (it was 489 px wide at 390 before); a body row shows only opening, score, White and Black; tapping a row opens it and shows its in/out and reset, and tapping them took the opening out and opened the reset confirmation as on desktop; move chips measure 36 px tall (23 before). With scripts off, progress (closed and fully opened) and settings were pixel-identical to the previous commit at 1280x900 and 900x900.
- The positions cells and the header's empty actions cell now carry `pos` and `acts` classes, so the narrow rule hides them by name rather than by place; no desktop rule uses them.
- The narrow rules apply to every `.ledger .table`, so they sit in `play.css` beside the 60em rule rather than under a page class; the help and position pages carry no `.row`, `.acts` or `.branches`.
- Ticket 25 hid every `.links` below 40em, so on a phone progress, settings, help and the position page lost their way back to play. Only the play page's corner links (`body > .links`) now go; the others keep theirs.
- The Stacked play header was 10 px wider than the screen (width 100% plus its padding), which gave the play page a horizontal scroll at 390 and 320 px; it now has `box-sizing: border-box`, as the landscape block already gave it.
