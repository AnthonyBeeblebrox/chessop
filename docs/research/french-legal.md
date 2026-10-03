# French legal obligations for the public chessop site

Research question: what must a free, donation-funded website run by a private individual in France provide, given optional accounts (Lichess OAuth or email magic link), stored per-learner learning history, an anonymous-learner session cookie, and cookieless visitor analytics? Date: 2026-09-29. All sources accessed 2026-09-29 unless noted.

This is research, not legal advice. Where a question turns on facts about chessop that are not settled yet (who hosts it, whether donations become regular income), the note says what changes the answer.

## Summary

1. **Mentions légales (LCEN art. 1-1, in force since 2024-05-23).** A publisher who is a natural person must show name, first names, home address and phone number, the publication director, and the host's name, address and phone number. A publisher acting **non-professionally** may stay anonymous by showing only the host's details, *provided they have given their own identity to that host*. Failing to comply carries up to 1 year in prison and a €75,000 fine (art. 1-2). Taking donations probably doesn't make the site "professional" on its own, but regular, organised income would weaken that argument (see §8).
2. **Privacy notice.** GDPR art. 13 sets the content: controller identity and contact, the purposes and legal basis of each processing, recipients, transfers outside the EU, retention periods, the data subject rights, the right to complain to the CNIL, and whether giving the data is required. French law adds one item: the right to set **post-mortem directives** (Loi Informatique et Libertés art. 48 and 85).
3. **Legal basis.** Account data (email, Lichess username) and the learning history of a signed-in learner fall under **contract** (GDPR art. 6(1)(b)), because the history *is* the service asked for. Anonymous-learner history is best based on contract or legitimate interest. Consent isn't needed for any of the core features. Sending marketing email would need separate consent.
4. **Audience measurement without consent.** The CNIL exempts it from consent when it is used only for the publisher's own audience statistics, produces only anonymous statistics, is not cross-referenced or shared, and does not track across sites. The CNIL also recommends: tell users in the privacy notice, offer an opt-out, keep data at most 25 months, and cap cookie lifetime at 13 months. The CNIL **no longer publishes a list of approved tools**: vendors self-assess using its July 2025 tool. The CNIL does host a Matomo configuration guide. From their own documentation, Plausible and GoatCounter look designed to meet the CNIL's hash criteria (a site-specific identifier with a time limit). The publisher still has to check the configuration.
5. **"Cookieless" does not mean outside the cookie rules.** EDPB Guidelines 2/2023 (adopted 2024-10-07) say that JavaScript telling the browser to send identifiers counts as "gaining access" under ePrivacy art. 5(3), so the CNIL exemption conditions still apply to cookieless analytics.
6. **Anonymous-learner session cookie.** No consent is needed if the cookie is used **only** to provide the trainer the learner is actively using: it keeps their progress, the same way authentication or shopping-cart cookies are exempt (CNIL guidelines 2020-091 §46–49). If the same cookie is used for anything else, including analytics, consent is needed (§48). It still has to be described in the privacy notice.
7. **Rights and retention.** Implement: access plus an **export** in a structured, machine-readable format (art. 15 and 20), **deletion** (art. 17), correction (art. 16), objection where legitimate interest is used (art. 21), and replies within one month (art. 12(3)). The CNIL considers deleting accounts after **2 years of inactivity** proportionate, with a warning sent to the user first.
8. **Hosting outside the EU** is allowed, but it becomes a GDPR chapter V transfer. A US host certified under the EU-US Data Privacy Framework is covered by the adequacy decision (EU) 2023/1795, which the General Court upheld on 2025-09-03 (T-553/23 Latombe). Any other non-EU host needs standard contractual clauses. An EU host avoids the question entirely. In every case, the host's identity goes in the mentions légales.
9. **Ko-fi donations.** Tax authorities treat regular tips received through an online activity as taxable income (BNC, CGI art. 92), declared from the first euro. If a gift were treated as a true gratuitous gift (*don manuel*), the recipient would have to declare it, and the tax rate between non-relatives is **60% with no allowance**. The site cannot issue tax receipts to donors (CGI art. 200 is reserved for eligible organisations). Donations should not be described as tax-deductible.

## 1. Mentions légales (LCEN)

Since the SREN law (loi n° 2024-449), the publisher-identification duty moved from LCEN art. 6 III to **art. 1-1** of loi n° 2004-575, in force since 2024-05-23 ([Légifrance, art. 1-1](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000049568614)). Art. 6 III now covers only access providers and hosts ([Légifrance, art. 6, version of 2026-08-26](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000042038977)).

**Art. 1-1 I** requires anyone whose activity is publishing an online public communication service to make the following available in an open standard:
- if a natural person: name, first names, home address, phone number, and a trade/business register number if registered;
- the name of the **directeur de la publication** (for an individual, themselves);
- the **host's** name, *dénomination* or *raison sociale*, address and phone number.

**Art. 1-1 II (anonymity).** People publishing **on a non-professional basis** may keep their anonymity and show only the host's name, *dénomination* or *raison sociale* and address. This works only if they have given the host the personal identification details listed in I. The host is bound by professional secrecy (Penal Code art. 226-13 and 226-14), except towards the judicial authority ([Légifrance, art. 1-1](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000049568614)).

**Art. 1-1 III** creates a right of reply: the publication director must publish a reply within 3 days of receiving it. The penalty is a €3,750 fine (same source). A site with user-generated content would need a contact channel for this. chessop has none, but the mentions page should still give a contact address.

**Penalty (art. 1-2).** Failing to comply with art. 1-1 I or II is punished by one year in prison and a €75,000 fine ([Légifrance, art. 1-2](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000049568616)). The CNIL summarises the point as "Tout site web doit permettre d'identifier son responsable et son hébergeur", and says the mentions légales are separate from the GDPR privacy notice ([CNIL, "Les mentions légales sur un site web, est-ce obligatoire ?"](https://www.cnil.fr/fr/cnil-direct/question/les-mentions-legales-sur-un-site-web-est-ce-obligatoire)).

**Tension with the privacy notice.** The GDPR art. 13 privacy notice must name the **controller** and give their contact details (§2). An anonymous LCEN notice does not remove that duty. In practice the GDPR identity requirement can be met with a name and a dedicated contact email. It does not demand a home address. The LCEN option protects the home address and phone number, not the controller's name. This is an inference from reading both texts together; no source found addresses the combination directly.

**"Non-professional" and donations.** Art. 1-1 II doesn't define the term. §8 shows that regular donations can be taxed as income from an activity. A cautious reading: an unregistered individual who takes voluntary donations and sells nothing can use II. Registering as a business (e.g. micro-entrepreneur) would bring in art. 1-1 I and the register number.

## 2. Privacy notice content

The GDPR applies: the controller is established in France (GDPR art. 3(1)). Publishing to the whole internet is not a purely household activity (art. 2(2)(c)). Source for all GDPR articles: [Regulation (EU) 2016/679, EUR-Lex](https://eur-lex.europa.eu/eli/reg/2016/679/oj).

**GDPR art. 13(1)**, required when the data is collected:
- (a) identity and contact details of the controller;
- (b) DPO contact details, if there is a DPO (not required here: art. 37 does not apply to a small site with no large-scale monitoring or special-category data);
- (c) the purposes and legal basis of each processing;
- (d) the legitimate interests pursued, where art. 6(1)(f) is used;
- (e) recipients or categories of recipients (host, email-sending provider, analytics provider, Lichess for OAuth);
- (f) any transfer outside the EU and what it relies on (adequacy decision or safeguards).

**Art. 13(2):**
- (a) retention period, or the criteria used to set it;
- (b) the rights of access, rectification, erasure, restriction, objection and portability;
- (c) the right to withdraw consent, if any processing is based on consent;
- (d) the right to lodge a complaint with a supervisory authority (the CNIL);
- (e) whether providing the data is a contractual requirement, and what happens if it isn't provided;
- (f) whether there is automated decision-making. There is none here; the notice can say so.

**Art. 12(1):** concise, transparent, intelligible and easily accessible, in clear and plain language, especially when addressed to a child.

**French addition.** Loi n° 78-17 art. 48 requires informing people of their right to set directives on what happens to their data after their death, under art. 85 ([Légifrance, art. 48](https://www.legifrance.gouv.fr/loda/article_lc/LEGIARTI000043887431); [art. 85](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000039280582/2021-02-13)).

**Trackers.** The CNIL recommends that even consent-exempt trackers are described in the privacy notice ([CNIL, "Cookies : solutions pour les outils de mesure d'audience", 2025-07-04](https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies-solutions-pour-les-outils-de-mesure-daudience)).

**Children.** Chess learners include minors. Loi 78-17 art. 45 sets 15 as the age at which a minor can consent alone to information-society services under GDPR art. 8. Below 15, consent must be given jointly with a parent ([Légifrance, art. 45](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037823135)). This only matters for processing **based on consent**. The recommended design (§3) doesn't rely on consent, but the notice should be written so a young teenager can follow it (art. 12(1); art. 45).

**Record of processing.** GDPR art. 30(5) exempts organisations with fewer than 250 employees *unless* the processing is not occasional. Account and learning-history processing is continuous, so a short register is required. It can be a single page.

## 3. Legal basis for learning history and email addresses

| Data | Suggested basis | Why |
|---|---|---|
| Email address (magic-link sign-in) | Art. 6(1)(b) contract | Needed to deliver the sign-in the user asked for. |
| Lichess user id and username (OAuth) | Art. 6(1)(b) contract | Same reasoning; only request the scopes you use. |
| Learning history of a signed-in learner | Art. 6(1)(b) contract | The stored history *is* the feature: spaced review and progress. |
| Learning history under the anonymous cookie | Art. 6(1)(b), or (f) legitimate interest | Pseudonymous data is still personal data. Contract fits if the history is the service asked for. |
| Server and security logs | Art. 6(1)(f) legitimate interest | Security of the service. The CNIL treats 6 months to 1 year as a reference retention period ([CNIL, journalisation recommendation](https://www.cnil.fr/fr/la-cnil-publie-une-recommandation-relative-aux-mesures-de-journalisation)). |
| Audience statistics | Art. 6(1)(f) | Within the CNIL exemption. Offering an opt-out covers the art. 21 right to object. |

Art. 6(1)(b) covers processing "necessary for the performance of a contract to which the data subject is party or in order to take steps at the request of the data subject prior to entering into a contract" (GDPR, EUR-Lex above). Using an email address for anything beyond sign-in and service messages would need its own basis, and marketing email would need consent. Free, donation-funded service terms still count as a contract for this purpose. Donation appeals by email would be marketing.

## 4. Cookie-less audience measurement: the CNIL exemption

### Legal hook

Loi 78-17 art. 82 (transposing ePrivacy Directive art. 5(3)) requires consent before reading or writing on a user's device. There are two exceptions: operations whose sole purpose is to carry the communication, and operations "strictement nécessaire à la fourniture d'un service de communication en ligne à la demande expresse de l'utilisateur" ([CNIL guidelines, délibération 2020-091, §3–4 and §46](https://www.cnil.fr/sites/default/files/atoms/files/lignes_directrices_de_la_cnil_sur_les_cookies_et_autres_traceurs.pdf)). Guidelines §50–52 treat audience measurement limited to the publisher's own statistics as strictly necessary. §52 adds that it remains a processing of personal data subject to the GDPR.

### Conditions ([CNIL page, 2025-07-04](https://www.cnil.fr/fr/cookies-et-autres-traceurs/regles/cookies-solutions-pour-les-outils-de-mesure-daudience))

The trackers **must**:
- be used only to measure the site's audience, on the publisher's exclusive behalf;
- produce only anonymous statistics.

The trackers **must not**:
- lead to cross-referencing with other processing, or pass non-anonymous data to third parties;
- allow tracking of a person across sites or apps.

**CNIL recommendations:**
- inform users, e.g. in the privacy notice;
- limit tracker lifetime (for example 13 months) and do not extend it automatically on new visits;
- keep collected data at most **25 months**;
- review these durations periodically.

The page also warns about **data transfers outside the EU** by the analytics vendor.

### Is there a list of approved tools? No, not any more

The CNIL now offers a **self-assessment tool** for vendors. Vendors may say "D'après notre auto-évaluation, la solution XXX est conforme aux critères établis par la CNIL… si elle est correctement configurée". They may not present a product as "certifiée" or "validée par la CNIL". Publishers are told to ask their vendor for supporting documentation (same CNIL page). Pages listing "CNIL-approved" tools are out of date or secondary.

The self-assessment tool ([CNIL, "Outil d'auto-évaluation", July 2025](https://www.cnil.fr/sites/default/files/2025-07/outil_d_auto-evaluation_mesure_d_audience.pdf)) spells out criteria that decide the cookieless tools:
- Collect at most page views, feature use (clicks) and load/scroll/time statistics. Minimise HTTP-header data, e.g. keep only the major OS or browser version.
- No import of CRM ids, UTM or campaign ids. The referrer, if collected, is limited to the host.
- IP: city-level geolocation at most, then pseudonymised by removing at least the last byte.
- **Any fingerprint-style identifier must include a site-specific component (e.g. the domain) and a time component**, so it cannot follow people across sites and has a limited lifetime.
- Reports show only anonymous statistics, rounded to the nearest ten or otherwise shown to be anonymous. No session replay.
- **Right to object:** where personal data is processed, provide an opt-out link or button in the privacy notice, and make it last (an opt-out cookie, or a blocklist of the fingerprint).
- The vendor acts as processor under an art. 28 DPA and does not reuse the data for itself.

### The three candidate tools

- **Matomo.** The CNIL hosts a vendor configuration guide ([CNIL-hosted Matomo guide](https://www.cnil.fr/sites/default/files/atoms/files/matomo_analytics_-_exemption_-_guide_de_configuration.pdf)). Steps:
  1. Turn off Visits log and Visitor profile.
  2. Add an opt-out to the privacy notice.
  3. Keep IP anonymisation on (the default removes 2 bytes).
  4. No third-party cookies or cross-domain tracking.
  5. No User ID tracking, which needs consent. For chessop this means **never sending the learner account id to Matomo**.
  6. No e-commerce tracking.
  7. Turn off heatmaps and session recording.
  8. Keep personal data out of URLs, titles and custom dimensions.

  Matomo uses first-party cookies by default. Self-hosting keeps the data with the publisher.
- **Plausible.** Per Plausible's own policy, it uses no cookies or local storage and counts visitors with `hash(daily_salt + website_domain + ip_address + user_agent)`. The salt is deleted every 24 hours, and raw IPs and User-Agents are not stored. Data is stored in the EU and the company is incorporated in Estonia ([Plausible data policy](https://plausible.io/data-policy)). This satisfies the CNIL's site-plus-time hash criterion. Two points to check: Plausible collects UTM/campaign parameters and referrers, while the self-assessment wants UTMs off and referrers limited to the host. Plausible does not claim a CNIL self-assessment in that document.
- **GoatCounter.** The session key is built from site id, User-Agent and IP. It is held only in memory for 8 hours, mapped to a random UUID, and IP and User-Agent are never written to disk ([GoatCounter, sessions](https://www.goatcounter.com/help/sessions)). It stores aggregates rather than individual page views ([GoatCounter, GDPR](https://www.goatcounter.com/help/gdpr)). This is site-specific and time-limited. The author's own view is only that GoatCounter "*probably* doesn't require a GDPR consent notice"; there is no CNIL self-assessment. Self-hosting GoatCounter on the chessop host removes the processor and transfer questions.

### Why "cookieless" still falls under the rule

EDPB Guidelines 2/2023 (final version adopted 2024-10-07), §51: for dynamically built pixels "it is the distribution of the applicative logic (usually a JavaScript code) that constitutes the instruction", so collecting the identifiers is "a 'gaining of access' in the meaning of Article 5(3) ePD". §55: IP addresses count too unless the entity can show they don't come from the user's device. §56: being within scope "does not systematically mean that consent needs to be collected" ([EDPB Guidelines 2/2023 v2](https://www.edpb.europa.eu/system/files/documents/2024-10/edpb_guidelines_202302_technical_scope_art_53_eprivacydirective_v2_en_0.pdf)). So chessop should treat its analytics script as a tracker that qualifies for the art. 82 exemption, not as something outside art. 82. It still needs a mention in the privacy notice and an opt-out.

## 5. The anonymous-learner session cookie

CNIL guidelines §49 list, among trackers that may be exempt from consent:
- trackers keeping the user's cookie choice;
- **authentication** trackers, including those securing the authentication;
- **shopping-cart** trackers;
- **interface-personalisation** trackers "lorsqu'une telle personnalisation constitue un élément intrinsèque et attendu du service";
- load-balancing trackers;
- paywall-sample trackers;
- some audience-measurement trackers.

The list is introduced with "notamment", so it is not exhaustive ([délibération 2020-091](https://www.cnil.fr/sites/default/files/atoms/files/lignes_directrices_de_la_cnil_sur_les_cookies_et_autres_traceurs.pdf)).

A cookie that ties an anonymous learner to their own progress, on a trainer they are using, does the same job as an authentication or cart cookie. It is strictly necessary for the service they asked for, so **no consent is needed**. This is an inference by analogy; the CNIL list has no "learning progress" entry.

Conditions:
- **Use it for that one purpose only.** §48: using one tracker for several purposes, some outside the exemptions, requires consent. Never reuse it as an analytics id or send it to the analytics tool.
- First-party, with a lifetime matched to the purpose. The server-side record expires with it (§7).
- Describe it in the privacy notice. The history it points to is personal data (§3).

No cookie banner is then needed at all: every tracker is exempt.

## 6. Data subject rights

From GDPR (EUR-Lex above):
- **Art. 12(3):** answer within one month; this can be extended by two months for complex requests. Free of charge.
- **Art. 15 access** and **art. 20 portability.** For data provided by the user and processed on the basis of contract or consent by automated means, provide it "in a structured, commonly used and machine-readable format". A JSON download of the account's learning history and settings covers both.
- **Art. 16 rectification:** let the user change their email address.
- **Art. 17 erasure:** a "delete my account" action that removes the account, email address, Lichess link and learning history. Backups should roll off within a stated period.
- **Art. 21 objection:** relevant to legitimate-interest processing, i.e. analytics (the opt-out) and logs.
- Anonymous learners: offer "forget this browser's history" (clear the cookie and delete the server record) and an export. Identifying who is asking is limited to whoever holds the cookie, which is acceptable under art. 11.

**Retention for inactive accounts.** The CNIL considers deleting accounts with no user action for **two years** proportionate. Users should be warned before the deadline so they can keep the account. The CNIL also describes a variant where the account is deactivated and archived, with reactivation possible ([CNIL, "Achat de contenus numériques : quelle durée de conservation des comptes inactifs ?", 2025-09-18](https://www.cnil.fr/fr/achat-de-contenus-numeriques-quelle-duree-de-conservation-des-comptes-inactifs)). That page is written for purchased digital content, but its 2-year benchmark is the CNIL's general position for online accounts. Suggested spec:
- signed-in accounts: delete after 24 months of inactivity, with a warning email sent about 30 days earlier;
- anonymous histories: have no email to warn with, so a shorter period is defensible, e.g. delete when the cookie expires or after 13 months of inactivity;
- analytics: at most 25 months;
- logs: 6–12 months.

## 7. Hosting outside the EU

Nothing in the LCEN or the GDPR requires EU hosting. The LCEN only requires the host's identity in the mentions légales (§1). Under the GDPR, sending personal data to a non-EU host or processor is a transfer under Chapter V (art. 44–49). It needs one of the following:
- an **adequacy decision** (art. 45). For the US this means the Data Privacy Framework, Commission Implementing Decision (EU) 2023/1795, which covers only DPF-certified US companies. The General Court dismissed the annulment action on 2025-09-03 ([CJEU press release 106/25, T-553/23 Latombe v Commission](https://curia.europa.eu/site/upload/docs/application/pdf/2025-09/cp250106en.pdf)). Check whether an appeal is pending before relying on it for the long term.
- appropriate safeguards (art. 46), typically standard contractual clauses in the host's DPA, plus a transfer impact assessment.

Either way the privacy notice must name the transfer and what it relies on (art. 13(1)(f)). The host needs an art. 28 processor agreement wherever it is. The CNIL analytics page separately flags transfers by analytics vendors. **Simplest spec choice: an EU host and EU or self-hosted analytics.** This avoids Chapter V except for the Lichess OAuth call. That call is the user's own request to Lichess, which is based in France.

## 8. Ko-fi donations: tax points worth noting

- **Probably taxable income, not gifts.** CGI art. 92 taxes as BNC "toutes occupations, exploitations lucratives et sources de profits ne se rattachant pas à une autre catégorie" ([Légifrance, CGI art. 92](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000044983291)). The Ministry of the Economy says all income from content-creator activity is taxable "dès le premier euro", as BNC when no goods or services are promoted ([economie.gouv.fr, "Ai-je une activité d'influence commerciale…"](https://www.economie.gouv.fr/suis-je-influenceur-demarches)). No primary source was found that rules specifically on voluntary tips to a free website. The official line on creator income, together with the catch-all in art. 92, points to **declaring Ko-fi receipts as BNC** on the annual return. Small amounts fit the micro-BNC regime.
- **If treated as gifts instead:** the recipient must declare a *don manuel*. From 2026-01-01 the declaration must be made online ([impots.gouv.fr, "Don manuel", modified 2026-03-20](https://www.impots.gouv.fr/particulier/don-manuel); [form 2735](https://www.impots.gouv.fr/formulaire/2735/declaration-de-dons-manuels-et-de-sommes-dargent), CGI art. 635 A and 790 G). Gifts between non-relatives are taxed at **60% with no allowance** ([service-public.gouv.fr F14203, updated 2026-05-13](https://www.service-public.gouv.fr/particuliers/vosdroits/F14203)). This treatment is worse, which is another reason the income reading above is the realistic one.
- **No tax receipts for donors.** The income-tax reduction for donations applies only to eligible organisations, which issue form 2041-RD receipts ([BOFiP BOI-IR-RICI-250-30](https://bofip.impots.gouv.fr/bofip/5873-PGP.html/identifiant=BOI-IR-RICI-250-30-20250715)). The site must not suggest donations are tax-deductible.
- **Interaction with §1:** regular, organised income can make the activity look "professional". This matters for the LCEN anonymity option and could raise registration questions. Small, irregular tips on a hobby project are the weakest case for that. Confirm with an *expert-comptable* if amounts grow.
- **Donor data:** Ko-fi processes donors' data as its own controller. If chessop receives donor names or emails, for example through Ko-fi webhooks, that is processing to list in the privacy notice and register.

## Checklist for the spec

**Mentions légales page**
- [ ] Publisher: full identity (name, address, phone) **or**, if non-professional, the anonymity option: host details only, with a note that the publisher's identity has been given to the host.
- [ ] Directeur de la publication (the publisher's name, or unnamed under the anonymity option).
- [ ] Host: name, address, phone.
- [ ] Contact email.

**Privacy notice (linked from every page and from sign-in)**
- [ ] Controller identity and contact email.
- [ ] One entry per processing, each with its purpose, legal basis, data, recipients and retention:
  - [ ] accounts via email magic link;
  - [ ] accounts via Lichess OAuth;
  - [ ] signed-in learning history;
  - [ ] anonymous-learner history and cookie;
  - [ ] server logs;
  - [ ] audience statistics;
  - [ ] donations (Ko-fi).
- [ ] Transfers outside the EU and their basis, or a statement that there are none.
- [ ] Rights: access, export, rectification, erasure, restriction, objection, complaint to the CNIL, and post-mortem directives (art. 85).
- [ ] Cookie and tracker list, with the analytics **opt-out link or button**.
- [ ] Plain language that a 13–15-year-old can follow.

**Product features**
- [ ] "Export my data": JSON of account and learning history (signed-in and anonymous).
- [ ] "Delete my account / forget this browser": hard-deletes server-side data.
- [ ] Email change.
- [ ] Inactive-account job: warning email about 30 days before, deletion at 24 months. Anonymous records expire at 13 months or with the cookie.
- [ ] Analytics opt-out that lasts.

**Cookies and analytics**
- [ ] Session or learner cookie: first-party, used only to authenticate or hold progress, never reused for analytics. No banner needed.
- [ ] Analytics configured to CNIL criteria:
  - [ ] no user or learner ids;
  - [ ] no UTMs;
  - [ ] referrer limited to the host;
  - [ ] site-specific, time-limited hash;
  - [ ] data kept at most 25 months;
  - [ ] vendor DPA, or self-hosted.

**Hosting and paperwork**
- [ ] Prefer an EU host (and EU or self-hosted analytics). Otherwise rely on DPF certification or SCCs and name the transfer.
- [ ] Processor DPAs with the host, the email provider and the analytics vendor (art. 28).
- [ ] One-page record of processing (art. 30).
- [ ] Log retention of 6–12 months.

**Donations**
- [ ] Ko-fi link wording: voluntary support, no tax receipt, not tax-deductible.
- [ ] Publisher note, outside the product: declare Ko-fi receipts as BNC income and keep a yearly total.
