# D-2026-11-17-release-verbatim: the release text is the entry verbatim, and an unfinished older version stops the run

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The question was put after the second review round of [PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9) was rejected.

Original, in Swedish:

> 1. **[PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9), släpp vid sammanslagning, med nytt angreppssätt.** Två saker ändras:
>    - Släpptexten blir versionens avsnitt i `CHANGELOG.md` ordagrant, med en fast rad sist som länkar till taggen. Inga länkar skrivs om.
>    - Saknar en äldre version tagg eller publicerat släpp blir körningen röd, inget skrivs, och du startar om den körningen för hand.
>
>    **Råd: ja.** Båda granskningsrundorna föll på att arbetsflödet försökte laga sig självt och skriva om texten. #12 och version 0.4 väntar på #9.

Translation into English:

> 1. **[PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9), release on merge, with a new approach.** Two things change:
>    - The release text becomes the version's section in `CHANGELOG.md` verbatim, with a fixed line last that links to the tag. No links are rewritten.
>    - If an older version lacks a tag or a published release, the run turns red, nothing is written, and you restart that run by hand.
>
>    **Advice: yes.** Both review rounds failed because the workflow tried to repair itself and rewrite the text. #12 and version 0.4 wait for #9.

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- The release text is the version's entry in `CHANGELOG.md`, verbatim, followed by one fixed line that links to the tag. No link in the entry is rewritten.
- If a version older than the one being released has no tag or no published release, the release run fails and writes nothing. The maintainer restarts that version's run by hand.
- This replaces technical choices 2 and 5 of [D-2026-11-17-release-on-merge](D-2026-11-17-release-on-merge.md): links are no longer pointed at the tag, and an older version needs a published release as well as a tag.

Proposals (P) made within the decision, shown in PR #9. The owner gave no answer on these.

1. P: A rerun for the version being released that finds its tag at the run's own commit and no release creates the release. It is that version's own run, not an older one, and the tag is already where it belongs. Why that is safe is in [checks/README.md](../checks/README.md#releasepy).
2. P: Tags and releases of versions newer than the one in `ratchet.json` at the checked-out commit are ignored, so that a rerun for an older version does not trip over a newer tag.
3. P: 0.1 needs only its tag. It was tagged before Ratchet published releases, and it has no release.
4. P: The workflow can also be started by hand, with `workflow_dispatch` and no input, for when a run cannot be rerun. It releases only what `ratchet.json` names at the head of `main`, under the same checks, and fails on any other branch.
5. P: "Verbatim" keeps the markers of generated blocks in the text. They are HTML comments, which GitHub does not show.
