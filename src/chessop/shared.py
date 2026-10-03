"""What the learners of one process share (public spec §4, ADR 0004).

**Band graphs** load on first use and stay for the process's life. The repertoire, the progress
ledger and the repertoire-only steering caches depend only on the **settings key** (band, widths,
popularity floor, share, opted-out openings: a `Settings`), so every learner with the same key
shares one `Shared`, kept least-recently-used, `SIZE` keys at most. A learner session
(`chessop.session`) holds the one it drills over, evicted or not.

A build is slow (a band's graph parsed, its ledger shaped), so a running process builds in a
worker thread (`get`): the event loop goes on answering every other learner's moves meanwhile.
Only a start builds on its own thread (`warm`): what it builds, the default key in hosted
mode, is never the one evicted, so a learner on it never waits on a build.
"""

import asyncio
import threading
from collections import OrderedDict
from collections.abc import Callable
from dataclasses import dataclass, replace

from chessop.graph import Graph
from chessop.progress import Ledger
from chessop.repertoire import START, Repertoire, Settings
from chessop.steering import Reach

SIZE = 16  # settings keys kept; past it the least recently used goes


class EmptyRepertoire(ValueError):
    """The settings leave nothing in scope to drill."""

    def __init__(self) -> None:
        super().__init__("the repertoire is empty: nothing in scope to drill")


@dataclass(frozen=True)
class Shared:
    """What every learner with one settings key drills over. The ledger is over the repertoire
    with nothing opted out: opted-out openings stay listed."""

    repertoire: Repertoire
    reach: Reach
    ledger: Ledger


class SharedCache:
    """The band graphs of one snapshot and the `Shared` of each settings key in use.

    `graph` is the band the process started on, the one a band the snapshot lacks falls back to
    (public spec §2); `load_band` loads another, and without it there is no other. Everything
    but the build inside `get` runs on the event loop's thread."""

    def __init__(self, graph: Graph, load_band: Callable[[str], Graph] | None) -> None:
        self._fallback = graph
        self._load_band = load_band
        self._warmed: set[Settings] = set()  # never evicted
        self._graphs = {graph.band: graph}
        self._loading = threading.Lock()  # a band is loaded once, whichever thread asks first
        self._kept: OrderedDict[Settings, Shared] = OrderedDict()  # least recently used first
        self._building: dict[Settings, asyncio.Future[Shared]] = {}

    def ready(self, settings: Settings) -> Shared | None:
        """What is kept for `settings`, counted as used; None when nothing is."""
        shared = self._kept.get(settings)
        if shared is not None:
            self._kept.move_to_end(settings)
        return shared

    def warm(self, settings: Settings) -> Shared:
        """What `settings` share, built here and now when it is not kept, and kept for the
        process's life: for a start, before any learner plays. `EmptyRepertoire` when they
        leave nothing to drill."""
        shared = self.ready(settings)
        if shared is None:
            shared = self._keep(settings, self._build(settings, self._listed(settings)))
        self._warmed.add(settings)
        return shared

    async def get(self, settings: Settings) -> Shared:
        """What `settings` share, built in a worker thread when it is not kept; learners asking
        for one key while it builds wait on the one build. `EmptyRepertoire` when they leave
        nothing to drill."""
        shared = self.ready(settings)
        if shared is not None:
            return shared
        building = self._building.get(settings)
        if building is None:
            building = asyncio.ensure_future(
                asyncio.to_thread(self._build, settings, self._listed(settings))
            )
            self._building[settings] = building
            building.add_done_callback(lambda built: self._built(settings, built))
        # Shielded: one learner giving up does not stop the build the others wait on.
        return await asyncio.shield(building)

    def _built(self, settings: Settings, built: asyncio.Future[Shared]) -> None:
        del self._building[settings]
        if not built.cancelled() and built.exception() is None:
            self._keep(settings, built.result())

    def _keep(self, settings: Settings, shared: Shared) -> Shared:
        self._kept[settings] = shared
        self._kept.move_to_end(settings)
        if len(self._kept) > SIZE:
            del self._kept[next(key for key in self._kept if key not in self._warmed)]
        return shared

    def _listed(self, settings: Settings) -> Ledger | None:
        """The ledger `settings` list when it is already kept: that of the same settings with
        nothing opted out."""
        everything = self._kept.get(replace(settings, opted_out=frozenset()))
        return None if everything is None else everything.ledger

    def _build(self, settings: Settings, ledger: Ledger | None) -> Shared:
        """On whichever thread: nothing here touches what is kept."""
        graph = self._graph(settings.band)
        settings = replace(settings, band=graph.band)
        repertoire = Repertoire(graph, settings)
        if START not in repertoire.positions or repertoire.is_leaf(START):
            raise EmptyRepertoire
        if ledger is None:
            everything = replace(settings, opted_out=frozenset())
            ledger = Ledger(Repertoire(graph, everything) if settings.opted_out else repertoire)
        return Shared(repertoire, Reach(repertoire), ledger)

    def _graph(self, band: str) -> Graph:
        """The graph of `band`, loaded when it is first asked for; the fallback when the
        snapshot holds none for it."""
        with self._loading:
            if band not in self._graphs:
                if self._load_band is None:
                    return self._fallback
                try:
                    self._graphs[band] = self._load_band(band)
                except KeyError:
                    return self._fallback
            return self._graphs[band]
