"""The learner's choices (spec §11): what the `/settings` form edits, stored in `settings`.

`Choices` is everything the form sets: the rating band (its graph loaded), the repertoire's
widths, popularity floor and share, the memory model's parameters, sound, animation and the time
zone the learner's days follow (public spec §3; the play page's `hello` also writes it). `load`
reads them from the store, each key at its §11 default until written; `parse` checks a submitted
form against the constraints and returns the new choices or one message per refused field; `save`
writes them back. The opted-out openings are read with the rest but edited from the progress view.
"""

import math
from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from typing import Any

from chessop.clock import zone
from chessop.graph import BANDS, DEFAULT_BAND
from chessop.memory import DAY, HOUR, MINUTE, Params
from chessop.repertoire import Settings
from chessop.store import TIMEZONE, LearnerStore


@dataclass(frozen=True)
class Choices:
    """Everything the settings page sets, at the spec §11 defaults."""

    settings: Settings = field(default_factory=Settings)
    params: Params = field(default_factory=Params)
    sound: bool = True
    animation_ms: int = 100
    timezone: str | None = None  # an IANA name; None: the machine's


@dataclass(frozen=True)
class Field:
    """One numeric field of the form: where its value lives, its unit on the form, its check."""

    key: str
    label: str
    check: Callable[[float], bool]
    rule: str  # the constraint, as the page states it and refuses with
    scale: float = 1.0  # stored value = form value * scale
    unit: str = ""
    integer: bool = False


def _between(low: float, high: float) -> Callable[[float], bool]:
    return lambda v: low <= v <= high


def _at_least(low: float) -> Callable[[float], bool]:
    return lambda v: v >= low


def _above(low: float) -> Callable[[float], bool]:
    return lambda v: v > low


# The repertoire's keys (in `Settings`), then the memory model's (in `Params`).
SETTINGS_FIELDS: tuple[Field, ...] = (
    Field("width_player", "Your width", _at_least(1), "an integer, at least 1", integer=True),
    Field(
        "width_opponent", "Opponent's width", _at_least(1), "an integer, at least 1", integer=True
    ),
    Field(
        "popularity_floor",
        "Popularity floor",
        _at_least(0),  # also at least the snapshot's storage cut-off, checked in `parse`
        "a share of the band's games, at least the snapshot's storage cut-off",
    ),
    Field("share", "Share", _between(0, 1), "between 0 and 1"),
)
PARAMS_FIELDS: tuple[Field, ...] = (
    Field("h0", "Initial half-life", _above(0), "above 0", HOUR, "hours"),
    Field("h_min", "Shortest half-life", _above(0), "above 0", MINUTE, "minutes"),
    Field("h_max", "Longest half-life", _above(0), "above 0, at least the shortest", DAY, "days"),
    Field("sure", "Sure threshold", lambda v: 0 < v < 1, "between 0 and 1, exclusive"),
    Field("floor", "Need floor", _between(0, 1), "between 0 and 1"),
    Field("C", "Exploration scale", _at_least(0), "at least 0"),
    Field("alpha", "Popularity exponent", _at_least(0), "at least 0"),
    Field("forced_rate", "Forced exploration rate", _between(0, 1), "between 0 and 1"),
    Field("side_floor", "Side floor", _between(0, 0.5), "between 0 and 0.5"),
)
ANIMATION = Field(
    "animation_ms", "Animation", _between(0, 100), "0 to 100", unit="ms", integer=True
)
BAND_NAMES: tuple[str, ...] = tuple(name for name, _, _ in BANDS)  # as the page lists them


def load(store: LearnerStore) -> Choices:
    """The choices stored, each at its default until written."""
    d = Choices()
    settings = Settings(
        band=store.setting("band", DEFAULT_BAND),
        opted_out=frozenset(store.setting("opted_out", [])),
        **{f.key: store.setting(f.key, getattr(d.settings, f.key)) for f in SETTINGS_FIELDS},
    )
    params = Params(
        **{f.key: store.setting(f.key, getattr(d.params, f.key)) for f in PARAMS_FIELDS}
    )
    return Choices(
        settings=settings,
        params=params,
        sound=bool(store.setting("sound", d.sound)),
        animation_ms=store.setting("animation_ms", d.animation_ms),
        timezone=store.setting(TIMEZONE, d.timezone),
    )


def save(store: LearnerStore, choices: Choices, *, sets_params: bool = True) -> None:
    """Write every key the form sets; the memory model's only when `sets_params`."""
    values: dict[str, Any] = {
        "band": choices.settings.band,
        "sound": choices.sound,
        "animation_ms": choices.animation_ms,
    }
    values.update({f.key: getattr(choices.settings, f.key) for f in SETTINGS_FIELDS})
    if sets_params:
        values.update({f.key: getattr(choices.params, f.key) for f in PARAMS_FIELDS})
    for key, value in values.items():
        store.set_setting(key, value)
    if choices.timezone is None:
        store.unset_setting(TIMEZONE)
    else:
        store.set_setting(TIMEZONE, choices.timezone)


def hello(store: LearnerStore, tz: object) -> None:
    """The play page's `hello {tz}` (public spec G6): the browser's time zone becomes the
    learner's while they have none, when it names one; anything else is ignored."""
    if zone(tz) is not None and store.setting(TIMEZONE, None) is None:
        store.set_setting(TIMEZONE, tz)


def form_values(choices: Choices) -> dict[str, str]:
    """The choices as the form shows them, in the form's units."""
    out = {
        "band": choices.settings.band,
        "animation_ms": str(choices.animation_ms),
        "sound": "on" if choices.sound else "",
        "timezone": choices.timezone or "",
    }
    for group, source in ((SETTINGS_FIELDS, choices.settings), (PARAMS_FIELDS, choices.params)):
        for f in group:
            out[f.key] = f"{getattr(source, f.key) / f.scale:g}"
    return out


def parse(
    form: Mapping[str, str],
    current: Choices,
    storage_cutoff: float,
    bands: tuple[str, ...],
    *,
    sets_params: bool = True,
) -> Choices | dict[str, str]:
    """The choices a submitted form makes, or a message per refused field.

    `current` supplies what the form does not edit (the opted-out openings, the time zone when
    the form has no field for it, and the memory model's parameters unless `sets_params`: they are
    then not the learner's to set, whatever the form carries); `bands` are the bands the
    snapshot holds, so a band not among them is refused though the page lists it.
    """
    errors: dict[str, str] = {}

    def number(f: Field) -> Any:
        raw = form.get(f.key, "").strip()
        try:
            value = int(raw) if f.integer else float(raw)
        except ValueError:
            value = None
        if value is None or not math.isfinite(value) or not f.check(value):
            errors[f.key] = f"{f.label}: {f.rule}"
            return None
        return value * f.scale if f.scale != 1.0 else value

    band = form.get("band", "")
    if band not in BAND_NAMES:
        errors["band"] = "Rating band: one of the bands listed"
    elif band not in bands:
        errors["band"] = f"Rating band: the snapshot holds no games for band {band}"
    # A form without the field (local mode's, whose day is the machine's) keeps the current one.
    timezone = (form["timezone"].strip() or None) if "timezone" in form else current.timezone
    if timezone is not None and zone(timezone) is None:
        errors["timezone"] = "Time zone: an IANA name such as Europe/Paris, or blank"
    settings = {f.key: number(f) for f in SETTINGS_FIELDS}
    model = {f.key: number(f) for f in PARAMS_FIELDS} if sets_params else None
    animation_ms = number(ANIMATION)
    floor = settings["popularity_floor"]
    if floor is not None and floor < storage_cutoff:
        errors["popularity_floor"] = (
            f"Popularity floor: at least the snapshot's storage cut-off, {storage_cutoff:g}"
        )
    if model is not None:
        h_min, h_max = model["h_min"], model["h_max"]
        if h_min is not None and h_max is not None and h_max < h_min:
            errors["h_max"] = "Longest half-life: at least the shortest"
    if errors:
        return errors
    return Choices(
        settings=replace(current.settings, band=band, **settings),
        params=current.params if model is None else Params(**model),
        sound=bool(form.get("sound")),
        animation_ms=animation_ms,
        timezone=timezone,
    )


def ignores_forced_rate(choices: Choices) -> bool:
    """With one accepted move per position there is nothing to set aside (ticket 05)."""
    return choices.settings.width_player == 1
