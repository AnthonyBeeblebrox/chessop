# What French and EU law require of the site

Type: research
Status: resolved
Blocked by: 
Map: [chessop in public](../map.md)

## Question

For a free, donation-funded website run by a private individual in France, with optional accounts (Lichess identity or email address), stored learning history, and cookieless visitor analytics: what must it provide? Cover, from primary sources (CNIL, Légifrance, GDPR text, EDPB): the **mentions légales** an individual publisher must show under the LCEN and whether they may stay anonymous via their host; the privacy notice's required content; lawful basis for storing history and emails; the CNIL's **consent exemption for audience measurement** and which tools qualify (GoatCounter, Plausible, Matomo configured per CNIL); whether a session cookie for an anonymous learner needs consent; data subject rights to implement (export, deletion) and retention limits; whether hosting outside the EU matters; and whether receiving Ko-fi donations has tax or declaration consequences worth a line in the spec. Write findings with citations to `docs/research/french-legal.md`.

AFK. Fired at charting time. Findings: branch `research/french-legal`, file `docs/research/french-legal.md`.

## Answer

Full findings with citations: `docs/research/french-legal.md` on branch `research/french-legal` (commit c1319c3). Research, not legal advice.

- **Legal notice (mentions légales, LCEN art. 1-1 since 2024-05)**: a non-professional individual may show only the host's name, address and phone, having given their identity to the host. Failing to comply risks 1 year in prison and €75,000.
- **But the privacy notice must name the controller and give a contact**. A name plus email seems enough, so anonymity protects the home address and phone, not the name *(the agent's reading)*.
- **Privacy notice** (GDPR art. 13): purposes, legal bases, recipients, transfers, retention, rights, the right to complain to the CNIL, and the French post-mortem instructions right. Readable by teenagers; the age of digital consent is 15.
- **Legal basis**: contract covers the account, Lichess identity, email and learning history. Legitimate interest covers logs and analytics. No core feature needs consent. Marketing or donation-appeal emails would.
- **Analytics**: the CNIL consent exemption applies with first-party anonymous statistics, no sharing or cross-site tracking, an opt-out, a privacy-notice mention, and at most 25 months of retention. There is no official approved list any more (vendors self-assess). Plausible (with UTM tracking off and referrers cut to the domain), GoatCounter, or Matomo configured per the CNIL guide all fit. "Cookieless" JS still counts as a tracker (EDPB 2/2023), so the exemption conditions still apply.
- **The anonymous-learner cookie needs no consent** if it only holds progress *(by analogy with the CNIL's examples)*. Reusing it for analytics would require consent. With every tracker exempt, **no cookie banner** is needed.
- **Rights and retention**: JSON export, account deletion, email change, analytics opt-out, replies within a month. Delete accounts after about 2 years of inactivity, with a warning first. Keep logs 6–12 months.
- **Hosting**: an EU host plus self-hosted or EU analytics avoids GDPR transfer questions. A US host needs certification under the EU-US Data Privacy Framework or standard contractual clauses.
- **Ko-fi**: regular tips are likely taxable BNC income from the first euro *(the agent's reading)*. The site must not suggest donations are tax-deductible. Regular donation income may weaken the "non-professional" status the anonymity option depends on.
