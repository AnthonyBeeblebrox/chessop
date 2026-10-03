"""The help page and the links to it from progress and play (public spec §9), through the app."""

import re
import time
from datetime import date

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import Graph
from chessop.memory import Params
from chessop.store import Store
from test_progress import commit, page
from test_settings import valid_form

# Each section's heading and anchor, in the page's order (public spec §9).
SECTIONS = [
    ("round", "How a round works"),
    ("verdict", "The verdict under the board"),
    ("forced", "“Not Nf3 this time”"),
    ("score", "Score"),
    ("since", "Change since your last day"),
    ("sides", "As White and as Black"),
    ("counts", "Known, learning, never passed"),
    ("session", "This session"),
    ("spark", "The line"),
    ("openings", "Openings"),
    ("colours", "Move colours"),
    ("band", "Rating band"),
]


def test_the_help_page_lists_every_section_then_holds_each_under_its_anchor(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph)) as client:
        response = client.get("/help")
    assert response.status_code == 200
    assert "<title>How chessop works</title>" in response.text
    assert "<h1>How chessop works</h1>" in response.text
    toc = re.findall(r'<li><a href="#([a-z]+)">([^<]+)</a></li>', response.text)
    assert toc == [(anchor, title) for anchor, title in SECTIONS]
    sections = re.findall(r'<section id="([a-z]+)">\s*<h2>([^<]+)</h2>', response.text)
    assert sections == SECTIONS


def section(page: str, anchor: str) -> str:
    """The text of the section under `anchor`."""
    found = re.search(rf'<section id="{anchor}">(.*?)</section>', page, re.S)
    assert found, anchor
    return found.group(1)


def test_the_known_section_quotes_the_running_sure_threshold_and_follows_a_change_of_it(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph, params=Params(sure=0.85))) as client:
        assert "85 % or more" in section(client.get("/help").text, "counts")
        saved = client.post("/settings", data=valid_form(band=graph.band, sure="0.8"))
        assert saved.status_code == 200  # after the redirect
        counts = section(client.get("/help").text, "counts")
    assert "80 % or more" in counts
    assert "85 %" not in counts


def test_the_session_section_quotes_the_target_range(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        assert "About 80\N{EN DASH}90 %" in section(client.get("/help").text, "session")


def help_links(page: str) -> list[tuple[str, str]]:
    """Each link into the help page: its anchor and its text, tags stripped, in page order."""
    return [
        (anchor, re.sub(r"<[^>]+>", "", text).strip())
        for anchor, text in re.findall(r'<a class="hl[^"]*" href="/help#([a-z]+)">(.*?)</a>', page)
    ]


def test_each_figure_label_on_the_progress_view_links_to_its_help_section() -> None:
    store = Store.in_memory()
    yesterday = time.time() - 86_400
    commit(store, "success", yesterday, score=0.25)  # a last day: the change since, the line
    links = help_links(page(store))
    assert links == [
        ("score", "Score"),
        ("since", f"-25.0 since {date.fromtimestamp(yesterday).isoformat()}"),
        ("sides", "as White"),
        ("sides", "as Black"),
        ("counts", "known / learning / never passed"),
        ("session", "this session"),
        ("spark", "daily"),
        ("openings", "Opening"),
        ("colours", "colours"),
    ]
    anchors = {anchor for anchor, _ in SECTIONS}
    assert {anchor for anchor, _ in links} <= anchors


def test_the_play_page_has_help_in_its_corner_and_two_links_under_the_verdict(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph)) as client:
        text = client.get("/").text
    corner = re.search(r'<nav class="links">(.*?)</nav>', text, re.S)
    assert corner and '<a href="/help">help</a>' in corner.group(1)
    under = text[text.index('id="verdict"') :]
    line = re.search(r'<p class="verdict-help" id="verdict-help" hidden>(.*?)</p>', under, re.S)
    assert line, "the post-round line, hidden until a round ends"
    assert re.findall(r'<a href="/help#([a-z]+)">([^<]+)</a>', line.group(1)) == [
        ("verdict", "what does this mean?"),
        ("score", "what is the Score?"),
    ]


# The glossary's Avoid words a reader could meet in help copy (CONTEXT.md), as whole words.
# Left out: those the copy rightly uses in another sense: player and game (Lichess players and
# their games), session and line (the figures "this session" and "the line"), rating (of players).
AVOID = (
    "user",
    "profile",
    "login",
    "sync",
    "import",
    "engine",
    "computer",
    "bot",
    "grind",
    "train",
    "practise",
    "study",
    "attempt",
    "mastered",
    "learned",
    "memorised",
    "retention",
    "strength",
    "knowledge",
    "level",
    "Elo",
    "pool",
    "epsilon",
    "hit",
    "failure",
    "error",
    "mistake",
    "priority",
    "weakness",
    "theory",
    "commentary",
    "dashboard",
    "best move",
    "book move",
    "acceptable move",
    "node",
    "variation",
)


def test_the_help_copy_says_none_of_the_glossary_avoid_words(graph: Graph) -> None:
    with TestClient(create_app(graph)) as client:
        text = client.get("/help").text
    main = text[text.index("<main") :]
    words = re.sub(r"<[^>]+>", " ", main)
    said = [w for w in AVOID if re.search(rf"\b{w}s?\b", words, re.I)]
    assert said == []
