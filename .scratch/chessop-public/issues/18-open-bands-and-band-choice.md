# 18: Open bands and direct band choice

**What to build:** A learner picks their rating band directly from a list of eight in settings: the five closed bands plus the open bands 1200+, 1500+ and 1800+ (2100+ is both). The snapshot build feeds a game into every band both players fall in; an open band needs both players at or above the bound. The declared rating and its mapping to a band disappear from settings, storage and UI. The default is 1500+, and a band absent from the loaded snapshot falls back to 1500+. The fixture graph gains the bands the tests need. (Spec §2, ADR 0003. Rebuilding the packaged snapshot is ticket 47.)

**Blocked by:** None (can start immediately)

**Status:** done

- [x] The snapshot build puts one game in every band both players fall in; open-band membership needs both players at or above the bound (build tests)
- [x] The 150,000-per-band cap, filters, ply cap and file shapes are unchanged
- [x] Settings shows a band list of eight and no rating field; saving a band regenerates the repertoire as a rating change did before
- [x] A new learner starts on 1500+ without being asked anything
- [x] A stored band missing from the loaded snapshot falls back to 1500+
- [x] No code, template or test still refers to a declared rating, except the v1 migration path left for ticket 22
