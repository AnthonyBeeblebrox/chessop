"""The play page's touch controls for the phone layout (public spec §8), through the app.

The layout itself (Stacked below about 40em, the landscape split) is CSS, verified by hand
against `prototype/mobile`; these tests hold the controls the page must carry for it.
"""

import re

from fastapi.testclient import TestClient

from chessop.app import create_app
from chessop.graph import Graph


def icons(page: str) -> str:
    """The header's icon buttons."""
    found = re.search(r'<span class="icons">(.*?)</span>\s*</div>', page, re.S)
    assert found, "the header's icon buttons"
    return found.group(1)


def test_the_header_has_a_sound_icon_showing_the_persisted_sound_then_progress_and_settings(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph)) as client:
        on = icons(client.get("/").text)
        with client.websocket_connect("/ws") as ws:
            ws.receive_json()
            ws.send_json({"type": "sound", "on": False})
        off = icons(client.get("/").text)
    sound = '<button type="button" class="icon" id="sound" aria-label="sound" aria-pressed="{}">{}'
    assert sound.format("true", "🔊</button>") in on
    assert sound.format("false", "🔇</button>") in off
    for icons_html in (on, off):
        links = re.findall(r'<a class="icon" href="([^"]+)" aria-label="([a-z]+)">', icons_html)
        assert links == [("/progress", "progress"), ("/settings", "settings")]


def test_the_next_round_button_follows_the_verdict_and_is_hidden_until_the_round_ends(
    graph: Graph,
) -> None:
    with TestClient(create_app(graph)) as client:
        page = client.get("/").text
    button = '<button type="button" class="next" id="next" hidden>Next round</button>'
    assert button in page
    assert page.index('id="verdict"') < page.index(button) < page.index('id="explanation"')
