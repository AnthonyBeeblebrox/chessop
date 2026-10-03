# 08: Explanations

**What to build:** at the end of every round the learner reads a short explanation of where the round ended, from Wikibooks *Chess Opening Theory*: the lead, a "more" toggle for the full text, a label when the text is borrowed from an earlier position on the path, and the CC BY-SA footer. `build-snapshot` fetches and trims the pages and writes the separate explanation file.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §3.2 step 6, §3.3 (explanation file), §8 (`round_over.explanation`), §9, §12. ADR 0003 ticket 15 amendment; `docs/research/opening-explanations.md` §1b for the trimming rules.

**Blocked by:** 03 (`build-snapshot`: the graph file).

**Status:** done

- [ ] Wikibooks titles built from the book line and the canonical order (`N. SAN` / `N...SAN`, `+ # ! ?` stripped, at most 30 plies)
- [ ] Queries the wikitext API, 50 titles per request, `redirects=1`, `maxlag=5`, in series, with a descriptive User-Agent carrying contact; each page stored once
- [ ] Wikitext converted to plain paragraphs per spec §3.2 step 6; lead = prose before the first remaining sub-heading, capped at a few hundred characters
- [ ] Explanation file with a CC BY-SA 4.0 licence header stating the text was trimmed, pages `{id, title, url, lead, text}`, and an `epd -> page id` map shared by all bands
- [ ] `round_over.explanation` is the page of the position where the round ended (the leaf on a success), else the nearest position with a page on the path walked with `borrowed_from` in SAN, else null
- [ ] Page: lead under the verdict strip, "more" expands in place without moving the board, borrowed label, footer "From Wikibooks, *Chess Opening Theory* · CC BY-SA 4.0 · trimmed" linking the title
- [ ] Tests: the converter offline on the saved wikitext samples in `refs/openings-text/`; explanation and fallback over the wire
- [ ] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
