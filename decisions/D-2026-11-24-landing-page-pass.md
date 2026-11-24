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

## Second question

Put to the maintainer by the control room on 2026-11-25, in Swedish, after the second head of the pull request. As the control room passed it on, with its own elisions:

> **A. Ja på alla tre och listan, plus en finputsning (rekommenderas).** Jämna sågtänder på hjulet och en tydligare GitHub-länk. […] **B. Ja som det är** […] **C. Behåll hjulet men ta bort listan.**

Translation: A. Yes to all three and the list, plus a polish (recommended). Even saw teeth on the wheel and a clearer GitHub link. […] B. Yes as it is […] C. Keep the wheel but remove the list.

The three are the further loosenings of the second head: under 780 words outside the CSS, a fourth `h2`, and the attribute `start` on an `<ol>`. The list is the list of the principles on the page.

## Second answer

> ja, du hade ett mycket bättre kugghjul förut. är du fortfarande begränsad av repots regler? känns som att du inte maxar dina visualle förmågor riktigt ... du gjorde ju ett bra ratchet hjul tidigare med animation som var klockren egentligen

Translation: yes, you had a much better cogwheel before. Are you still limited by the repo's rules? It feels as if you are not really using your visual abilities to the full ... you did make a good ratchet wheel earlier, with an animation that was spot on, really.

## What follows

Decided by the two answers:

- `checks/test_pages.py` may hold the page to under 780 words outside its CSS where it held it to under 400, to one `h1` and four `h2` where it held it to two, may allow a link to the list of issues, `/issues`, in that one form, and may allow `start` on an `<ol>`. Nothing links out of the repo, as before.
- The page says "Beta", followed by "Before 1.0, a new version may change the form of your register".
- The page lists the title of each principle, in order, as `generate.py` writes them from `ratchet.json`, with the two lines of `values.json` around them. For the page this reverses the choice of [D-2026-11-23-values-and-principles](D-2026-11-23-values-and-principles.md), which had made the principles a link.
- The figure is the ratchet wheel of the control room's sketches of 2026-11-21, with its animation: a wheel with a numbered notch for each principle, and a pawl that clicks from one to the next and never back.

Proposals (P) until the maintainer has answered them, since no answer names them:

- The animated wheel stays a file of its own, `docs/ratchet-notch.svg`, which an `<img>` loads, and the page's rules on motion stand as they were: the animation runs only for a visitor who has not asked for less motion. The figure may now hold a `<g>`, to group what the animation turns.
- The page's palette gains two colors for the figure, `--signal` for the wheel and `--ink` for the pawl on it. This is an exception to "the accent only on what is clicked", made for the wheel the maintainer asked for: the button remains the one block of color on the first screen.
- The page may hold one inline SVG, the GitHub mark in the link to the repo at the top: an `<svg>` of `<path>` only, with no script, no event handler, no `href`, no style attribute and no text. The link has a border of its own, shows no count of stars, and is not a second button.
- The test gains ties between the page and the repo: "Before 1.0" holds only while the version of `ratchet.json` is below 1.0, "MIT" only while `LICENSE` starts "MIT License", each line of the sample of the dry run is a line that `checks/init.py --check` prints in an empty repo, the principles on the page are those of `ratchet.json`, and the figure has a notch, a stop of the pawl and a delay for each.
- The story and the values stand word for word as `values.json` holds them. They moved below the top of the page.
