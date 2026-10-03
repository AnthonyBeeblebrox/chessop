# 27: Installable app

**What to build:** chessop installs to a home screen and opens full-screen, in both modes. A web app manifest (name "chessop — drill your openings", short name "chessop", `start_url` `/`, standalone, any orientation, background and theme `#161512`, 192 and 512 px icons plus a maskable 512), an Apple touch icon and the iOS web-app meta tag are linked from the base template. A service worker at `/sw.js` with root scope caches only the static shell under a cache name that changes with each release and deletes old caches on activate; page loads always go to the network; when one fails it shows the offline page "chessop needs a connection: every move is checked by the server" with a Try again button. No offline play. (Spec §8.)

**Blocked by:** 19

**Status:** done

- [x] The manifest and `/sw.js` are served in local mode with the stated fields and root scope
- [x] The cache name includes the release version
- [x] Only static shell files are cached; pages and the socket are never served from cache
- [x] With the network off, a page load shows the offline page and Try again reloads (verified by hand)
- [x] Icons at 192, 512 and maskable 512 exist and are referenced
