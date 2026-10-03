# 34: Legal notice, privacy notice and analytics

**What to build:** The hosted site carries what French and EU law require, with no cookie banner. `/legal`: anonymous under LCEN, showing only the host (OVH SAS and its address and phone), that the publisher's identity was given to the host, `contact@chessop.fr`, and three lines of terms; English with a short French version. `/privacy`: plain enough for a 13-year-old, naming the controller (the owner's name is a placeholder the owner fills in) and one entry per processing with purpose, basis, data, recipients and retention, the recipients, the one cookie, the rights, the CNIL, the retention periods, and the opt-out toggle for audience statistics. The GoatCounter snippet is served in hosted mode only when its URL is configured: page views only, referrer reduced to its host, UTM parameters dropped, never the learner cookie or account id; the toggle sets the `skipgc` flag; Do Not Track and Global Privacy Control suppress the count. The Ko-fi link sits in the footer and on the progress page with the line that tips pay for the server and domain and are not tax-deductible. `contact@chessop.fr` is a mail link on `/legal`, `/privacy`, `/data` and `/help` (hosted). A one-page GDPR art. 30 processing register goes in the legal docs. Content follows the French-law research and the spec exactly. (Spec §10, §12, G3.)

**Blocked by:** 28

**Status:** done

- [x] `/legal` and `/privacy` are served in hosted mode with every element the spec lists, and answer 404 in local mode
- [x] The footer links resolve on every hosted page
- [x] The analytics snippet is present only when the URL is configured, and never in local mode
- [x] The privacy page's toggle sets and clears the opt-out flag; DNT and GPC suppress counting
- [x] The Ko-fi line appears on hosted progress
- [x] Hosted `/help` shows the contact address; local `/help` links the repository only
- [x] The processing register exists and names the OVH and Scaleway processor agreements and the backup bucket
