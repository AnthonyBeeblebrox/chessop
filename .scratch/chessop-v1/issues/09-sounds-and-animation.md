# 09: Sounds and animation

**What to build:** the play page sounds like Lichess: Move, Capture, Check, Victory on a success, Error on a miss, nothing extra on forced. The `m` key toggles sound and the choice persists. Piece animation is 100 ms by default and follows the `animation_ms` setting.

Spec: [`../../chessop/spec.md`](../../chessop/spec.md) §8 (`sound` message), §9 (sounds, animation), §11 (`sound`, `animation_ms`), §12. Ticket 16; ADR 0004 ticket 21 amendment.

**Blocked by:** 04 (Memory model and persistence).

**Status:** done

- [x] Lichess `sfx` set (Enigmahack, AGPLv3+) vendored with its licence: Move, Capture, Check, Victory, Error (the set's Defeat, since its Error is a link to the `standard` set); the non-free `standard` set not shipped
- [x] Sounds per spec §9 on every move, including the opponent's reply
- [x] `m` toggles sound and sends `{"type": "sound", "on": bool}`; the server writes the `sound` setting, replies nothing, and accepts it with or without a round in flight
- [x] The page starts with the persisted `sound` and `animation_ms` (default true and 100; 0 disables animation)
- [x] Test: the `sound` message persists the setting
- [x] `uv run ruff format --check`, `uv run ruff check`, `uv run ty check` and `uv run pytest` all pass
