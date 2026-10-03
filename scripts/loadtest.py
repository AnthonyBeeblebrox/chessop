"""The load test (public spec §7): N scripted learners play rounds over the socket of a running
hosted chessop, then the figures the pre-launch gate is judged on are printed.

    uv run scripts/loadtest.py http://127.0.0.1:8000/ --learners 30 --duration 60

Each scripted learner is a new anonymous learner: one socket with no cookie, playing rounds with
a think time before every move and every next round, as a person would. It learns the main moves
from the reveals that end rounds (every scripted learner shares what it learns), plays a main move
it has seen revealed, but one time in ten (and wherever it has seen none) a legal move at random.

Printed: the p50, p95 and max of the server's move handling (the `handled_ms` every `moved`
message carries: from the move's receipt to its replies ready, the round-end commit included)
and of the end-to-end reply time (from sending the move to receiving `moved`), and the server's
resident memory at the start and at its peak. `handled_ms` leaves out the time a move waits unread
while the event loop serves other learners (another round's commit); the end-to-end time, taken
on the server's machine, counts it, so the gate is judged on both lines there. The memory is read
from `/proc` when the target is on this machine (the process listening on its port) or when
`--pid` names the server.

The gate, run by hand before launch and after any change to the round-end path, never in CI:
server move handling under 10 ms at p95 with 30 learners playing (both lines, on the server's
machine), and resident memory under 1 GB at 300 sessions.

Each scripted learner sends its own `X-Forwarded-For` address (from 198.18.0.0/15, the range set
aside for benchmarks), which the server trusts from 127.0.0.1 only. Run on the server's machine
against its own port, every learner is then a client of its own, past the per-client limits
(30 new anonymous learners an hour, 40 open sockets). Through the reverse proxy every learner is
the one client: past 30 in an hour the rest are throwaway learners, which commit nothing, so the
script counts them. 300 sessions are measured on the server's machine.
"""

import argparse
import asyncio
import contextlib
import ipaddress
import json
import math
import os
import random
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit

from websockets.asyncio.client import ClientConnection, connect
from websockets.exceptions import ConnectionClosed, InvalidHandshake

from chessop.hosted import THROWAWAY

STRAY_RATE = 0.1  # how often a scripted learner plays a legal move at random, mains seen or not
SERVER_BUDGET_MS = 10.0  # p95 of the server's move handling, with 30 learners playing
MEMORY_BUDGET = 1024**3  # resident memory, at 300 sessions
BENCHMARK = ipaddress.ip_network("198.18.0.0/15")  # RFC 2544's addresses, one per learner


def summary(timings: list[float]) -> dict[str, float | int | None]:
    """The count, median, 95th percentile (nearest rank) and max of `timings`."""
    ordered = sorted(timings)
    count = len(ordered)

    def rank(p: float) -> float | None:
        return ordered[max(0, math.ceil(p * count) - 1)] if ordered else None

    return {
        "count": count,
        "p50": rank(0.50),
        "p95": rank(0.95),
        "max": ordered[-1] if ordered else None,
    }


@dataclass(frozen=True)
class Memory:
    """The resident memory of the server's process, `pid`, read from `/proc`."""

    pid: int

    @classmethod
    def of(cls, url: str, pid: int | None = None) -> "Memory | None":
        """The memory of `pid`, else of the process listening on `url`'s port when `url` is on
        this machine; None when there is no such process to read."""
        if pid is not None:
            return cls(pid)
        parts = urlsplit(url)
        host = parts.hostname or ""
        try:
            local = host == "localhost" or ipaddress.ip_address(host).is_loopback
        except ValueError:
            local = False
        if not local:
            return None
        port = parts.port or (443 if parts.scheme == "https" else 80)
        found = _listening(port)
        return None if found is None else cls(found)

    def read(self) -> int | None:
        """Its resident memory in bytes now, None when it cannot be read."""
        try:
            status = Path(f"/proc/{self.pid}/status").read_text()
        except OSError:
            return None
        for line in status.splitlines():
            if line.startswith("VmRSS:"):
                return 1024 * int(line.split()[1])
        return None


def _listening(port: int) -> int | None:
    """The process listening on TCP `port` on this machine, None when none can be found."""
    inodes = set()
    for table in ("/proc/net/tcp", "/proc/net/tcp6"):
        try:
            rows = Path(table).read_text().splitlines()[1:]
        except OSError:
            continue
        for row in rows:
            fields = row.split()
            if fields[3] == "0A" and int(fields[1].rsplit(":", 1)[1], 16) == port:  # LISTEN
                inodes.add(f"socket:[{fields[9]}]")
    if not inodes:
        return None
    for proc in Path("/proc").iterdir():
        if not proc.name.isdigit():
            continue
        with contextlib.suppress(OSError):
            for fd in (proc / "fd").iterdir():
                with contextlib.suppress(OSError):
                    if os.readlink(fd) in inodes:
                        return int(proc.name)
    return None


@dataclass
class Tally:
    """What the scripted learners measured and met."""

    server_ms: list[float] = field(default_factory=list)
    reply_ms: list[float] = field(default_factory=list)
    rounds: int = 0
    illegal: int = 0
    played: int = 0  # learners whose socket opened
    refused: int = 0  # learners whose socket was refused (limits, a full site)
    throwaway: int = 0  # learners told nothing they play is saved
    dropped: dict[int | None, int] = field(default_factory=dict)  # sockets closed early, by code
    live: int = 0
    peak_live: int = 0


def socket_url(url: str) -> str:
    """The play socket's address on the site at `url`."""
    parts = urlsplit(url)
    scheme = {"http": "ws", "https": "wss"}.get(parts.scheme, parts.scheme)
    return urlunsplit((scheme, parts.netloc, parts.path.rstrip("/") + "/ws", "", ""))


def epd(fen: str) -> str:
    """The position a FEN is written for: its first four fields."""
    return " ".join(fen.split()[:4])


def choose(position: dict, revealed: dict[str, list[str]], rng: random.Random) -> str:
    """The move a scripted learner plays at the `round` or `moved` message `position`: a main
    move it has seen `revealed`, but now and then (and where it has seen none) a legal move at
    random. Never the move set aside."""
    aside = (position.get("forced_uci") or "")[:4]
    mains = [uci for uci in revealed.get(epd(position["fen"]), ()) if uci[:4] != aside]
    if mains and rng.random() >= STRAY_RATE:
        return rng.choice(mains)
    legal = [frm + to for frm, tos in position["dests"].items() for to in tos]
    return rng.choice([uci for uci in legal if uci != aside] or legal)


async def learner(
    url: str,
    deadline: float,
    think: float,
    revealed: dict[str, list[str]],
    tally: Tally,
    rng: random.Random,
) -> None:
    """One scripted learner, playing rounds until `deadline` (`time.monotonic`)."""
    await asyncio.sleep(rng.uniform(0, think))  # not all at once
    address = str(BENCHMARK[rng.randrange(1, BENCHMARK.num_addresses - 1)])
    try:
        sock = await connect(
            socket_url(url), additional_headers={"X-Forwarded-For": address}, proxy=None
        )
    except (InvalidHandshake, OSError):
        tally.refused += 1
        return
    tally.played += 1
    tally.live += 1
    tally.peak_live = max(tally.peak_live, tally.live)
    try:
        await play(sock, deadline, think, revealed, tally, rng)
    except ConnectionClosed as e:
        code = None if e.rcvd is None else e.rcvd.code
        tally.dropped[code] = tally.dropped.get(code, 0) + 1
    finally:
        tally.live -= 1
        await sock.close()


async def play(
    sock: ClientConnection,
    deadline: float,
    think: float,
    revealed: dict[str, list[str]],
    tally: Tally,
    rng: random.Random,
) -> None:
    """Rounds on the open `sock` until `deadline`."""

    async def receive() -> dict:
        return json.loads(await sock.recv())

    def pause() -> float:
        return rng.uniform(0.5 * think, 1.5 * think)

    await sock.send(json.dumps({"type": "hello", "tz": "Europe/Paris"}))
    position = await receive()
    if position.get("notice") and THROWAWAY in position["notice"]:
        tally.throwaway += 1
    side = position["side"]
    while time.monotonic() < deadline:
        await asyncio.sleep(pause())
        uci = choose(position, revealed, rng)
        sent = time.perf_counter()
        await sock.send(json.dumps({"type": "move", "from": uci[:2], "to": uci[2:4]}))
        reply = await receive()
        if reply["type"] != "moved":
            tally.illegal += 1
            continue
        tally.reply_ms.append(1000 * (time.perf_counter() - sent))
        tally.server_ms.append(reply["handled_ms"])
        if reply["dests"]:
            position = reply
            continue
        round_over = await receive()
        tally.rounds += 1
        reveal = round_over["reveal"]
        if reveal["fen"].split()[1] == side[0]:  # the learner's own position: its main moves
            revealed[epd(reveal["fen"])] = [m["uci"] for m in reveal["main"]]
        if time.monotonic() >= deadline:
            break
        await asyncio.sleep(pause())
        await sock.send(json.dumps({"type": "next"}))
        position = await receive()
        side = position["side"]


async def watch(memory: Memory, samples: list[int]) -> None:
    """Read `memory` into `samples` every second until cancelled."""
    while True:
        rss = memory.read()
        if rss is not None:
            samples.append(rss)
        await asyncio.sleep(1.0)


async def run(args: argparse.Namespace) -> Tally:
    """The load test `args` ask for, its figures printed."""
    rng = random.Random(args.seed)
    revealed: dict[str, list[str]] = {}
    tally = Tally()
    memory = Memory.of(args.url, args.pid)
    samples: list[int] = []
    watching = asyncio.create_task(watch(memory, samples)) if memory is not None else None
    deadline = time.monotonic() + args.duration
    learners = [
        learner(args.url, deadline, args.think, revealed, tally, random.Random(rng.random()))
        for _ in range(args.learners)
    ]
    await asyncio.wait_for(asyncio.gather(*learners), args.duration + 10 * args.think + 30)
    if watching is not None:
        watching.cancel()
    report(args, tally, memory, samples)
    return tally


def report(
    args: argparse.Namespace, tally: Tally, memory: Memory | None, samples: list[int]
) -> None:
    """Print the figures the gate is judged on."""

    def ms(figures: dict[str, float | int | None]) -> str:
        if not figures["count"]:
            return "no moves"
        return ", ".join(f"{k} {figures[k]:.1f} ms" for k in ("p50", "p95", "max"))

    def mb(size: int) -> str:
        return f"{size / 1024**2:.0f} MB"

    dropped = ", ".join(f"{n} (code {code})" for code, n in tally.dropped.items()) or "0"
    print(f"chessop load test: {args.learners} learners for {args.duration:g} s on {args.url}")
    print(
        f"learners: {tally.played} played (at most {tally.peak_live} at once),"
        f" {tally.refused} refused, {tally.throwaway} throwaway, dropped {dropped}"
    )
    print(f"rounds: {tally.rounds}, moves: {len(tally.server_ms)}, illegal: {tally.illegal}")
    print(
        f"server move handling: {ms(summary(tally.server_ms))}"
        f"  (budget: p95 under {SERVER_BUDGET_MS:g} ms with 30 learners)"
    )
    print(
        f"end-to-end reply:     {ms(summary(tally.reply_ms))}"
        "  (counts waiting behind other learners: on the server's machine, the same budget)"
    )
    if memory is None or not samples:
        print("resident memory: not read (run on the server's machine, or pass --pid)")
    else:
        print(
            f"resident memory: {mb(samples[0])} at the start, {mb(max(samples))} at its peak"
            f"  (budget: under {mb(MEMORY_BUDGET)} at 300 sessions; pid {memory.pid})"
        )
    if tally.throwaway:
        print(
            "warning: throwaway learners commit nothing; run on the server's machine against"
            " its own port for every learner to be saved",
            file=sys.stderr,
        )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """The target, the learner count, the duration and the rest, from the command line."""
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("url", help="the hosted site, e.g. http://127.0.0.1:8000/")
    parser.add_argument("--learners", "-n", type=int, default=30, help="default 30")
    parser.add_argument(
        "--duration", "-d", type=float, default=60.0, help="seconds of play (default 60)"
    )
    parser.add_argument(
        "--think",
        type=float,
        default=2.0,
        help="mean seconds before a move or a next round, drawn from half to one and a half"
        " times it (default 2)",
    )
    parser.add_argument("--pid", type=int, help="the server's process, to read its memory")
    parser.add_argument("--seed", type=int, help="for a repeatable run")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    """Run the load test; the exit status is 1 when no move was measured."""
    tally = asyncio.run(run(parse_args(argv)))
    return 0 if tally.server_ms else 1  # nothing measured: say so with the exit status


if __name__ == "__main__":
    sys.exit(main())
