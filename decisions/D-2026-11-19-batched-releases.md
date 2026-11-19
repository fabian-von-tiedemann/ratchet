# D-2026-11-19-batched-releases: changes are collected under an unreleased version and released together

- Date: 2026-11-19
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Ratchet had made eight releases in four days. One of them, 0.8, only moved two pins in the list of sources. Five choices were put to the maintainer together, each with a recommendation. They came after this text.

Original, in Swedish:

> Ja, du har rätt. Vi följer semver formellt, men vi släpper alldeles för ofta.

> **Grundorsaken är en koppling i kontrollerna, inte att vi har bråttom.** Varje ändring i `ratchet.json` kräver en ny version, och en ny version på `main` publiceras direkt vid sammanslagningen. Det går alltså inte att samla ihop ändringar.

Translation into English:

> Yes, you are right. We follow semver formally, but we release far too often.

> **The root cause is a coupling in the checks, not that we are in a hurry.** Every change to `ratchet.json` requires a new version, and a new version on `main` is published as soon as it is merged. So changes cannot be collected.

The choices. Original, in Swedish:

> 1. **Ändringar samlas och släpps när det finns tillräckligt.** Nästa version står i ändringsloggen som `## 0.9 (unreleased)`, och PR:er lägger sina ändringar där. Släppflödet publicerar inget så länge rubriken säger `unreleased`. Själva släppet blir en egen liten PR som sätter datum, och den slår jag bara ihop på ditt ja: "släpp 0.9". **Råd: ja.**
> 2. **Takt: högst ett släpp i veckan**, eller när du ber om det. Ett säkerhetsfel släpps direkt. **Råd: ja.**
> 3. **Listan med källor flyttas ut ur `ratchet.json`**, till en egen fil som inte ingår i det som släpps. En framflyttad källa ger då aldrig någon ny version. **Råd: ja.**
> 4. **Ingen patchnivå (0.9.1) nu.** Med samlade släpp behövs den inte, och den skulle kräva ändringar i flera kontroller. **Råd: nej.**
> 5. **Vi bestämmer vad 1.0 betyder.** Jag skriver ett utkast till beslut med kriterier som du tar ställning till: formen har varit oförändrad i några veckor, Ratchet kommer igång med ett kommando, minst en annan repo använder det, och en viss andel av kärnan har kontroller. **Råd: ja.**

Translation into English:

> 1. **Changes are collected and released when there is enough.** The next version stands in the changelog as `## 0.9 (unreleased)`, and PRs add their changes there. The release workflow publishes nothing as long as the heading says `unreleased`. The release itself becomes a small PR of its own that sets the date, and I merge it only on your yes: "release 0.9". **Advice: yes.**
> 2. **Pace: at most one release a week**, or when you ask for one. A security fault is released at once. **Advice: yes.**
> 3. **The list of sources moves out of `ratchet.json`**, into a file of its own that is not part of what is released. A pin that moves then never gives a new version. **Advice: yes.**
> 4. **No patch level (0.9.1) for now.** With collected releases it is not needed, and it would require changes in several checks. **Advice: no.**
> 5. **We decide what 1.0 means.** I write a draft decision with criteria for you to take a position on: the form has been unchanged for some weeks, Ratchet gets going with one command, at least one other repo uses it, and a certain share of the core has checks. **Advice: yes.**

## Answer

Original, in Swedish:

> ok ja på dina reks

Translation into English:

> ok yes to your recommendations

So choices 1, 2, 3 and 5 are taken, and choice 4 is not: there is no patch level.

## What follows

- **1 and 3 are built in the PR that records this decision.** The first entry of `CHANGELOG.md` may be headed `## <version> (unreleased)`. While it is, the release workflow publishes nothing for that version, and `ratchet.json` may name it and change. The release is a PR that replaces `(unreleased)` with the date. Its merge publishes the version, and from its tag on the version is frozen as before. The list of sources moves to `sources.json`, which `checks/released_text.py` does not compare with a tag, so a pin that moves needs no version.
- **2 is a practice that the control room follows. It is text only.** No check counts releases. The control room proposes a release at most once a week, or when the maintainer asks, and a fix for a security fault is released at once.
- **4: nothing.** Versions stay `MAJOR.MINOR`.
- **5 is a separate draft decision, later.** It is written as a proposal with the criteria above, for the maintainer to take a position on.

Observation (O): item 3 of [D-2026-11-17-new-approaches](D-2026-11-17-new-approaches.md) chose a version for each change, so that no heading `## Unreleased` was needed, because such a heading had been the way released text was rewritten. This decision brings back an unreleased heading, in one exact form, only for the first entry. Released text stays protected as before: an entry is compared with its tag from the tag on, and an entry with a date is published by the next push to `main`.

Proposal (P), which the maintainer did not decide, and which the PR builds: the date of a version is no longer in `ratchet.json`, only in the heading of its entry in `CHANGELOG.md`, so that the release PR sets it in one place. `date` and `sources` leave `ratchet.json`, a change of form that a minor version before 1.0 may make ([D-2026-11-18-form-change-before-1-0](D-2026-11-18-form-change-before-1-0.md)), and the changelog lists it.

## Round 2 of the review

The review from another model family of [PR #50](https://github.com/fabian-von-tiedemann/ratchet/pull/50), round 1, found three faults in what the PR built. They are fixed in the same PR, and change nothing that the maintainer decided.

- Observation (O): a version dated on `main` and then headed `(unreleased)` again, with the run of the dated commit cancelled before it tagged, passed every later run with no tag. Now, once a commit on `main` has dated a version, it must be released whatever the head says: a head that heads it `(unreleased)` again fails and names the commit that dated it.
- Observation (O): the pull request of a release moves the command in `README.md` that fetches Ratchet to the version it dates, before the tag exists. So the claim that the command never fetches a tag that does not exist yet was false. The claim is now narrower: the command names the newest version with a date, whose tag the release run creates after the merge. For the minutes that run takes, the command fails, and longer if the run is cancelled, while the daily release run is red.
- Observation (O): `generate.py` accepted the pin anywhere in `README.md`. It now reads the command as one exact line in a code block marked `sh`, and no other line may run `git clone`.

Question (Q) for the maintainer: should the pin in `README.md` move in a pull request of its own, after the tag exists, so that the command never names a missing tag? `generate.py --check` would then read the tags and require the newest tag, which takes a second pull request for each release and makes the check depend on the tags being fetched. **Advice: no.** Keep the narrower claim above: the window is the minutes of one run, and a run that does not finish is already red each day.

Proposal (P) above, unchanged: `date` leaves `ratchet.json`. The review found it consistent and left it to the maintainer.
