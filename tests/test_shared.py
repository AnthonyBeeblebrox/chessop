"""What learners share in the process (public spec §4): band graphs, and the repertoire, ledger
and repertoire-only steering caches of each settings key, built off the event loop. The cache is
driven as a learner session drives it; the hosted site as browsers do."""

import asyncio
import threading
from dataclasses import replace
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from chessop.graph import DEFAULT_BAND, Graph
from chessop.repertoire import START, Settings
from chessop.shared import SIZE, EmptyRepertoire, Shared, SharedCache
from test_hosted import Site, hosted_form, open_socket
from test_wire import E4_E5, play

OTHER_BAND = "1500-1800"
E4_E5_OTHER = replace(E4_E5, band=OTHER_BAND)


def key(n: int) -> Settings:
    """The `n`th of some distinct settings keys; the one numbered 0 is the default."""
    return Settings(width_opponent=3 + n)


def get(cache: SharedCache, settings: Settings) -> Shared:
    """What `settings` share, as a running process asks for it."""
    return asyncio.run(cache.get(settings))


def test_learners_with_the_same_settings_share_one_repertoire_and_steering_caches() -> None:
    cache = SharedCache(E4_E5, None)
    mine = get(cache, Settings(opted_out=frozenset({"Sicilian Defense"})))
    yours = get(cache, Settings(opted_out=frozenset({"Sicilian Defense"})))
    assert yours is mine
    assert mine.reach.repertoire is mine.repertoire
    assert START in mine.repertoire.positions


def test_a_learner_with_different_settings_gets_their_own() -> None:
    cache = SharedCache(E4_E5, None)
    mine = cache.warm(Settings())
    for other in (
        Settings(width_player=1),
        Settings(width_opponent=4),
        Settings(popularity_floor=0.001),
        Settings(share=0.1),
        Settings(opted_out=frozenset({"Sicilian Defense"})),
    ):
        theirs = get(cache, other)
        assert theirs is not mine
        assert theirs.repertoire is not mine.repertoire and theirs.reach is not mine.reach
        assert theirs.repertoire.settings == other


def test_the_17th_distinct_settings_key_evicts_the_least_recently_used() -> None:
    assert SIZE == 16
    cache = SharedCache(E4_E5, None)
    built = [get(cache, key(n)) for n in range(16)]
    assert cache.ready(key(0)) is built[0]  # used again: key 1 is now the least recently used
    get(cache, key(16))
    assert cache.ready(key(1)) is None
    assert all(cache.ready(key(n)) is built[n] for n in (0, *range(2, 16)))


def test_the_key_warmed_at_the_start_is_never_the_one_evicted() -> None:
    cache = SharedCache(E4_E5, None)
    default = cache.warm(Settings())
    built = {n: get(cache, key(n)) for n in range(1, 17)}
    assert cache.ready(Settings()) is default
    assert cache.ready(key(1)) is None
    assert all(cache.ready(key(n)) is built[n] for n in range(2, 17))


def test_an_opted_out_key_lists_the_same_ledger_as_the_key_with_nothing_opted_out() -> None:
    cache = SharedCache(E4_E5, None)
    everything = get(cache, Settings())
    narrowed = get(cache, Settings(width_player=1, opted_out=frozenset({"Sicilian Defense"})))
    assert get(cache, Settings(opted_out=frozenset({"Sicilian Defense"}))).ledger is (
        everything.ledger
    )
    assert narrowed.ledger.repertoire.settings == Settings(width_player=1)


def test_settings_that_leave_nothing_to_drill_are_refused_and_not_kept() -> None:
    cache = SharedCache(E4_E5, None)
    nothing = Settings(popularity_floor=1.0)
    with pytest.raises(EmptyRepertoire):
        get(cache, nothing)
    assert cache.ready(nothing) is None


def test_a_band_graph_loads_on_first_use_and_stays() -> None:
    loaded: list[str] = []

    def load_band(band: str) -> Graph:
        loaded.append(band)
        return E4_E5_OTHER

    cache = SharedCache(E4_E5, load_band)
    first = get(cache, Settings(band=OTHER_BAND))
    second = get(cache, Settings(band=OTHER_BAND, width_player=1))
    assert loaded == [OTHER_BAND]
    assert first.repertoire.graph is second.repertoire.graph is E4_E5_OTHER
    assert get(cache, Settings()).repertoire.graph is E4_E5


def test_a_band_the_snapshot_lacks_falls_back_to_the_default() -> None:
    def load_band(band: str) -> Graph:
        raise KeyError(band)

    shared = SharedCache(E4_E5, load_band).warm(Settings(band="2100+"))
    assert shared.repertoire.graph is E4_E5
    assert shared.repertoire.settings.band == DEFAULT_BAND


class Bands:
    """A snapshot whose other band takes as long to load as the test says: `asked` is set
    when its load begins, which then waits for `release`."""

    def __init__(self) -> None:
        self.asked, self.release = threading.Event(), threading.Event()
        self.loads = 0
        self.released: bool | None = None  # whether the load ended by being released

    def __call__(self, band: str) -> Graph:
        self.loads += 1
        self.asked.set()
        self.released = self.release.wait(5)
        return E4_E5_OTHER


def with_bands(tmp_path: Path, bands: Bands) -> Site:
    return Site(tmp_path, graph=replace(E4_E5, bands=(DEFAULT_BAND, OTHER_BAND)), load_band=bands)


def test_the_default_settings_key_is_warm_once_the_hosted_site_has_started(tmp_path: Path) -> None:
    bands = Bands()
    site = with_bands(tmp_path, bands)
    assert site.app.state.shared.ready(Settings()) is not None
    with site.browser() as browser:
        ws = open_socket(browser)
        try:
            start = ws.receive_json()
            assert play(ws, "e2e4" if start["side"] == "white" else "e7e5")
        finally:
            ws.__exit__(None, None, None)
    assert bands.loads == 0


def test_while_another_band_builds_another_learners_moves_are_still_answered(
    tmp_path: Path,
) -> None:
    bands = Bands()
    site = with_bands(tmp_path, bands)
    saved: list[int] = []

    def save(browser: TestClient) -> None:
        response = browser.post(
            "/settings", data=hosted_form(band=OTHER_BAND), follow_redirects=False
        )
        saved.append(response.status_code)

    with site.browser() as browser:  # one event loop serves both learners
        ws = open_socket(browser)
        try:
            start = ws.receive_json()
            other = TestClient(site.app, base_url=site.url, client=("203.0.113.8", 50000))
            other.portal = browser.portal  # the same event loop
            saving = threading.Thread(target=save, args=(other,))
            saving.start()
            assert bands.asked.wait(5)
            moved, _ = play(ws, "e2e4" if start["side"] == "white" else "e7e5")
            assert moved["verdict"] == "pass"
            bands.release.set()
            saving.join(5)
        finally:
            bands.release.set()
            ws.__exit__(None, None, None)
    assert bands.released is True  # the move was answered while the band was still loading
    assert saved == [303]


def test_two_hosted_learners_choosing_a_band_load_its_graph_once(tmp_path: Path) -> None:
    bands = Bands()
    bands.release.set()
    site = with_bands(tmp_path, bands)
    for ip in ("203.0.113.7", "203.0.113.8"):
        with site.browser(ip) as browser:
            saved = browser.post(
                "/settings", data=hosted_form(band=OTHER_BAND), follow_redirects=False
            )
            assert saved.status_code == 303
            assert f'<option value="{OTHER_BAND}" selected>' in browser.get("/settings").text
    assert bands.loads == 1
