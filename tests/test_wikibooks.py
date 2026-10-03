"""The explanation side of `build-snapshot`: Wikibooks titles, the API, the wikitext converter and
the explanation file. Offline: the converter runs on the wikitext saved under `refs/`."""

import email.message
import gzip
import io
import json
import urllib.error
import urllib.parse
from pathlib import Path

import pytest

from chessop.graph import DEFAULT_BAND, Graph, Position
from chessop.wikibooks import (
    LEAD_CAP,
    SavedPages,
    WikibooksApi,
    build_explanations,
    convert,
    title_for,
    write_explanation_file,
)
from graphs import board_after, epd_after

REFS = Path(__file__).parents[1] / "refs" / "openings-text"
SICILIAN = (REFS / "wikibooks-sample-1e4-c5.wikitext").read_text()


@pytest.fixture(scope="module")
def book_pages() -> dict[str, str]:
    """The wikitext of every page of Chess Opening Theory, as saved by ticket 14."""
    with gzip.open(REFS / "wikibooks-Chess_Opening_Theory-pages.json.gz") as f:
        return {title: page["wikitext"] for title, page in json.load(f).items()}


# Titles


def test_a_title_numbers_white_and_black_moves_and_strips_check_and_annotations() -> None:
    assert title_for(["e4", "c5", "Nf3"]) == "Chess Opening Theory/1. e4/1...c5/2. Nf3"
    assert title_for(["e4", "e5", "Qh5", "Nc6", "Bc4", "Nf6", "Qxf7#"]) == (
        "Chess Opening Theory/1. e4/1...e5/2. Qh5/2...Nc6/3. Bc4/3...Nf6/4. Qxf7"
    )
    assert title_for(["e4", "e5", "f4!?", "exf4", "Bc4", "Qh4+"]) == (
        "Chess Opening Theory/1. e4/1...e5/2. f4/2...exf4/3. Bc4/3...Qh4"
    )


def test_no_title_for_the_start_or_beyond_thirty_plies() -> None:
    assert title_for([]) is None
    assert title_for(["Nf3", "Nf6", "Ng1", "Ng8"] * 7 + ["Nf3", "Nf6"]) is not None  # 30 plies
    assert title_for(["Nf3", "Nf6", "Ng1", "Ng8"] * 7 + ["Nf3", "Nf6", "Ng1"]) is None


# The converter


def test_the_position_template_the_move_heading_and_the_hidden_sections_are_dropped() -> None:
    page = convert(SICILIAN)
    assert page is not None
    assert "Chess Position" not in page.text and "responses" not in page.text
    assert "Sicilian defence==" not in page.text and "1...c5 · Sicilian" not in page.text
    assert page.text.startswith("1...c5 is the Sicilian defence, a counter-attacking")
    assert "wikitable" not in page.text and "365Chess" not in page.text  # the table
    assert "{{" not in page.text and "}}" not in page.text and "<ref" not in page.text
    assert "Cite web" not in page.text and "chess.com" not in page.text  # references


def test_links_lose_their_markup_and_keep_their_label() -> None:
    page = convert(SICILIAN)
    assert page is not None
    assert "The main approach for White is the Open Sicilian: 2. Nf3 intending" in page.text
    assert "reminiscent of the Bongcloud opening." in page.text
    assert "a 1594 codex by Giulio Polerio l'Apruzzese" in page.text
    assert "[[" not in page.text and "'''" not in page.text and "''" not in page.text


def test_the_lead_is_the_prose_before_the_first_sub_heading_capped() -> None:
    page = convert(SICILIAN)
    assert page is not None
    assert page.lead.startswith("1...c5 is the Sicilian defence")
    assert "Open the position" not in page.lead
    assert len(page.lead) <= LEAD_CAP
    assert page.lead.endswith((".", "…"))
    assert page.text.startswith(page.lead.rstrip("…").rstrip())


def test_sub_headings_stay_in_the_full_text_as_their_own_paragraphs() -> None:
    page = convert(SICILIAN)
    assert page is not None
    paragraphs = page.text.split("\n\n")
    assert "Open the position" in paragraphs
    assert "History" in paragraphs
    assert all(p.strip() == p and p for p in paragraphs)


def test_a_short_lead_is_kept_whole() -> None:
    page = convert("{{Chess Opening Theory/Position|x}}\n== 1. e4 ==\n\nWhite takes the centre.\n")
    assert page is not None
    assert page.lead == page.text == "White takes the centre."


def test_a_page_without_prose_converts_to_nothing() -> None:
    wikitext = (
        "{{Chess Opening Theory/Position\n|Foo\n}}\n== 1. a3 · Foo ==\n{{ChessMid}}\n"
        "== Theory table ==\n{{Chess Opening Theory/Table|x}}\n== References ==\n{{reflist}}\n"
        "{{Chess Opening Theory/Footer}}\n"
    )
    assert convert(wikitext) is None


def test_quotations_and_notation_templates_are_kept() -> None:
    wikitext = (
        "== 1. e4 ==\nAfter 12. Qd4! {{Chess/not|++}}. Black is lost. "
        "Compare the {{w|Wing Gambit}}.\n\n"
        "<blockquote>Almost a respectable opening.</blockquote>\n"
        "When contributing to this Wikibook, please follow the Conventions for organization.\n"
    )
    page = convert(wikitext)
    assert page is not None
    assert page.text == (
        "After 12. Qd4! ±. Black is lost. Compare the Wing Gambit.\n\nAlmost a respectable opening."
    )


def test_magic_words_are_dropped_and_the_move_heading_with_them(book_pages: dict[str, str]) -> None:
    page = convert(book_pages["Chess Opening Theory/1. e4"])
    assert page is not None
    assert page.lead.startswith("Best by test.")
    assert "__NOTOC__" not in page.text and "King's Pawn opening\n" not in page.text


def test_the_whole_saved_book_converts_to_clean_plain_text(book_pages: dict[str, str]) -> None:
    converted = {title: convert(w) for title, w in book_pages.items()}
    pages = [p for p in converted.values() if p is not None]
    assert len(pages) > 0.8 * len(book_pages)
    for page in pages:
        assert page.lead and page.text
        assert len(page.lead) <= LEAD_CAP
        for mark in (
            "{{",
            "}}",
            "[[",
            "]]",
            "<ref",
            "'''",
            "{|",
            "|}",
            "==",
            "<br",
            "__",
            "thumb|",
        ):
            assert mark not in page.text, (mark, page.text[:200])


def test_the_najdorf_page_reads_like_the_lichess_extract(book_pages: dict[str, str]) -> None:
    extract = json.loads((REFS / "wikibooks-api-sample-najdorf-extract-plaintext.json").read_text())
    [expected] = extract["query"]["pages"]
    page = convert(book_pages[expected["title"]])
    assert page is not None
    first = expected["extract"].split("\n")
    prose = next(line for line in first if line and not line.startswith("="))
    assert page.text.startswith(prose.strip()[:80])


# The API


class FakeApi:
    """Answers the MediaWiki action API from a dict of pages and redirects, recording requests."""

    def __init__(self, pages: dict[str, str], redirects: dict[str, str] | None = None) -> None:
        self.pages = pages
        self.redirects = redirects or {}
        self.requests: list[tuple[dict[str, list[str]], dict[str, str]]] = []

    def __call__(self, request, timeout: float):
        query = urllib.parse.parse_qs(request.data.decode())
        self.requests.append((query, dict(request.header_items())))
        if query.get("list") == ["allpages"]:
            titles = sorted([*self.pages, *self.redirects])
            prefix = query["apprefix"][0]
            body = {"query": {"allpages": [{"title": t} for t in titles if t.startswith(prefix)]}}
        else:
            asked = query["titles"][0].split("|")
            redirects = [{"from": t, "to": self.redirects[t]} for t in asked if t in self.redirects]
            found = {self.redirects.get(t, t) for t in asked}
            pages = [
                {"title": t, "revisions": [{"slots": {"main": {"content": self.pages[t]}}}]}
                if t in self.pages
                else {"title": t, "missing": True}
                for t in sorted(found)
            ]
            body = {"query": {"redirects": redirects, "pages": pages}}
        return _Response(json.dumps(body).encode())


class _Response:
    def __init__(self, data: bytes) -> None:
        self.data = data
        self.headers: dict[str, str] = {}

    def read(self) -> bytes:
        return self.data

    def __enter__(self):
        return self

    def __exit__(self, *exc) -> None:
        pass


def test_the_api_asks_for_wikitext_fifty_titles_at_a_time_following_redirects() -> None:
    titles = [f"Chess Opening Theory/1. e4/{i}" for i in range(120)]
    fake = FakeApi({t: f"text {t}" for t in titles[:3]}, {titles[3]: titles[0]})
    api = WikibooksApi("chessop/test (someone@example.org)", urlopen=fake, sleep=lambda s: None)
    found = api.fetch(titles)
    assert [len(q["titles"][0].split("|")) for q, _ in fake.requests] == [50, 50, 20]
    for query, headers in fake.requests:
        assert query["action"] == ["query"]
        assert query["prop"] == ["revisions"]
        assert query["redirects"] == ["1"]
        assert query["maxlag"] == ["5"]
        assert headers["User-agent"] == "chessop/test (someone@example.org)"
    assert found[titles[0]] == (titles[0], f"text {titles[0]}")
    assert found[titles[3]] == (titles[0], f"text {titles[0]}")
    assert titles[4] not in found


def test_the_api_lists_the_pages_and_redirects_of_chess_opening_theory() -> None:
    fake = FakeApi(
        {"Chess Opening Theory/1. e4": "x", "Other": "y"}, {"Chess Opening Theory/1. f3": "Other"}
    )
    api = WikibooksApi("ua", urlopen=fake, sleep=lambda s: None)
    assert api.titles() == {"Chess Opening Theory/1. e4", "Chess Opening Theory/1. f3"}


def test_the_api_waits_and_retries_on_maxlag() -> None:
    calls: list[str] = []
    waits: list[float] = []

    def urlopen(request, timeout: float):
        calls.append("x")
        if len(calls) == 1:
            response = _Response(json.dumps({"error": {"code": "maxlag"}}).encode())
            response.headers = {"Retry-After": "7"}
            return response
        return _Response(json.dumps({"query": {"pages": []}}).encode())

    api = WikibooksApi("ua", urlopen=urlopen, sleep=waits.append)
    assert api.fetch(["Chess Opening Theory/1. e4"]) == {}
    assert len(calls) == 2
    assert 7 in waits


def test_the_api_waits_and_retries_when_the_server_is_unavailable() -> None:
    calls: list[str] = []
    waits: list[float] = []

    def urlopen(request, timeout: float):
        calls.append("x")
        if len(calls) <= 2:
            code = 503 if len(calls) == 1 else 429
            headers = email.message.Message()
            headers["Retry-After"] = "11"
            raise urllib.error.HTTPError(request.full_url, code, "busy", headers, io.BytesIO())
        return _Response(json.dumps({"query": {"pages": []}}).encode())

    api = WikibooksApi("ua", urlopen=urlopen, sleep=waits.append)
    assert api.fetch(["Chess Opening Theory/1. e4"]) == {}
    assert len(calls) == 3
    assert waits.count(11) == 2


def test_the_api_gives_up_on_other_http_errors() -> None:
    def urlopen(request, timeout: float):
        raise urllib.error.HTTPError(request.full_url, 403, "no", email.message.Message(), None)

    api = WikibooksApi("ua", urlopen=urlopen, sleep=lambda s: None)
    with pytest.raises(urllib.error.HTTPError):
        api.fetch(["Chess Opening Theory/1. e4"])


# The explanation file


E4 = "Chess Opening Theory/1. e4"
E4_C5 = "Chess Opening Theory/1. e4/1...c5"
D4_NF6_NF3 = "Chess Opening Theory/1. d4/1...Nf6/2. Nf3"


def position(*sans: str, canonical: tuple[str, ...] | None = None, named: bool = False) -> Position:
    line = tuple(m.uci() for m in board_after(*sans).move_stack)
    return Position(
        epd=epd_after(*sans),
        count=100,
        name="x" if named else None,
        eco=None,
        canonical=line if canonical is None else canonical,
        book_line=line if named else None,
    )


def graph(*positions: Position) -> Graph:
    return Graph("v1", DEFAULT_BAND, 1000, {p.epd: p for p in positions})


def test_every_position_with_a_page_maps_to_it_and_each_page_is_stored_once() -> None:
    nf3_d4 = tuple(m.uci() for m in board_after("Nf3", "Nf6", "d4").move_stack)
    source = SavedPages(
        {E4: "== 1. e4 ==\nWhite takes the centre.", D4_NF6_NF3: "== x ==\nA Queen's pawn."},
        {"Chess Opening Theory/1. Nf3/1...Nf6/2. d4": D4_NF6_NF3},
    )
    graphs = {
        "a": graph(position(), position("e4"), position("e4", "c5")),
        "b": graph(position("e4"), position("d4", "Nf6", "Nf3", canonical=nf3_d4)),
    }
    file = build_explanations(graphs, "v1", source)
    assert file.version == "v1"
    assert [(p.title, p.lead) for p in file.pages] == [
        (D4_NF6_NF3, "A Queen's pawn."),
        (E4, "White takes the centre."),
    ]
    ids = {p.title: p.id for p in file.pages}
    assert file.positions == {
        epd_after("e4"): ids[E4],
        epd_after("d4", "Nf6", "Nf3"): ids[D4_NF6_NF3],
    }
    assert file.pages[1].url == "https://en.wikibooks.org/wiki/Chess_Opening_Theory/1._e4"


def test_the_books_own_line_is_tried_before_the_canonical_order() -> None:
    named = Position(
        epd=epd_after("d4", "Nf6", "Nf3"),
        count=100,
        name="Indian",
        eco=None,
        canonical=tuple(m.uci() for m in board_after("Nf3", "Nf6", "d4").move_stack),
        book_line=tuple(m.uci() for m in board_after("d4", "Nf6", "Nf3").move_stack),
    )
    source = SavedPages(
        {
            D4_NF6_NF3: "== x ==\nThe book's order.",
            "Chess Opening Theory/1. Nf3/1...Nf6/2. d4": "== x ==\nThe popular order.",
        }
    )
    file = build_explanations({"a": graph(named)}, "v1", source)
    [page] = [p for p in file.pages if p.id == file.positions[named.epd]]
    assert page.lead == "The book's order."


def test_a_page_without_prose_is_no_page() -> None:
    source = SavedPages({E4: "{{Chess Opening Theory/Position|x}}\n== 1. e4 ==\n{{ChessMid}}"})
    file = build_explanations({"a": graph(position("e4"))}, "v1", source)
    assert file.pages == [] and file.positions == {}


def test_the_file_carries_the_licence_notice_and_the_version(tmp_path: Path) -> None:
    source = SavedPages({E4_C5: SICILIAN})
    file = build_explanations({"a": graph(position("e4", "c5"))}, "v1", source)
    out = tmp_path / "x.explanations.json.gz"
    write_explanation_file(file, out)
    doc = json.loads(gzip.decompress(out.read_bytes()))
    assert doc["version"] == "v1"
    assert "CC BY-SA 4.0" in doc["licence"]["name"]
    assert doc["licence"]["url"] == "https://creativecommons.org/licenses/by-sa/4.0/"
    assert "trimmed" in doc["licence"]["notice"]
    [page] = doc["pages"]
    assert set(page) == {"id", "title", "url", "lead", "text"}
    assert doc["positions"] == {epd_after("e4", "c5"): page["id"]}


def test_the_explanation_file_is_what_the_server_loads(tmp_path: Path) -> None:
    from chessop.explanations import load_explanations

    source = SavedPages({E4_C5: SICILIAN})
    file = build_explanations({"a": graph(position("e4", "c5"))}, "v1", source)
    write_explanation_file(file, tmp_path / "x.json.gz")
    loaded = load_explanations(tmp_path / "x.json.gz")
    assert loaded.version == "v1"
    assert loaded.page_at(epd_after("e4", "c5")) == file.pages[0]


def test_saved_pages_read_the_ticket_14_pull(tmp_path: Path) -> None:
    source = SavedPages.read(REFS / "wikibooks-Chess_Opening_Theory-pages.json.gz")
    assert E4_C5 in source.titles()
    assert source.fetch([E4_C5, "Chess Opening Theory/1. e4/1...a5/2. a4"]) == {
        E4_C5: (E4_C5, source.pages[E4_C5])
    }
