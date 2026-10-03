# Sign-in: Lichess OAuth, magic-link email, and good practice

Research ticket: [05-sign-in](../../.scratch/chessop-public/issues/05-sign-in.md). Date: 2026-09-29.

Context: chessop.fr, a hobby trainer on one OVH VPS in France (Python server, SQLite), tens of concurrent learners, a few hundred accounts at most, owner a private individual under GDPR. Sign-in = "Log in with Lichess" first, email magic link as fallback, no passwords.

Primary sources read: the Lichess OpenAPI spec (`lichess-org/api` @ `4553fde`, 2026-09-28) and Lichess server source (`lichess-org/lila` @ `d9ee02f`, 2026-09-29); vendor pricing/docs pages as fetched on 2026-09-29; OWASP Cheat Sheet Series (master, 2026-09-29); NIST SP 800-63B-4; Google's sender guidelines.

## Summary

1. **Lichess OAuth needs no registration.** PKCE (S256 only) with any unique `client_id` you choose (e.g. `chessop.fr`); no client secret. `GET /api/account` needs **no scope**; it returns the stable `id` (lowercase username) and `username`. `email:read` adds `GET /api/account/email`, which we do not need. Tokens last 12 months, no refresh tokens; revoke with `DELETE /api/token`. Store the Lichess `id` as the key: a username can only change letter case, and a closed account's name is never reissued.
2. **Email provider: Scaleway Transactional Email (TEM).** It is French, runs only in `fr-par`, has no non-EU sub-processors, gives 300 free emails/month, then €0.25 per 1,000. That is €0 at 100 emails/month and about €0.18 at 1,000. It offers API and SMTP. You need SPF and DKIM records on chessop.fr, plus DMARC. Brevo (300/day free) and Mailjet (6,000/month free, 200/day) are EU-hosted fallbacks, but both put their branding on free-tier mail. Resend and Postmark keep data in the US. SES is cheap, but its sandbox and approval step are overkill here. Sending straight from the VPS is possible (OVH does not block port 25 on VPS by default), but you would have to build IP reputation yourself, and it is the least reliable option.
3. **Magic links.** Send a random token of at least 128 bits, stored only as a hash, single-use, expiring in about 10-15 minutes. Put a **6-digit code in the same email** so someone who opens the email on another device can still sign in. Opening the link should show a page with a button, and only the button's POST consumes the token; this stops link scanners from burning it. Always answer "if that address is valid, we sent a link" in constant time. Rate-limit per address and per IP, and cap failed code tries per pending login.

## 1. Lichess OAuth2

### Client registration and flow

- "Lichess supports unregistered and public clients (no client authentication, choose any unique client id). The only accepted code challenge method is `S256`." [api spec, `lichess-api.yaml` §Authentication]
- `client_id`: "Arbitrary identifier that uniquely identifies your application", e.g. `example.com` [`tags/oauth/oauth.yaml`].
- Authorize: `GET https://lichess.org/oauth?response_type=code&client_id=…&redirect_uri=…&code_challenge_method=S256&code_challenge=BASE64URL(SHA256(verifier))&scope=…&state=…`. There is an optional `username` hint. On failure you get `error` (e.g. `access_denied`), `error_description` and `state`. On success you get `code` and `state`. "check that the returned `state` matches" [`oauth.yaml`].
- Token: `POST https://lichess.org/api/token` (form-encoded) with `grant_type=authorization_code`, `code`, `code_verifier`, `redirect_uri` (must match), `client_id` (must match). It returns `token_type`, `access_token` and `expires_in` [`tags/oauth/api-token.yaml`].
- Server-side details [lila `modules/oauth/src/main/`]:
  - The authorization code expires after **120 s** (`AuthorizationApi.scala`: `nowInstant.plusSeconds(120)`).
  - The `code_verifier` must be **at least 43 chars** (`Protocol.scala`: `CodeVerifier.from … _.size >= 43`).
  - Each (user, client origin) keeps at most ~30 tokens; older ones are deleted (`AccessTokenApi.createAndRotate`, `.skip(30)`).
- Python example linked from the spec: [lakinwecker/lichess-oauth-flask](https://github.com/lakinwecker/lichess-oauth-flask) (Authlib).

### Redirect URI rules

From lila `Protocol.scala` (`RedirectUri`):
- Allowed schemes are `http`, `https`, `ionic`, `capacitor`, some grandfathered app schemes, or any scheme containing a `.` (reverse-DNS). Anything else fails with "exotic redirect_uri scheme not allowed".
- There is no pre-registered allow-list, because clients are unregistered. The token request's `redirect_uri` must equal the authorize one. Matching ignores a trailing `/` (`value.toString.stripSuffix("/") == other.value.stripSuffix("/")`); otherwise you get `MismatchingRedirectUri`.
- Plain `http` on a non-local host is flagged `insecure`. `http` on localhost is treated as secure, so a local dev redirect like `http://localhost:8000/auth/lichess/callback` works.
- The consent screen shows the redirect URI's **origin**. The token is stored with that origin (`granted.redirectUri.origin`) and shows under the user's Lichess security settings.

### Scopes: what "no scope" gets you

- `GET /api/account` ("Get my profile — Public information about the logged in user") declares `security: OAuth2: []`, i.e. **no scope required** [`tags/account/api-account.yaml`]. It returns `UserExtended`, which includes `id` and `username` [`schemas/User.yaml`]. So request **no scope** at all. The consent prompt is then minimal, and the token can only read public data.
- `email:read` ("Read your email address") gates `GET /api/account/email`, which returns `{"email": "…"}` [`tags/account/api-account-email.yaml`; lila `OAuthScope.scala`]. We would only want it to pre-fill or link a magic-link account. It is extra personal data under GDPR (data minimisation, Art. 5(1)(c)), so skip it unless a concrete need appears.

### Token lifetime and revocation

- "Access tokens are long-lived (expect one year), unless they are revoked. Refresh tokens are not supported." [spec §Authentication]. lila sets `expires = nowInstant.plusMonths(12)` for tokens issued via OAuth (`AccessTokenApi.create`).
- Revoke with `DELETE https://lichess.org/api/token` and `Authorization: Bearer <token>`, which returns `204` [`api-token.yaml`].
- Recommendation: we only need the identity once. Call `/api/account`, create our own session, then immediately `DELETE /api/token` and **store no Lichess token**. That makes one less secret to protect or declare.

### Identity stability

- The Lichess `id` is the lowercased username. Changing a username only allows a case change: "Only the case of the letters can change. For example "johndoe" to "JohnDoe"" and "This can only be done once" [lila `translation/source/site.xml` `changeUsernameNotSame`, `changeUsernameDescription`]. It is enforced by `name.id == user.username.id` [`modules/user/src/main/UserForm.scala`].
- On closing an account: "The username will NOT be available for registration again." [`translation/source/settings.xml` `cantOpenSimilarAccount`].
- So key accounts on `id`, and show `username` (refresh it on each login in case its case changed).

### Rate limits and terms

- "All requests are rate limited … Only make one request at a time. If you receive an HTTP response with a 429 status … waiting one minute before retrying will be sufficient" [spec §Rate limiting]. No specific number is published for `/api/token` or `/api/account`. One token exchange plus one account read per login is far below any plausible limit.
- The ToS has no clause specific to OAuth login or third-party sites. It reserves "reasonable caps, limits, restrictions … purely determined at Lichess' discretion" and the right to "revoke access temporarily or permanently" ([lichess.org/terms-of-service](https://lichess.org/terms-of-service)). Community guidelines forbid "abuse of our APIs".
- The spec lists third-party sites (e.g. PyChess) as "Real life examples" of Login with Lichess, so this use is sanctioned.

## 2. Transactional email for magic links

Volume: ~100-1,000 emails/month. Budget: part of €10/month.

| Provider | Free tier | Cost at 100 / 1,000 per month | Data location | DPA | Interface | Domain setup |
|---|---|---|---|---|---|---|
| **Scaleway TEM** | 300/month per organization | €0 / ~€0.18 (700 × €0.25/1,000) | EU only, `fr-par`; "no personal data is transferred outside the EU"; no non-EU sub-processors | Yes (Scaleway DPA, French law) | REST API + SMTP relay | SPF + DKIM required; DMARC guidance; no recursive SPF `include` |
| Brevo (FR) | 300/day, shared by marketing and transactional | €0 / €0 | EU (OVH FR/DE, Google Cloud BE) | Yes (in ToS, Annex 2) | API + SMTP | Domain authentication (SPF/DKIM/DMARC); account must be approved before sending |
| Mailjet (Sinch) | 6,000/month, 200/day; Mailjet branding | €0 / €0 | EU (GCP Frankfurt, St-Ghislain BE) | Yes (part of Terms of Use) | API + SMTP | SPF/DKIM |
| OVH mailbox (MX Plan / Email Pro) SMTP | Comes with a mailbox | Mailbox price | FR | OVH DPA | SMTP only (`ssl0.ovh.net`) | OVH DNS SPF; "~200/h per account, 300/h per IP"; OVH says mailboxes are "not designed for … bulk transactional emails" |
| Amazon SES | New-account AWS credits only | ~$0.01 / $0.10 (à la carte $0.10/1,000) | Can pick `eu-west-3` Paris; AWS is a US company | AWS GDPR DPA | API + SMTP | Verify domain (DKIM); **sandbox**: verified recipients only, 200/24 h, until production access is granted after review |
| Postmark | 100/month developer, no expiry | $0 / $15 (Basic, 10k) | US (Chicago DC + AWS); SCCs | Yes | API + SMTP | DKIM + Return-Path |
| Resend | 3,000/month, 100/day, 3 domains | $0 / $0 | Can *send* from `eu-west-1`, but "All account data … is stored in the United States" | Yes (pre-signed, SCCs + DPF) | API + SMTP | SPF/DKIM |
| Self-send (Postfix on VPS) | n/a | €0 | Our VPS | none needed | SMTP | Must set PTR, SPF, DKIM signing, DMARC yourself; cold IP reputation |

Sources:
- Scaleway: [pricing](https://www.scaleway.com/en/pricing/managed-services/) ("Essential 300 per organization (Free tier) Pay As You Go … €0.25" per 1,000); [capabilities and limits](https://www.scaleway.com/en/docs/transactional-email/reference-content/tem-capabilities-and-limits/) (default 10,000/month quota, 10 recipients/email, "only available in the fr-par region", "recursive SPF include directive is not supported"); [FAQ](https://www.scaleway.com/en/docs/transactional-email/faq/) ("You need to add SPF and DKIM records to be able to send emails"; "All data is hosted and processed entirely within the European Union"; no non-EU sub-processors; new domains are ramped up progressively); [DPA](https://www-uploads.scaleway.com/DPA_2024_ENG_b0abb5cc26.pdf).
- Brevo: [pricing](https://www.brevo.com/pricing/) ("Once we approve your account for sending, you can start sending up to 300 emails per day"; Starter "from 5,000 emails per month", listed at $9); [data storage location](https://help.brevo.com/hc/en-us/articles/360001005510-Data-storage-location); [DPA](https://corp-backend.brevo.com/wp-content/uploads/2024/08/BREVO-Annex-2-DPA-150524.pdf).
- Mailjet: [pricing](https://www.mailjet.com/pricing/) (6,000/month, 200/day, Starter $9 for 8,000); [where data is stored](https://documentation.mailjet.com/hc/en-us/articles/360042712274-Where-is-my-personal-data-stored); [DPA](https://documentation.mailjet.com/hc/en-us/articles/360042750094-Do-you-provide-a-Data-Processing-Agreement-for-your-clients).
- OVH: [email sending best practices](https://docs.ovhcloud.com/en/guides/web-cloud/web-hosting/email-sending-best-practices) (MX Plan quotas; mailboxes "not designed for bulk sending").
- SES: [pricing](https://aws.amazon.com/ses/pricing/); [sandbox](https://docs.aws.amazon.com/ses/latest/dg/request-production-access.html).
- Postmark: [pricing](https://postmarkapp.com/pricing); [EU privacy](https://postmarkapp.com/eu-privacy); [DPA](https://postmarkapp.com/dpa).
- Resend: [pricing](https://resend.com/pricing); [regions](https://resend.com/docs/dashboard/domains/regions); [DPA](https://resend.com/legal/dpa).

Prices are as listed on 2026-09-29, before tax. Branding on the Brevo free plan is shown on its pricing page (a "Brevo logo" feature row) but not quoted verbatim; check it before choosing Brevo.

### Self-sending from the OVH VPS

- OVH says: "Port 25 is not blocked by default on OVHcloud VPS servers (with the exception of VPS deployed in Local Zones …), but we still recommend using port 587 (STARTTLS)". The same page lists what you must set up: "email authentication (SPF, DKIM, DMARC), reverse DNS (PTR) configuration" ([OVH VPS FAQ](https://docs.ovhcloud.com/en/guides/bare-metal-cloud/virtual-private-servers/vps-faq)). Some third-party blogs claim port 25 is blocked by default; OVH's own FAQ contradicts them.
- OVH's anti-spam (Vade) watches outbound mail. If it detects spam, "we have blocked the port 25 of your server, at the network level" ([OVH AntiSpam](https://docs.ovhcloud.com/en/guides/bare-metal-cloud/dedicated-servers/antispam-best-practices)).
- Gmail requires the following of **all** senders: "SPF or DKIM", "valid forward and reverse DNS records, also referred to as PTR records", TLS, and a spam rate under 0.3%. DMARC and From-alignment are required only above 5,000/day ([Google sender guidelines](https://support.google.com/a/answer/81126)).
- In practice: a single fresh VPS IP with ~30 emails/day has no reputation. Outlook/Hotmail and small French ISPs are the usual trouble spots. You would also run Postfix and OpenDKIM and watch blocklists yourself. That is feasible, but it is ongoing work to save roughly €0.18/month. Keep it as a fallback, not the plan.

### Recommendation

Use **Scaleway TEM**. It is French and EU-only, so no transfer analysis is needed in the privacy notice. It is effectively free at our volume, has no provider branding in the email, and supports both API and SMTP (a plain `smtplib` or `httpx` call). Set up:
- DKIM (TXT at the selector Scaleway gives you);
- SPF `v=spf1 include:_spf.scw-tem.cloud -all` (`_spf.scw-tem.cloud` resolves to Scaleway TEM ranges as of 2026-09-29, checked with `dig`; confirm against the console);
- DMARC `v=DMARC1; p=none; rua=…`, tightened to `quarantine` later;
- a sender like `connexion@chessop.fr`.

List Scaleway as a processor in the privacy notice. Runner-up: Brevo's free plan, if Scaleway's account verification or domain ramp-up gets in the way.

## 3. Magic-link good practice

The primary sources are OWASP's Forgot Password and Authentication cheat sheets (magic-link sign-in has the same threat model as a reset token) and NIST SP 800-63B-4.

- **Token generation and storage**: "Randomly generated using a cryptographically safe algorithm", "Sufficiently long to protect against brute-force attacks", "Stored securely", "Single use and expire after an appropriate period", "Linked to an individual user in the database" ([OWASP Forgot Password CS](https://cheatsheetseries.owasp.org/cheatsheets/Forgot_Password_Cheat_Sheet.html)). Concretely: `secrets.token_urlsafe(32)` in the link, only `sha256(token)` in SQLite, delete the row on use.
- **Lifetime**: OWASP gives no number. NIST's out-of-band secret rule is "the authentication SHALL be considered invalid unless completed within 10 minutes" and "accept a given authentication secret as valid only once" ([SP 800-63B-4](https://pages.nist.gov/800-63-4/sp800-63b.html), out-of-band devices). Suggest 15 minutes for the link and code, invalidating any earlier pending login for that address when a new one is issued.
- **Email is not a strong authenticator**: NIST says "Email SHALL NOT be used for out-of-band authentication" (password-only mailbox access, interception, DNS rerouting) [SP 800-63B-4 §3.1.3.1]. That is acceptable for a hobby trainer with no money or sensitive data involved, but it is why Lichess OAuth comes first.
- **Link plus code (cross-device)**: OWASP describes both URL tokens and 6-12 digit PINs, which can be "broken up with spaces" for readability [OWASP Forgot Password CS §URL Tokens, §PINs]. Put both in one email:
  - The **link** is for the same device. It opens a confirmation page with a "Sign in" button, and the POST consumes the token.
  - The **6-digit code** is typed into the original tab. This covers opening the email on a phone, or in a mail app's in-app browser that lacks our cookie.
  - The code alone is only 20 bits, so bind it to the pending-login row created in the requesting browser (cookie). NIST: "If the authentication secret is less than 64 bits long, the verifier SHALL implement a rate-limiting mechanism … Generating a new authentication secret SHALL NOT reset the failed authentication count." Cap tries at e.g. 5 per pending login and invalidate it after that. NIST's absolute ceiling is 100 consecutive failures per account [§3.2.2].
- **Link scanners**: corporate mail scanners (e.g. Microsoft Defender Safe Links) pre-fetch URLs and consume tokens that are validated on GET. Supabase documents this as the top cause of "otp_expired" and recommends a confirm-button page or a code ([Supabase troubleshooting](https://supabase.com/docs/guides/troubleshooting/otp-verification-failures-token-has-expired-or-otp_expired-errors-5ee4d0)). So GET must never consume the token.
- **Link hygiene** [OWASP Forgot Password CS §URL Tokens]:
  - Build the URL from a hard-coded base, not the `Host` header ("Host Header Injection").
  - Serve it over HTTPS only.
  - Send `Referrer-Policy: no-referrer` on the landing page.
  - Rate-limit token guessing.
- **Enumeration**: "Return a consistent message for both existent and non-existent accounts" and "Ensure that the time taken for the user response message is uniform", e.g. by sending asynchronously [OWASP Forgot Password CS]. The generic-response rule also covers registration ([OWASP Authentication CS §Authentication Responses](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html)). With sign-up and sign-in merged (unknown address creates an account on first use), the reply is always "Check your inbox". Put the send on a background task so timing does not leak whether the address exists.
- **Rate limiting**: OWASP calls for "rate-limiting on a per-account basis, requiring a CAPTCHA, or other controls", because otherwise an attacker floods the victim's inbox [OWASP Forgot Password CS]. Suggested limits:
  - per address: 3 emails / 15 min, 10 / day;
  - per IP: 10 / hour;
  - globally: a daily cap below the provider quota. This also protects Scaleway sender reputation and the 300-email free tier.
- **Session after sign-in**: "The session ID must be renewed or regenerated … after any privilege level change", and anonymous to authenticated is the canonical case ([OWASP Session Management CS](https://cheatsheetseries.owasp.org/cheatsheets/Session_Management_Cheat_Sheet.html)). This matters for chessop's anonymous-learner merge on adopt (ADR 0002/0004): issue a fresh session cookie when the anonymous learner is adopted into an account.

## Open points

- The new-domain ramp-up ("progressive emailing") numbers are shown in the console. They were not captured here.
- Lichess publishes no numeric rate limit for `/api/token`. Handle a 429 by showing "try again in a minute".
