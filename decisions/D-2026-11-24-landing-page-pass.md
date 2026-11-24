# D-2026-11-24-landing-page-pass: the landing page's first screen, its trust section and the word "Beta"

- Date: 2026-11-24
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Put to the maintainer by the control room on 2026-11-24, in Swedish, after the first head of the pull request that adds this file. As the control room passed it on, with its own elision:

> **Fyra saker behöver ditt beslut.** Jag rekommenderar ja på alla: 1. **Ordtaket höjs** från under 400 till under 560 ord. Sidan har nu 549. 2. **Sidan får en rubrik till**, så att "Who is behind it" får en egen. 3. **En länk till ärendelistan på GitHub tillåts**, för frågor. 4. **Ratchet beskrivs som "Beta"**, följt av "Before 1.0, a new version may change the form of your register." […] Svara till exempel **"ja på alla fyra"**, eller säg vad du vill ändra.

Translation: Four things need your decision. I recommend yes to all: 1. The word cap is raised from under 400 to under 560 words. The page now has 549. 2. The page gets one more heading, so that "Who is behind it" has its own. 3. A link to the list of issues on GitHub is allowed, for questions. 4. Ratchet is described as "Beta", followed by "Before 1.0, a new version may change the form of your register." […] Answer for example "yes to all four", or say what you want to change.

## Answer

> ja på alla fyra. gärna visualisering av en ratchet. kanske med alla primciper? Kan vi ha en github-länk? Är du med så att det syns tydligt? Även om vi inte har några stars än ...

Translation: yes to all four. A visualization of a ratchet would be welcome. Perhaps with all the principles? Can we have a GitHub link? Are you with me, so that it shows clearly? Even though we have no stars yet ...

## What follows

Decided by the answer:

- `checks/test_pages.py` may hold the page to under 560 words outside its CSS where it held it to under 400, to one `h1` and three `h2` where it held it to two, and may allow a link to the list of issues, `/issues`, in that one form. Nothing links out of the repo, as before.
- The page says "Beta", followed by "Before 1.0, a new version may change the form of your register".

Proposals (P) until the maintainer has answered them, since the yes covers the four things named and the rest of the answer asks for work without naming a limit:

- The visualization is the page's one figure, a ratchet wheel with a numbered tooth for each principle and a pawl, in place of the staircase. Under it the page lists the title of each principle, in order, as `generate.py` writes them from `ratchet.json`, with the two lines of `values.json` around them. This puts the principles back on the page, where [D-2026-11-23-values-and-principles](D-2026-11-23-values-and-principles.md) had made them a link.
- That list needs two further loosenings: under 780 words where the answer allowed under 560 (the page has 761), and a fourth `h2`, "The principles".
- The GitHub link stands at the top of the page, opposite the logo, as the word "GitHub", with no count of stars and no mark: the page may hold no inline SVG, and a second file in `docs/` would need a strict reader of its own.
- The test gains ties between the page and the repo: "Before 1.0" holds only while the version of `ratchet.json` is below 1.0, "MIT" only while `LICENSE` starts "MIT License", each line of the sample of the dry run is a line that `checks/init.py --check` prints in an empty repo, the principles on the page are those of `ratchet.json`, and the figure has a tooth for each.
- The story and the values stand word for word as `values.json` holds them. They moved below the top of the page.
