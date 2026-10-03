# Sign-in with Lichess and email

Type: grilling
Status: resolved
Blocked by: 04
Map: [chessop in public](../map.md)

## Question

Settled at charting: Log in with Lichess (OAuth) first, email magic link as fallback, no passwords. Decide the details: which Lichess OAuth scopes (none beyond identity?), how an email-only account and a Lichess account relate (can one learner link both?), which service sends magic-link emails and at what cost, session lifetime and cookie settings, sign-out (does the device go back to a fresh, empty anonymous learner?) and "delete my account", and what the local single-learner mode shows (no sign-in at all).

## Answer

Grilled 2026-09-29. Recorded in [ADR 0008](../../../docs/adr/0008-sign-in.md), which supersedes ADR 0002's "Accounts with Lichess OAuth: rejected" for the hosted mode. Glossary unchanged (**Account** already reads "one sign-in identity, Lichess or email"). Facts: `docs/research/sign-in.md` on branch `research/sign-in` (commit b7175fb).

- **Account = one identity**, Lichess id or email, no linking, no joining by email.
- **Lichess**: PKCE, `client_id` `chessop.fr`, no scope; read `id` (key) + username (display) from `GET /api/account`, then `DELETE /api/token`. No token or email stored.
- **Email**: Scaleway TEM (fr-par) HTTP API from `login@chessop.fr`; SPF, DKIM, DMARC `p=none` to start, in the OVH DNS zone. ~€0 at hobby scale (300/month free, then €0.25/1000).
- **Magic link**: link + 6-digit code in one email, 15 min, single-use, token ≥ 128 bits stored hashed. Link opens a confirm button; only its POST signs in. Code bound to the requesting browser's pending sign-in, 5 tries, a resend does not reset the count. First sign-in with an unknown address creates the account. Landing page sends `Referrer-Policy: no-referrer`; links built from a fixed base URL.
- **Limits**: always "check your inbox", sent in the background; 3 emails / address / 15 min, 10 / IP / hour, 250 / day globally.
- **Session**: one HttpOnly/Secure/SameSite=Lax cookie holding a server-side session token, rotated at sign-in (adopt) and sign-out; signed-in sessions last 1 year, sliding. Server-side sessions let deletion sign out every device.
- **Sign-out**: cookie cleared; the next round creates a fresh anonymous learner.
- **Delete my account**: account page, confirm dialog, immediate deletion of learner, history, identities, sessions. No grace period.
- **Email change**: account page, confirm link to the new address (same mechanics); refused if another account holds it.
- **UI**: header "Sign in" → `/signin` (Lichess first, email field below), returning to the page you came from; signed in, the header shows username or email, linking to an account page (sign out, delete, change email). The once-shown "progress lives in this browser" notice after the first round offers sign-in too.
- **Local mode**: no sign-in routes, link, notice, or cookie.
- **Handed on**: anonymous cookie lifetime, export, inactivity purge → "Legal pages and data rights"; mobile layout → "Mobile pages and installable app"; configuration of the Lichess/Scaleway/base-URL settings → "Switching chessop serve into hosted mode".
