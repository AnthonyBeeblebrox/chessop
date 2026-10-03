# 40: Scaleway mailer and notify-owner

**What to build:** On the real site, mail is sent through Scaleway Transactional Email's HTTP API, in the background, from `CHESSOP_MAIL_FROM`. The TEM key and project id are required when the base URL is `https` and optional on `http`, where the console mailer stays. `chessop notify-owner --subject …` reads a body on stdin and sends it to `CHESSOP_OWNER_EMAIL` through the same mailer; it reads the same environment as `serve --hosted`. A send failure is logged as an error without the recipient's address being lost to the caller's flow: sign-in still answers "check your inbox". (Spec §1, §5, §13, G2.)

**Blocked by:** 29

**Status:** done

- [x] With an `https` base URL and no TEM key, startup refuses and names the missing variables
- [x] The TEM mailer posts the expected request (asserted against a stubbed HTTP endpoint) and never blocks the request that triggered it
- [x] `notify-owner` sends stdin as the body with the given subject to the owner's address, and exits non-zero on failure
- [x] On an `http` base URL with no key, `notify-owner` prints the message to the console
