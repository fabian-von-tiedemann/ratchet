# D-2026-11-24-landing-page-pass: loosen three style limits of the landing page for its first screen and its trust section

- Date: 2026-11-24
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Put to the maintainer in the pull request that adds this file, on 2026-11-24. Until the answer below is filled in, this file is a proposal (P).

The maintainer asked for a small pass on the landing page, `docs/index.html`, so that more people understand what Ratchet is and take a first step: who it is for, what they get and where it stands, one thing to do, and the trust a visitor needs (license, who is behind it, where questions go). The pass keeps every check of `checks/test_pages.py` that guards what the page may say or load. It needs three of that test's limits on style loosened. May they be loosened as follows? Recommended: yes to all three.

1. The words. The page had to hold under 400 words outside its CSS. It now holds 549, and the limit becomes under 560. The added words are the line on who it is for and what you get, the line on the status, the sample of what the dry run prints, and the four lines on who is behind it.
2. The headings. The page had to hold one `h1` and two `h2`. It now holds one `h1` and three `h2`: "Who is behind it" is the third.
3. The links. A link into the repo could go to the repo, a file or a directory on `main`, a pull request, an issue or the latest release. It may now also go to the list of issues, `/issues`, in that one form, because that is where a question is asked. Nothing links out of the repo, as before.

One exact string of the test changes with them and loosens nothing: the one button reads "Try it on your repo" where it read "Start here". The test now also fails on a second link of the class `button`.

## Answer

To be filled in on approval: the control room writes the maintainer's answer here, verbatim, before the pull request is merged.

## What follows

Proposals (P) until the pull request is merged:

- `checks/test_pages.py` states the three new limits exactly and fails on a breach of each: 560 words or more, headings other than one `h1` and three `h2`, and a link into the repo of another form, such as `/issues/new` or `/pulls`.
- The test gains three ties between the top of the page and the repo: "Before 1.0" holds only while the version of `ratchet.json` is below 1.0, "MIT" only while `LICENSE` starts "MIT License", and each line of the sample of the dry run is a line that `checks/init.py --check` prints in an empty repo.
- The story and the values stand word for word as `values.json` holds them ([D-2026-11-23-values-and-principles](D-2026-11-23-values-and-principles.md)). They moved below the top of the page.
