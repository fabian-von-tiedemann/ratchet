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

- `.github/workflows/release.yml` runs on every push to `main`. It reads the version in `ratchet.json`. When no tag and no release exist for that version, it runs the checks, then creates the tag `vMAJOR.MINOR` on that commit and a release with the changelog entry for the version as its text.
- Approving a pull request that raises the version is approving the release. The maintainer still approves every release, through that pull request.
- An agent still does not tag or release by hand.
- `repo.tags-stay` holds: the workflow never moves, deletes or edits a tag. When the tag or a release for the version already exists, it does nothing.

Technical choices made within the owner's decision. The owner gave no answer on these. By `ratchet.five-choices` the control room makes technical choices and shows them in the PR.

1. A draft release for the version also counts as an existing release. The workflow then leaves the version to be published by hand, so that one version never gets two releases.
2. The links in the release text point at the files in the tag, so that they work outside the repo.
3. The release runs the same three checks as the job `checks` before it tags, so that a version is never tagged on a commit where they fail.
