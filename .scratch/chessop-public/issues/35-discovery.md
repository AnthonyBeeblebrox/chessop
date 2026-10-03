# 35: Discovery: pitch, link previews, indexing, README

**What to build:** Someone who meets a chessop link sees what it is. Hosted `/` is titled `chessop: grind chess openings` with the description "Grind chess openings against the moves people at your rating really play, drawn from Lichess games. Free, no sign-up."; `/help` keeps its title with the same description. `/` and `/help` are indexable with `rel=canonical`; every other page carries `noindex`; `robots.txt` allows crawling; no sitemap. Open Graph title, description, URL, type and image plus `twitter:card` come through `site`, all built from the configured base URL, never the request's `Host`. The preview image is one static 1200×630 PNG; ship a placeholder, the owner makes the real one (ticket 48). The README leads with the pitch, the site link and a screenshot slot, then "Run it yourself", then "Hosting your own" (no support promised), licence last, no badges. "Grind" appears in the pitch only. Local mode has none of the tags and its title is unchanged. (Spec §11.)

**Blocked by:** 24, 28

**Status:** done

- [ ] Hosted `/` and `/help` carry the title, description, canonical and Open Graph tags from the base URL even with a forged `Host`
- [ ] Every other hosted page carries `noindex`
- [ ] `robots.txt` is served in hosted mode only and allows crawling
- [ ] Local pages have no Open Graph or canonical tags and no `robots.txt`
- [ ] The README follows the stated order
- [ ] "Grind" appears nowhere outside the pitch
