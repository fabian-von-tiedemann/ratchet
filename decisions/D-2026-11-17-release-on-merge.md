# D-2026-11-17-release-on-merge: a new version is tagged and released when it reaches main

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

The mark `[...]` shows where this file leaves out part of a message. Nothing else in the original is changed.

## Question

The question was the first of three points in one message, with the question whether to do all three. The other two are about the agents' machine and are left out.

Original, in Swedish:

> 1. **Release vid merge.** Ett arbetsflöde skapar taggen och releasen när en ny version hamnar på main. Då försvinner dagens steg med Publish. Det kommer som en PR, eftersom det rör `.github/`.
>
> [...]
>
> Ska jag göra alla tre?

Translation into English:

> 1. **Release on merge.** A workflow creates the tag and the release when a new version reaches main. Then today's step with Publish goes away. It comes as a PR, because it touches `.github/`.
>
> [...]
>
> Shall I do all three?

## Answer

Original, in Swedish:

> ja, gör alla 3

Translation into English:

> yes, do all 3

## What follows

- `.github/workflows/release.yml` runs on every push to `main`. It runs the same three checks as the job `checks`, then [checks/release.py](../checks/release.py). The script reads the version in `ratchet.json`. When no tag and no release exist for that version, it creates the tag `vMAJOR.MINOR` on that commit and a release with the changelog entry for the version as its text.
- Approving a pull request that raises the version is approving the release. The maintainer still approves every release, through that pull request.
- An agent still does not tag or release by hand.
- `repo.tags-stay` holds: the workflow never moves, deletes or edits a tag. When the tag or a release for the version already exists, it writes nothing. What it does in each case is in [checks/README.md](../checks/README.md#releasepy).

Proposals (P): technical choices made within the owner's decision. The owner gave no answer on these, and each is a proposal until the PR is merged. By `ratchet.five-choices` the control room makes technical choices and shows them in the PR.

1. P: A draft release for the version also counts as an existing release. The run then writes nothing and fails, so that the version is published by hand and never gets two releases.
2. P, replaced by [D-2026-11-17-release-verbatim](D-2026-11-17-release-verbatim.md): the release text is the entry verbatim, then one fixed line that links to the files at the tag. No link is rewritten.
3. P: The release runs the same three checks as the job `checks` before it tags, so that a version is never tagged on a commit where they fail.
4. P: The logic is a script under `checks/`, with tests that need no network, and the workflow only calls it. The changelog is read strictly, so that the release text is the entry a reader sees.
5. P, replaced by [D-2026-11-17-release-verbatim](D-2026-11-17-release-verbatim.md): every run checks that each older version in the changelog has a tag and a published release, and fails, names one that has not and writes nothing, so that no version is skipped without a red run. The maintainer reruns that version's run.
6. P: The tag is created first, with a request that fails if it exists, then the release, and then the tag is read back. A tag at another commit than the run's is never written to.
