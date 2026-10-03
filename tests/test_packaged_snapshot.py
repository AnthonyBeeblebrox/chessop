"""The snapshot shipped inside the package (spec §3.3, §4, §14)."""

import pytest

from chessop.build import repertoire_size
from chessop.cli import explanations_for
from chessop.graph import BANDS, DEFAULT_BAND, PACKAGED_SNAPSHOT, Graph, load_graph
from chessop.repertoire import Repertoire, Settings


def test_the_packaged_graph_holds_every_band() -> None:
    graph = load_graph(PACKAGED_SNAPSHOT, DEFAULT_BAND)
    assert graph.bands == tuple(name for name, _, _ in BANDS)


def test_the_packaged_graph_and_explanation_files_share_one_version() -> None:
    graph = load_graph(PACKAGED_SNAPSHOT, "1500-1800")
    month = graph.version.split("/")[0]
    assert month >= "2026-08"
    explanations = explanations_for(PACKAGED_SNAPSHOT, graph.version)
    assert explanations is not None and explanations.version == graph.version
    assert explanations.pages and explanations.positions


@pytest.mark.slow
def test_the_packaged_1800_2100_band_is_the_size_spec_4_expects() -> None:
    """Spec §4, 1800-2100 at the defaults on the 2026-08 snapshot with no named-position prune
    (ticket 24): about 3,074 positions, 3,432 edges, 1,052 leaves, 21 plies deep, 22 % of
    positions exactly named, no stubs. Sanity bounds, not exact targets."""
    graph = load_graph(PACKAGED_SNAPSHOT, "1800-2100")
    size = repertoire_size(graph)
    assert 2_500 <= size["positions"] <= 3_700
    assert 2_800 <= size["edges"] <= 4_100
    assert 800 <= size["leaves"] <= 1_300
    assert 18 <= size["max_depth"] <= 24
    assert 0.15 <= size["book_lines_covered"] / size["positions"] <= 0.30
    assert stubs(graph) == 0


@pytest.mark.slow
def test_the_packaged_1500_1800_band_is_the_size_spec_4_expects() -> None:
    """Spec §4, 1500-1800 at the defaults: about 2,695 positions, 3,030 edges, 1,043 leaves,
    17 plies deep. Sanity bounds, not exact targets."""
    graph = load_graph(PACKAGED_SNAPSHOT, "1500-1800")
    size = repertoire_size(graph)
    assert 2_200 <= size["positions"] <= 3_200
    assert 2_500 <= size["edges"] <= 3_600
    assert 800 <= size["leaves"] <= 1_300
    assert 15 <= size["max_depth"] <= 20
    assert stubs(graph) == 0


def stubs(graph: Graph) -> int:
    repertoire = Repertoire(graph, Settings(band=graph.band))
    return sum(
        repertoire.is_stub(e) for p in repertoire.positions for e in repertoire.main_moves(p)
    )
