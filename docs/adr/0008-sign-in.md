# Sign-in: Lichess identity or email magic link, one per account

Status: accepted (chessop-public ticket 05, 2026-09-29)

The hosted mode (ADR 0007) lets an anonymous learner sign in so their history follows them to other devices; signing in adopts the anonymous history (ADR 0002). This ADR decides how a learner proves who they are. Facts come from `docs/research/sign-in.md` (branch `research/sign-in`).

## Decision

- **Two ways in, no passwords**: "Log in with Lichess" (OAuth2 with PKCE, no client registration, `client_id` `chessop.fr`) offered first, and an email magic link below it.
- **An account is exactly one sign-in identity**: a Lichess id or an email address, never both. Signing in with the other method reaches a different account; there is no linking and no automatic joining by email.
- **From Lichess, identity only**: no scope; `GET /api/account` once for the `id` (the stable key: a username can change only its letter case) and the username (for display). The token is revoked at once and never stored; no email is asked of Lichess.
- **The magic-link email carries a link and a 6-digit code**, both single-use and valid 15 minutes. The link opens a confirmation button whose POST signs in, so mail scanners do not spend it; the code is typed into the requesting tab for mail read on another device. The first sign-in with an unknown address creates the account.
- **Email goes through Scaleway Transactional Email** (Paris region) from `login@chessop.fr`, with SPF, DKIM and DMARC on the domain.
- **One cookie** for anonymous and signed-in learners alike: a server-side session token, rotated at sign-in and sign-out. Signed-in sessions last a year, renewed on each visit. Sign-out leaves the browser with no learner; the next round starts a fresh anonymous one.
- **Local mode has no sign-in**: no routes, no link, no cookie (ADR 0002's single implicit learner).

## Considered options

- **Linking a Lichess identity and an email on one account**: a fallback for a Lichess user, at the cost of a linking flow and merge rules between two accounts; rare for a hobby site, and addable later since identities are keyed separately.
- **Joining accounts by the email Lichess reports** (`email:read`): automatic, but collects an address the learner never gave chessop and silently merges histories.
- **Passwords**: storage, resets and breach exposure for a hobby site; ruled out at charting.
- **A link-only magic email**: breaks when the mail is read on another device or pre-fetched by a scanner.
- **Sending from the VPS** (free, but a fresh IP with no reputation), **Brevo or Mailjet** (their branding on free-tier mail), **Amazon SES** (sandbox for new accounts), **US providers** (Postmark, Resend: data outside the EU).
- **Sign-out keeping a copy as a new anonymous learner**: leaks the account's history to the next person on a shared machine.

## Consequences

- One person can end up with two separate accounts (Lichess and email) holding split history; accepted.
- An email account can change its address (confirmed by a link to the new one, refused if another account holds it); a Lichess account has no email to change.
- Deleting an account deletes the learner, its history and every session at once; with sessions server-side, every device is signed out.
- NIST does not count email alone as strong authentication; acceptable for practice history, and one more reason Lichess comes first.
- Supersedes ADR 0002's rejection of "Accounts with Lichess OAuth" for the hosted mode.

## Amendment: what binds the code to the requesting browser (chessop-public ticket 29)

The 6-digit code is good only together with a **binding**: a random value the "check your inbox" page holds in a hidden form field, stored hashed with the pending sign-in, never mailed. Not a cookie: the site keeps its one cookie, and asking to sign in sets none. A resend from that page carries the binding, so it keeps the count of wrong tries. The link needs no binding and works from any browser.

## Amendment: what binds a Lichess sign-in to the browser that began it (chessop-public ticket 31)

The OAuth `state` and the PKCE verifier are held in the process's memory for 10 minutes, the `state` good once; a restart loses the sign-ins under way, and the learner presses the button again. The `state` is good only in a browser whose cookie is what it was when the sign-in began (or that still has none). Not a second cookie: the site keeps its one cookie, and asking to sign in sets none. So a sign-in begun elsewhere cannot make a browser with an anonymous learner hand their history to someone else's account. The start is a button's POST, so a fetched link begins nothing. The username shown is refreshed at each sign-in, since its letter case can change.

## Amendment: how an email account changes its address (chessop-public ticket 32)

The account page mails the new address **a link only**, no code: the change is asked from a signed-in page, so there is no other tab to type a code into. The link is the sign-in link's in every other way: 256 random bits stored hashed, good once for 15 minutes, opening a page (`Referrer-Policy: no-referrer`) whose button's POST makes the change, from any browser, within the sign-in emails' limits. A pending change is a pending sign-in of purpose `email-change`, carrying the learner it is for (a column added for it, cascading on the learner's deletion); a learner has one at most, so a newer request kills the older link. It is refused, with nothing mailed, when another account holds the address, and again at the button when one has taken it since; the page says so and nothing else does. The account's sessions stay signed in; the old address then signs in to a different, new account.
