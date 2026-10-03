# Mobile layout and installable app

Type: prototype
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

How should the play page, settings, and progress view look and behave on a phone (portrait, one hand, touch drags on chessground, keyboard shortcuts such as `m` having no equivalent), and what does the PWA add: manifest, icon, splash, what a service worker caches given play needs the server? Decided by a rough prototype viewed on a real phone.

## Answer

Decided on a real phone over 4G against the prototype (branch `prototype/mobile`, commit `dd448bc`: three play layouts A Stacked / B Thumb bar / C Focus, two progress layouts A Condensed table / B Cards, a manifest, icons and a service worker). The owner picked **Stacked** for play and **Condensed table** for progress.

**Play page on a narrow screen (below about 40em wide): Stacked.**
- One compact header row: the side badge, the Score and its change, then three 44 px icon buttons on the right: sound on/off, progress, settings. They replace the text links in the corner.
- The opening name (and the yellow "not X this time") on its own line under the header.
- The board as wide as the screen (capped at 72vh), `touch-action: none` so dragging never scrolls or zooms. Drag and chessground's tap-to-move both work; the owner found the squares big enough.
- The verdict strip under the board, wrapping onto two lines if needed. The "space next round" hint is hidden on touch.
- A full-width green **Next round** button (at least 52 px tall) under the verdict, shown only once the round is over. Tapping the verdict still starts the next round.
- The Explanation below, scrolling with the page.
- Touch equivalents of the keys: the sound icon does what `m` does (and shows 🔊/🔇); Next does what space does. The keys stay on desktop.
- **Landscape** (not prototyped, decided here): the board on the left at full height, the header, verdict, Next and Explanation in a column on its right.
- The desktop layout stays as v1 has it.

**Progress page on a narrow screen: Condensed table.** Columns cut to opening name, Score, White, Black. ECO, positions and the known/learning bar are hidden. The in/out and reset buttons appear only when the row is opened. Move chips in the branches get tap padding (about 6 px). The head block wraps as it does today. Settings needs no change: its form already goes to one column below 40em.

**Installable app (PWA).**
- A web app manifest: name "chessop — drill your openings", short name "chessop", `start_url` `/`, `display: standalone`, **any orientation** (no lock), background and theme `#161512`, icons 192 and 512 px PNG plus a maskable 512. Apple touch icon and `apple-mobile-web-app-capable` for iOS.
- A service worker at `/sw.js` (root scope) that **caches only the static shell**: chessground's JS and CSS, pieces, the five sounds, the page CSS/JS and the icon, under a cache name that changes with each release (old caches deleted on activate). Page loads always go to the network. When a page load fails it shows an offline page: "chessop needs a connection: every move is checked by the server", with a Try again button. **No offline play** (ADR 0004 keeps the server authoritative).
- Installing needs https, which the hosted site has (ADR 0007). Whether local mode also serves the manifest and service worker is left to "Switching chessop serve into hosted mode".
