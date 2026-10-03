"""The load-test script's own logic (public spec §7). The load test itself is run by hand
against a running server, never here."""

import importlib.util
import socket
import sys
from pathlib import Path
from types import ModuleType

import pytest

SCRIPT = Path(__file__).parent.parent / "scripts" / "loadtest.py"


@pytest.fixture(scope="module")
def loadtest() -> ModuleType:
    spec = importlib.util.spec_from_file_location("loadtest", SCRIPT)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules["loadtest"] = module
    spec.loader.exec_module(module)
    return module


@pytest.mark.skipif(not Path("/proc/net/tcp").exists(), reason="reads Linux's /proc")
def test_the_resident_memory_of_the_process_listening_on_a_local_target_is_read(
    loadtest: ModuleType,
) -> None:
    with socket.socket() as listener:
        listener.bind(("127.0.0.1", 0))
        listener.listen()
        port = listener.getsockname()[1]
        memory = loadtest.Memory.of(f"http://127.0.0.1:{port}/")
        assert memory is not None
        mine = int(
            next(
                line.split()[1]
                for line in Path("/proc/self/status").read_text().splitlines()
                if line.startswith("VmRSS:")
            )
        )
        assert memory.read() == pytest.approx(1024 * mine, rel=0.5)


def test_the_memory_of_a_remote_target_is_not_read(loadtest: ModuleType) -> None:
    assert loadtest.Memory.of("https://chessop.fr/") is None


def test_a_summary_gives_the_median_and_the_95th_percentile(loadtest: ModuleType) -> None:
    timings = [float(ms) for ms in range(1, 101)]  # 1 to 100 ms
    summary = loadtest.summary(timings)
    assert summary == {"count": 100, "p50": 50.0, "p95": 95.0, "max": 100.0}


def test_a_summary_of_nothing_says_so(loadtest: ModuleType) -> None:
    assert loadtest.summary([]) == {"count": 0, "p50": None, "p95": None, "max": None}
