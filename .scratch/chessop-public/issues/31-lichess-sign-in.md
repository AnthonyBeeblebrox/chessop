# 31: Lichess sign-in

**What to build:** A learner signs in with their Lichess identity in two clicks, offered first on `/signin`. OAuth2 with PKCE, the `client_id` and `redirect_uri` derived from the configured base URL, no scope and no client secret. After the callback the server calls the Lichess account endpoint once for the id (the account key) and username (shown in the header), then revokes the token. No token and no email are stored. The same session, adoption and sign-out rules as email apply. A Lichess account and an email account are different accounts: no linking. The Lichess client is injected, with a fake for tests. (Spec §5, ADR 0008.)

**Blocked by:** 29

**Status:** done

- [x] Sign-in with the fake client creates or reaches the account keyed by the Lichess id, and the header shows the username
- [x] The authorisation request carries a PKCE challenge, no scope, and URLs from the base URL even with a forged `Host`
- [x] The token is revoked after the one account call and stored nowhere
- [x] A wrong or replayed `state` is refused
- [x] Anonymous history is adopted exactly as with email
- [x] Signing in with email afterwards reaches a different account
