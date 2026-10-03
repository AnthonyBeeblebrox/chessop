# 19: Shared base template (prefactor)

**What to build:** Every page (play, progress, settings, position, reset) extends one shared base template that owns the document head, `lang="en"` and the common chrome, and takes a `site` value that is empty in local mode. No behaviour or appearance changes. This is the prefactor that lets the footer, link previews, manifest link and sign-in link arrive later in one place. (Spec §1, seam 3.)

**Blocked by:** None (can start immediately)

**Status:** done

- [x] Every page template extends the base template
- [x] The rendered pages are unchanged in local mode (existing tests pass untouched)
- [x] The base template accepts a `site` value and renders nothing extra when it is absent
- [x] No template other than the base tests for `site`
