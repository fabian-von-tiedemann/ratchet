# D-2026-11-17-release-links: the release links to the changelog entry instead of copying it

- Date: 2026-11-17
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The question was put after the second review round of the approach in [D-2026-11-17-release-verbatim](D-2026-11-17-release-verbatim.md) was rejected, in [PR #9](https://github.com/fabian-von-tiedemann/ratchet/pull/9). Both rounds of that approach found that the published text could differ from the entry as a Markdown renderer shows it. Two options were put, with a recommendation for the first.

Original, in Swedish:

> 1. **Släppet länkar till avsnittet i stället för att kopiera det.** Släpptexten blir en fast rad skriven i koden, "Ratchet 0.4: see the changelog entry and the files at this tag", med en länk till `CHANGELOG.md` i taggen. Skriptet läser bara versionsnumret ur `ratchet.json` och rubriken för versionen. **Råd: ja.** Det minsta som fungerar: texten kan inte avvika eftersom den inte kopieras, och all tolkning av Markdown i släppskriptet försvinner. Kvar blir taggen, kontrollen av äldre versioner och återställningen för hand, som granskningen redan har godkänt.
> 2. **Ändringsloggen blir data.** `CHANGELOG.md` genereras ur en strikt datafil, på samma sätt som `REGISTER.md`, och släpptexten genereras ur samma data. Det ger snyggare släpp och stämmer med beslutet om strikta former, men det är betydligt mer att bygga. Jag avråder från det just nu och tar hellre upp det senare om fyllig släpptext saknas.

Translation into English:

> 1. **The release links to the entry instead of copying it.** The release text becomes one fixed line written in the code, "Ratchet 0.4: see the changelog entry and the files at this tag", with a link to `CHANGELOG.md` at the tag. The script reads only the version number from `ratchet.json` and the heading for the version. **Advice: yes.** The least that works: the text cannot differ because it is not copied, and all reading of Markdown in the release script goes away. What remains is the tag, the check of older versions and the recovery by hand, which the review has already approved.
> 2. **The changelog becomes data.** `CHANGELOG.md` is generated from a strict data file, in the same way as `REGISTER.md`, and the release text is generated from the same data. It gives nicer releases and agrees with the decision on strict forms, but it is considerably more to build. I advise against it for now and would rather take it up later if a fuller release text is missed.

## Answer

Original, in Swedish:

> pr9, din rek

Translation into English:

> PR #9, your recommendation

That is option 1.

## What follows

- The release text is one fixed line written in the code, "Ratchet MAJOR.MINOR: see the changelog entry and the files at this tag", with a link to `CHANGELOG.md` at the tag.
- The release script reads only the version number from `ratchet.json` and the heading for the version in `CHANGELOG.md`. Nothing from the changelog is copied into the release, and the script reads no Markdown.
- The tag, the check of older versions and the recovery by hand stay as the review approved them.
- This replaces [D-2026-11-17-release-verbatim](D-2026-11-17-release-verbatim.md) as far as the release text goes. That decision's rule on unfinished older versions stands.
- Option 2, the changelog as data, is not done now.

Proposals (P) made within the decision, shown in PR #9. The owner gave no answer on these.

1. P: The links in the line are written in Markdown, and the line also links to the files at the tag: `Ratchet 0.4: see [the changelog entry](https://github.com/OWNER/NAME/blob/v0.4/CHANGELOG.md) and [the files at this tag](https://github.com/OWNER/NAME/tree/v0.4)`. The link names the file, with no anchor, so it does not depend on how GitHub makes the anchor of a heading.
2. P: "The heading for the version" is a whole line `## MAJOR.MINOR (YYYY-MM-DD)` and nothing else, after CRLF is read as LF, in a file read as strict UTF-8. Every other line is passed over. What that misses is in [checks/README.md](../checks/README.md#releasepy).
3. P: The run still fails when the version in `ratchet.json` has no such line, when a tag up to that version has none, and when a line names a version newer than the one in `ratchet.json`.
4. P, after round 1 of the review of this approach: the older versions that must have a tag and a published release are every value that `version` in `ratchet.json` has had on the first-parent history of the commit being released, read with git, and no longer the version headings in the changelog, which a pull request can edit. The release workflow checks out the whole history (`fetch-depth: 0`). The rule on unfinished older versions is unchanged. Only where the versions are read from changes, and the message now names the commit whose run to rerun.
