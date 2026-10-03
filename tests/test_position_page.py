import re
import time
from urllib.parse import quote

import pytest
from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.explanations import Explanations, Page
from chessop.memory import DAY, Verdict
from chessop.repertoire import START
from chessop.score import Scores
from chessop.store import RoundEnd, Store
from graphs import epd_after, graph_of
from test_progress import NAMES, SICILIAN


def remember(store: Store, epd: str, *verdicts: tuple[Verdict, float]) -> None:
    """Commit one round per verdict at `epd`, in order."""
    for verdict, at in verdicts:
        store.implicit().commit(
            RoundEnd(
                started_at=at - 5,
                ended_at=at,
                side="white",
                path=[],
                outcome="miss" if verdict == "miss" else "success",
                end_epd=epd,
                verdicts={epd: (verdict, at)},
                before={},
                snapshot_version="test",
            ),
            lambda record: Scores(0.0, 0.0, 0.0),
        )


def position_page(
    epd: str, store: Store | None = None, explanations: Explanations | None = None
) -> str:
    graph = graph_of(SICILIAN, NAMES)
    with TestClient(
        create_app(graph, store=store or Store.in_memory(), explanations=explanations)
    ) as client:
        response = client.get(f"/progress/position/{quote(epd, safe='')}")
    assert response.status_code == 200
    return response.text


def state(text: str) -> str:
    found = re.search(r'<b class="state [a-z]+">([^<]+)</b>', text)
    assert found is not None
    return found.group(1)


E4_C5 = epd_after("e4", "c5")  # White to move, a learner position of the Sicilian


@pytest.mark.parametrize(
    ("verdicts", "word"),
    [
        ((), "never passed"),
        ((("counted", 0.0),), "known"),  # just passed, h = 2 days
        ((("counted", -1 * DAY),), "learning"),  # R = 2^-0.5 ~ 0.71
        ((("counted", -5 * DAY),), "fading"),  # R = 2^-2.5 ~ 0.18
        ((("counted", -1 * DAY), ("miss", -DAY / 2)), "relearning"),  # R = 0.5, owed
        ((("miss", -DAY),), "relearning"),  # missed before any pass: owed all the same
    ],
)
def test_the_state_word_follows_the_recall_estimate_and_the_relearning_mark(
    verdicts: tuple[tuple[Verdict, float], ...], word: str
) -> None:
    store = Store.in_memory()
    now = time.time()
    remember(store, E4_C5, *((v, now + at) for v, at in verdicts))
    assert state(position_page(E4_C5, store)) == word


def test_the_page_is_server_rendered_with_the_board_from_the_learners_side() -> None:
    white = position_page(E4_C5)
    black = position_page(epd_after("e4", "c5", "Nf3"))
    assert "<script" not in white
    assert "<svg" in white
    assert a1_corner(white) == "bottom left"
    assert a1_corner(black) == "top right"


def a1_corner(text: str) -> str:
    """Where the board drawn on the page puts the square a1."""
    found = re.search(r'<rect x="(\d+)" y="(\d+)"[^>]*class="square \w+ a1"', text)
    assert found is not None
    x, y = int(found.group(1)), int(found.group(2))
    return f"{'bottom' if y > 100 else 'top'} {'left' if x < 100 else 'right'}"


def test_an_unknown_position_is_not_found() -> None:
    graph = graph_of(SICILIAN, NAMES)
    with TestClient(create_app(graph)) as client:
        epd = epd_after("h4")
        assert client.get(f"/progress/position/{quote(epd, safe='')}").status_code == 404


def heading(text: str) -> str:
    h1 = text[text.index("<h1>") : text.index("</h1>")]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", "", h1)).strip()


def test_a_position_not_named_itself_is_marked_inherited() -> None:
    # 1.e4 c5 2.Nf3 is unnamed: it takes the Sicilian Defense from 1.e4 c5.
    assert heading(position_page(epd_after("e4", "c5", "Nf3"))) == (
        "black to move Sicilian Defense (inherited)"
    )
    assert heading(position_page(E4_C5)) == "white to move Sicilian Defense"
    assert "1.e4 c5 2.Nf3</p>" in position_page(epd_after("e4", "c5", "Nf3"))


def text_page(page_id: int, lead: str, text: str) -> Page:
    title = f"Chess Opening Theory/{page_id}"
    return Page(page_id, title, f"https://en.wikibooks.org/wiki/{title}", lead, text)


def explained(**pages: Page) -> Explanations:
    """Explanations at the positions after the SAN lines given as keywords (`e4_c5=...`)."""
    return Explanations(
        "test",
        list(pages.values()),
        {epd_after(*line.split("_")): p.id for line, p in pages.items()},
    )


def test_a_position_with_its_own_page_shows_its_lead_more_and_the_licence() -> None:
    sicilian = text_page(1, "The Sicilian.", "The Sicilian.\n\nBlack fights for d4.")
    text = position_page(E4_C5, explanations=explained(e4_c5=sicilian))
    section = text[text.index('<section class="explanation">') :]
    assert "No text of its own" not in section
    assert "<p>The Sicilian.</p>" in section
    assert '<summary class="more">more</summary>' in section
    assert "<p>Black fights for d4.</p>" in section
    assert f'href="{sicilian.url}"' in section
    assert "CC BY-SA 4.0 · trimmed" in section


def test_a_position_without_a_page_borrows_the_nearest_along_its_canonical_order() -> None:
    # 1.e4 c5 2.Nf3 d6 has no page; 1.e4 c5 has, and 1.e4 too (further back).
    pages = explained(
        e4=text_page(1, "King's pawn.", "King's pawn."), e4_c5=text_page(2, "S.", "S.")
    )
    text = position_page(epd_after("e4", "c5", "Nf3", "d6"), explanations=pages)
    assert "No text of its own: the text for 1.e4 c5</p>" in text
    assert "<p>S.</p>" in text
    assert "<summary" not in text  # nothing more than the lead


def test_the_start_has_no_explanation_to_borrow() -> None:
    pages = explained(e4=text_page(1, "King's pawn.", "King's pawn."))
    assert 'class="explanation"' not in position_page(START, explanations=pages)


def chips(text: str) -> list[str]:
    """The main-move chips as `san:shade`, `san:stub` for a stub."""
    found = re.findall(r'class="mv chip ([a-z]+)"[^>]*>([^ <]+)', text)
    return [f"{san}:{kind}" for kind, san in found]


def test_main_moves_are_chips_coloured_by_the_childs_recall_with_stubs_marked() -> None:
    graph_counts = {**SICILIAN, "e4 c5 c3": 700}  # 2.c3 stored nowhere below: a stub
    store = Store.in_memory()
    now = time.time()
    remember(store, epd_after("e4", "c5", "Nf3"), ("counted", now))  # the child is known
    with TestClient(
        create_app(graph_of(graph_counts, NAMES, unstored=frozenset({"e4 c5 c3"})), store=store)
    ) as client:
        text = client.get(f"/progress/position/{quote(E4_C5, safe='')}").text
    # 2.Nc3 leads to a position never passed.
    assert chips(text) == ["Nf3:known", "Nc3:never", "c3:stub"]
    assert f'href="/progress/position/{quote(epd_after("e4", "c5", "Nf3"), safe="")}"' in text


def test_the_numbers_count_the_share_of_games_and_the_move_orders() -> None:
    # 1.d4 Nf6 2.c4 e6 is reached by two orders; the band has 10,000 games.
    graph = graph_of(
        {
            "d4": 5000,
            "c4": 2000,
            "d4 Nf6": 4000,
            "c4 e6": 1000,
            "d4 Nf6 c4": 3000,
            "c4 e6 d4": 500,
            "d4 Nf6 c4 e6": 2500,
            "c4 e6 d4 Nf6": 400,
            "d4 Nf6 c4 e6 Nc3": 1500,
            "d4 Nf6 c4 e6 Nc3 Bb4": 1000,
        },
        {"d4 Nf6 c4 e6 Nc3 Bb4": "Nimzo-Indian Defense"},
    )
    store = Store.in_memory()
    epd = epd_after("d4", "Nf6", "c4", "e6")
    now = time.time()
    remember(store, epd, ("counted", now - 2 * DAY), ("miss", now - DAY))
    with TestClient(create_app(graph, store=store)) as client:
        text = client.get(f"/progress/position/{quote(epd, safe='')}").text
    flat = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", text))
    assert "25.00 % of the band's games · 2 move orders" in flat
    assert "counted passes / misses 1 / 1 (relearning pass owed)" in flat
    assert "half-life 24 h" in flat  # h0 * 2^(1 - 1)
    assert "recall estimate 25.0 %" in flat  # two days at a day's half-life
    assert "last pass 2.0 days ago" in flat


def test_the_start_and_positions_with_nothing_named_before_them_are_not_marked_inherited() -> None:
    assert heading(position_page(START)) == "white to move Start position"
    assert heading(position_page(epd_after("d4"))) == "black to move First moves (no name)"
