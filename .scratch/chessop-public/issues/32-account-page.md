# 32: Account page

**What to build:** The account page lets a signed-in learner sign out, change their email, or delete their account. Change email (email accounts only) sends a confirm link to the new address with the same mechanics as sign-in, and is refused if another account holds that address without revealing so beyond the page's own message. Delete my account asks for confirmation, then at once removes the learner, their history, their identity and every session on every device. (Spec §5.)

**Blocked by:** 29

**Status:** done

- [x] The account page shows the identity and kind, and is reachable from the header
- [x] Changing email takes effect only after the confirm link sent to the new address; the old address then no longer signs in to this account
- [x] A change to an address another account holds is refused
- [x] Lichess accounts see no change-email control
- [x] Deleting the account removes everything and a second signed-in client is signed out on its next request
