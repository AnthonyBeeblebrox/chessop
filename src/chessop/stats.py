"""`chessop stats` (public spec §12): the owner's tables of how much the site is used, read from
the database. No admin page shows them.

Past days come from the daily usage aggregate (`Store.usage_days`), its last 30 rows, the derived
counts of a day only once they are written. The rest is computed live over the learners that
remain: active learners per week and per month (the aggregate keeps no learner id to count a
week's distinct learners from its days'), the retention of each week's new learners, and the
band, opening and snapshot choices of the learners active in the last 30 days. Every day is a
UTC day and every week begins on a Monday. A learner is active over a span when they logged at
least one round in it; one with an account now counts as signed in.
"""

from collections import Counter
from collections.abc import Callable, Iterable, Sequence
from datetime import date, timedelta

from chessop.clock import utc_day, utc_midnight
from chessop.graph import DEFAULT_BAND
from chessop.memory import DAY
from chessop.store import Store, UsageDay

DAYS_SHOWN = 30  # the aggregate's last rows
WEEKS_SHOWN = 12  # the current week and the ones before it
MONTHS_SHOWN = 12
ACTIVE_SPAN = 30  # days: who the mixes are of
RETURN_AFTER = (1, 7, 30)  # days after a learner was created


def report(store: Store, now: float) -> str:
    """Every table, as `chessop stats` prints them at `now`."""
    usage = store.usage_days()
    days = usage[-DAYS_SHOWN:]
    written = [u for u in days if u.rounds is not None]
    today = date.fromisoformat(utc_day(now))
    weeks = [today - timedelta(days=today.weekday() + 7 * i) for i in reversed(range(WEEKS_SHOWN))]
    return "\n".join(
        (
            _active_days(written),
            _active_spans(store, "week", "week of", weeks, lambda d: d + timedelta(days=7)),
            _active_spans(store, "month", "month", _months(today), _next_month, label=_month),
            _table(
                "New learners per day",
                ("day", "new"),
                [(u.day, str(u.new_learners)) for u in written],
            ),
            _rounds(written),
            _success_rate(usage),
            _table(
                "Sign-ins, adoptions and deletions per day",
                ("day", "sign-ins", "adoptions", "deletions"),
                [(u.day, str(u.sign_ins), str(u.adoptions), str(u.deletions)) for u in days],
            ),
            _retention(store, weeks, now),
            _mixes(store, now),
        )
    )


ACTIVE_HEADINGS = ("anonymous", "signed in", "total")


def _active_row(label: str, anonymous: int, signed_in: int) -> tuple[str, ...]:
    return label, str(anonymous), str(signed_in), str(anonymous + signed_in)


def _active_days(written: list[UsageDay]) -> str:
    rows = [_active_row(u.day, u.active_anonymous or 0, u.active_signed_in or 0) for u in written]
    return _table("Active learners per day", ("day", *ACTIVE_HEADINGS), rows)


def _active_spans(
    store: Store,
    span: str,
    heading: str,
    starts: Sequence[date],
    following: Callable[[date], date],
    label: Callable[[date], str] = date.isoformat,
) -> str:
    """Active learners in each span beginning on one of `starts`, from the first with any."""
    rows: list[tuple[str, ...]] = []
    for start in starts:
        begin = utc_midnight(start.isoformat())
        anonymous, signed_in = store.active_learners(
            begin, utc_midnight(following(start).isoformat())
        )
        if rows or anonymous + signed_in:
            rows.append(_active_row(label(start), anonymous, signed_in))
    return _table(f"Active learners per {span}", (heading, *ACTIVE_HEADINGS), rows)


def _months(today: date) -> list[date]:
    """The first days of the current month and of the ones before it, oldest first."""
    firsts = [today.replace(day=1)]
    while len(firsts) < MONTHS_SHOWN:
        firsts.append((firsts[-1] - timedelta(days=1)).replace(day=1))
    return firsts[::-1]


def _next_month(first: date) -> date:
    return (first + timedelta(days=31)).replace(day=1)


def _month(first: date) -> str:
    return first.isoformat()[:7]


def _rounds(written: list[UsageDay]) -> str:
    rows = []
    for u in written:
        active = (u.active_anonymous or 0) + (u.active_signed_in or 0)
        per = f"{(u.rounds or 0) / active:.1f}" if active else "-"
        rows.append((u.day, str(u.rounds), per))
    return _table("Rounds per day", ("day", "rounds", "per active learner"), rows)


def _success_rate(usage: list[UsageDay]) -> str:
    """Over every day the aggregate wrote, forced rounds out of both counts (public spec G4)."""
    rounds = sum(u.rounds or 0 for u in usage)
    successes = sum(u.successes or 0 for u in usage)
    rate = f"{100 * successes / rounds:.1f}%" if rounds else "-"
    return (
        f"Success rate: {rate} ({successes} successes in {rounds} rounds,"
        " forced exploration left out)\n"
    )


def _retention(store: Store, weeks: Sequence[date], now: float) -> str:
    """Of each week's new learners, how many logged a round at least 1, 7 and 30 days after
    they were created; "-" until every one of them could have."""
    rows = []
    for monday in weeks:
        begin = utc_midnight(monday.isoformat())
        end = begin + 7 * DAY
        created, returned = store.returning_learners(begin, end, [n * DAY for n in RETURN_AFTER])
        if not created:
            continue
        cells = [
            f"{count} ({round(100 * count / created)}%)" if end + n * DAY <= now else "-"
            for n, count in zip(RETURN_AFTER, returned, strict=True)
        ]
        rows.append((monday.isoformat(), str(created), *cells))
    headings = [f"after {n} day{'s' if n > 1 else ''}" for n in RETURN_AFTER]
    return _table("Retention of each week's new learners", ("week of", "new", *headings), rows)


def _mixes(store: Store, now: float) -> str:
    """The bands, opted-out openings and snapshot versions of the learners active lately."""
    bands: Counter[str] = Counter()
    openings: Counter[str] = Counter()
    versions: Counter[str] = Counter()
    for band, opted_out, version in store.choices_since(now - ACTIVE_SPAN * DAY):
        bands[band or DEFAULT_BAND] += 1
        openings.update(opted_out or ["none"])
        versions[version or "none"] += 1
    return "\n".join(
        (
            f"Active, in the three tables below: a round in the last {ACTIVE_SPAN} days.\n",
            _table("Bands of active learners", ("band", "learners"), _counted(bands)),
            _table("Openings of active learners", ("opted out", "learners"), _counted(openings)),
            _table(
                "Snapshot versions of active learners", ("version", "learners"), _counted(versions)
            ),
        )
    )


def _counted(counts: Counter[str]) -> list[tuple[str, str]]:
    """Most learners first, then by name."""
    ranked = sorted(counts.items(), key=lambda item: (-item[1], item[0].casefold()))
    return [(name, str(count)) for name, count in ranked]


def _table(title: str, header: Sequence[str], rows: Iterable[Sequence[str]]) -> str:
    """`title`, then the rows under `header`, indented: the first column to the left, the
    others to the right."""
    lines = [list(header), *(list(row) for row in rows)]
    if len(lines) == 1:
        return f"{title}\n  (none)\n"
    widths = [max(len(line[i]) for line in lines) for i in range(len(header))]
    text = [title]
    for line in lines:
        cells = [line[0].ljust(widths[0])]
        cells += [cell.rjust(width) for cell, width in zip(line[1:], widths[1:], strict=True)]
        text.append("  " + "  ".join(cells))
    return "\n".join(text) + "\n"
