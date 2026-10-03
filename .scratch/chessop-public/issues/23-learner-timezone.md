# 23: Learner timezone

**What to build:** A learner's day ends at their own midnight. The browser sends a new client-to-server message, `hello {tz}`, with its IANA timezone when the socket opens; the server stores it when the learner has none and sends no reply. The timezone is a per-learner setting, editable in settings. The daily Score's day and "change since your last day" follow it. Local mode keeps using the machine clock. A clock is injected at the app factory so tests can move time. (Spec §3, G6.)

**Blocked by:** 22

**Status:** done

- [x] `hello {tz}` sets the timezone when unset and does not overwrite a stored one
- [x] An invalid timezone name is ignored
- [x] The timezone is shown and editable in settings
- [x] With the injected clock, a round played just before and just after the learner's local midnight lands on two different days of the daily Score
- [x] Local mode's day boundary is unchanged

## Comments

**Decision (owner, 2026-10-02):** In local mode the learner's day always follows the machine's zone; `hello {tz}` and the stored timezone do not move local mode's day boundary (ADR 0002). The timezone criteria are tested at the store/day-computation seam with the injected clock and a non-implicit learner, and through the wire once ticket 28 adds hosted mode. The working tree holds an earlier uncommitted attempt at this ticket: build on it and bring it in line with this decision.

**Built (2026-10-02):** `LearnerStore.day` follows the learner's stored zone, except for the learner `Store.implicit()` hands out, whose day is always the machine's. `hello` lives in `choices.hello`. Local settings show no time zone field, and a form without one keeps the stored zone. The criteria are tested at the store/choices seam with a learner from `create_learner`, and local mode's unchanged day also through the wire. Glossary gap for `/domain-modeling`: "the learner's day" and "time zone" are not yet in `CONTEXT.md`.
