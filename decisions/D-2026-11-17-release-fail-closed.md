# D-2026-11-17-release-fail-closed: the release script claims to fail closed, and names the version only when the API answers

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The question was put after the second review round of the claim in [D-2026-11-17-release-narrow-claim](D-2026-11-17-release-narrow-claim.md) was rejected, in [PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9). `checks/README.md` promised that a red run would name an unfinished version within one scheduled interval at most. The reviewer tagged 0.4, cancelled the run before the release, and then gave a scheduled run HTTP 503 on the list of tags. The run was red and wrote nothing, but its message named only the request and did not name 0.4. Both rounds of that claim found the same kind of failure: a run that ended without naming the unfinished version. No code can promise to name a version while the API it reads from does not answer.

Original, in Swedish:

> Ska release-kontrollen lova att varje körning som inte kan bekräfta att alla versioner är släppta blir röd och inte skriver något? Att den också säger vilken version det gäller blir då något den gör när GitHubs API svarar, men det lovas inte. **Råd: ja.** Koden ändras inte, bara texten i `checks/README.md` och en beslutsfil. Sedan granskar Codex en sista runda.

Translation into English:

> Should the release check promise that every run that cannot confirm that all versions are released turns red and writes nothing? That it also says which version is concerned then becomes something it does when GitHub's API answers, but it is not promised. **Advice: yes.** The code does not change, only the text in `checks/README.md` and a decision file. Then Codex reviews a last round.

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- The release script promises that every run that cannot confirm that all versions are released turns red and writes nothing.
- That the run also says which version is concerned is something it does when GitHub's API answers. It is not promised.
- The code does not change. Only the text in [checks/README.md](../checks/README.md#releasepy) and this file change.
- Then Codex reviews a last round.

Proposals (P) made within the decision, shown in PR #9. The owner gave no answer on these.

1. P: "Writes nothing" is stated as the code does it. A scheduled run writes nothing at all. A run of a push or by hand writes nothing when it cannot confirm that every older version is tagged and released, or when any check before its writes fails. Its only writes are the tag and the release of the version in `ratchet.json`, after every check has passed. If it cannot confirm either, it is red. A run that tags and then fails to publish has written the tag, so "writes nothing" cannot be said of that run.
2. P: The README names the cases where a run is red and does not name the version: the API does not answer, answers with an HTTP error such as 503, or answers with something that is not JSON or is of the wrong form, before the run has read the tags and the releases. An error the script does not expect before any write is not caught. Python exits with 1, so the run is red.
3. P: While a version is unfinished, the daily scheduled run is red each day GitHub starts it. The limits of GitHub's schedule stay as they were in "What it does not claim".
4. P: A test in `checks/test_release.py` pins the claim. A scheduled run gets HTTP 503, 500 or 502, no answer, an answer that is not JSON or of the wrong form, or an unexpected error, at each read it makes. That covers three states: 0.4 cancelled after its tag, never tagged, and released at an earlier commit. The run is red, sends only `GET` requests and writes nothing. The test passes against the code as it is, because the code already fails closed.
