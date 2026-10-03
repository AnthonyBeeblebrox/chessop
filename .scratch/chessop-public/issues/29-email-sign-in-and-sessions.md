# 29: Email sign-in, sessions, adopt into an empty account

**What to build:** An anonymous learner signs in with an email address and never a password. The header's "Sign in" leads to `/signin` (the email field, a link to the privacy notice) and returns to the page they came from. One message carries a link and a 6-digit code, both single-use, valid 15 minutes, stored hashed, the token at least 128 bits. The link opens a page with a confirm button, sent with `Referrer-Policy: no-referrer`; only that button's POST signs in. The code is typed into the requesting tab and bound to that browser's pending sign-in: 5 tries, and a resend does not reset the count. An unknown address creates the account. The answer is always "check your inbox". Limits: 3 emails per address per 15 minutes, 10 per IP per hour, 250 per day site-wide. Mail goes through an injected mailer; the console mailer (printing the message) is the development implementation and a recording fake serves the tests.

The session uses the same single cookie, holding a server-side session token rotated at sign-in and at sign-out, lasting one year sliding, with no cap on concurrent sign-ins. At sign-in the browser's anonymous learner is adopted with no prompt: an account with no history takes everything and the anonymous learner is deleted (merging into an account that has history is ticket 30). Signed in, the header shows the email, linking to a minimal account page with Sign out. Sign-out clears the cookie and leaves no learner on the browser. Local mode has none of this. (Spec §5, ADR 0008.)

**Blocked by:** 28

**Status:** done

- [x] Link flow: opening the link signs nobody in; the confirm POST does; a second use fails
- [x] Code flow: the code works only in the requesting client; five wrong tries exhaust it; a resend does not reset the count
- [x] Both expire after 15 minutes (injected clock)
- [x] An unknown address creates an account at first sign-in; the response is "check your inbox" for any address, and past each email limit
- [x] The cookie token rotates at sign-in and sign-out; the session lasts a year from the last visit
- [x] Signing in for the first time keeps the anonymous history under the account, and the anonymous learner no longer exists
- [x] After sign-out the browser has no learner and sees none of the account's history; the next round creates a fresh anonymous one
- [x] The header shows "Sign in" or the email; sign-in returns to the originating page
- [x] With no mail key, the message is printed to the console
- [x] Local mode has no sign-in routes, link, notice or cookie
