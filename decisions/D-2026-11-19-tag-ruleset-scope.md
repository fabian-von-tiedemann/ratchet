# D-2026-11-19-tag-ruleset-scope: the tag ruleset blocks deleting and moving a tag, not creating one

- Date: 2026-11-19
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

The question came before the work on 0.7. It was put in English:

> **The ruleset blocks deleting and moving tags, but not creating them.** A published tag can then never disappear or point somewhere else, which is the part that can't be undone. The release flow can still create tags exactly as today, and no new secret is needed. If the agent account creates a tag on its own, the tripwire catches the usual ways of writing that command. A tag created by mistake doesn't publish anything, and you can delete it. **Recommendation: yes.**
>
> The alternative is a deploy key or a GitHub App that the release flow pushes tags with. That also locks creation, but it brings a new secret that has to be stored in the repo and rotated, and `release.py` would have to be rebuilt.

It was put again later, in these words:

> **The tag ruleset** blocks deleting and moving tags, but not creating them. GitHub doesn't let the release workflow's token past a block on creation. **Recommendation: yes.**

## Answer

Original, in Swedish:

> ja

Translation into English:

> yes

## What follows

- This amends item 2 of [D-2026-11-19-locks-not-parsing](D-2026-11-19-locks-not-parsing.md), which said that "only you and the release flow can create or delete a tag". The ruleset for tags blocks deleting a tag and moving one, for every actor but the repository admin role. It does not block creating a tag.
- The ruleset is [templates/tag-ruleset.json](../templates/tag-ruleset.json): target `tag`, every tag, enforcement `active`, the rules `deletion`, `update` and `non_fast_forward`, and the repository admin role as the only bypass actor. The maintainer applies it, because settings are the maintainer's, and reads it back. The steps are in [checks/README.md](../checks/README.md#the-tag-ruleset).
- The release workflow is unaffected: `checks/release.py` creates a tag with one `POST` to `git/refs` and never moves, deletes or edits one.
- Creating a tag or a release is caught by the tripwire alone, `checks/tripwire.py`, which catches the usual spellings and is not a lock.

Observation (O): GitHub's documentation on rulesets does not say whether the built-in GitHub Actions integration can be a bypass actor. Public reports from projects that tried say that GitHub refuses it as a bypass actor on a repository ruleset, or accepts the `github-actions[bot]` user and ignores it at push time, so a ruleset that blocks creating a tag also blocks a release workflow that tags with the built-in token. That is why creation is left open. It was not tried in this repo.
