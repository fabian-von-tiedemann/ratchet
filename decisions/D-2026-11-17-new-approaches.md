# D-2026-11-17-new-approaches: new approaches for PR #10 and PR #12, and how a new rule is released

<!-- generated:status -->
Status: amended by D-2026-11-19-batched-releases (item 3, an unreleased first entry comes back)
<!-- /generated:status -->

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Three choices put to the maintainer together, each with a recommendation. PR #10 (issue #8) and PR #12 (issue #2) had each been rejected in two review rounds in a row with the same kinds of failure, so no third round was started (`ratchet.two-rounds`).

Original, in Swedish:

> 1. **#10 (#8), källbevakningen.** Ärendet från bevakningen ska bara innehålla data vi själva kontrollerar: källnamnet i en snäv form, två commit-SHA:er, antal ändringar och en länk till jämförelsen. Commit-rubriker och filnamn tas inte med. Grunden är att båda rundorna fann att text från källorna inte gick att göra ofarlig och att tokenen kunde smita igenom. **Råd: ja.**
> 2. **#12 (#2), kontrollen av att väntade tester körde.** Kontrollen flyttas ut ur testprocessen till ett eget steg i CI. Steget fallerar om körningen saknar en fullständig, unik post för varje test, även om testprocessen själv avslutade med 0. Regeln ska bara lova att fånga tester som tappats av misstag, inte testkod som medvetet slår ut kontrollen, eftersom sådan kod kör med samma rättigheter. Steget kräver en ändring i `checks.yml`, och dess exakta innehåll läggs i PR-beskrivningen som för #8. **Råd: ja.**
> 3. **Hur en ny regel släpps.** En PR som lägger till en regel höjer också versionen, i #12:s fall till 0.4, och släpps när den slås ihop via #9. Då behövs varken `## Unreleased`, `releases.json` eller texten "with unreleased changes", som var hela grunden till att släppt text kunde skrivas om. Varje ny regel blir då en egen version, och det är frekvent men enkelt och ärligt. Valet kräver att du först godkänner [PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9). **Råd: ja.**

Translation into English:

> 1. **#10 (#8), the source watch.** The issue from the watch holds only data we check ourselves: the source name in a narrow form, two commit SHAs, the number of changes and a link to the compare. Commit subjects and file names are left out. The reason is that both rounds found that text from the sources could not be made inert and that the token could slip through. **Advice: yes.**
> 2. **#12 (#2), the check that expected tests ran.** The check moves out of the test process into a step of its own in CI. The step fails if the run lacks a complete, unique record for each test, even if the test process itself exited with 0. The rule only promises to catch tests dropped by mistake, not test code that deliberately defeats the check, since such code runs with the same rights. The step needs a change to `checks.yml`, and its exact content goes in the PR description, as for #8. **Advice: yes.**
> 3. **How a new rule is released.** A PR that adds a rule also raises the version, in #12's case to 0.4, and is released when it is merged, through #9. Then neither `## Unreleased`, `releases.json` nor the text "with unreleased changes" is needed, and those were the whole reason released text could be rewritten. Each new rule then becomes a version of its own, which is frequent but simple and honest. The choice requires that you first approve [PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9). **Advice: yes.**

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- PR #10 is rebuilt so that an issue from the watch holds no text from a source. A reader follows the compare link to see the commits and files.
- PR #12 is rebuilt with the completeness check in a CI step of its own, outside the test process. The rule and the check claim only to catch tests dropped by mistake.
- A PR that adds a rule raises the version in `ratchet.json` and has a changelog entry for that version. It is released on merge by the workflow in PR #9. PR #12 raises the version to 0.4.

Proposals (P), which the maintainer did not decide: each rebuilt PR keeps its branch and number and starts again at review round 1. PR #9 is merged before PR #12, so that 0.4 is released on merge. Each workflow file is added to its PR's branch by the maintainer before approving, so that the check runs in CI on the head that is approved.
