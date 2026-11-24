# D-2026-11-24-faster-suite: run the suite once in each pass, and the suite on a released copy in a job of its own

- Date: 2026-11-24
- Decided by: Ratchet's maintainer
- Kind: decision (D)

## Question

Put to the maintainer in the control room on 2026-11-24, after a measurement of this repo's CI. The job `own` of `.github/workflows/checks.yml` ran `python3 -m unittest discover -s checks -v` and then `python3 checks/expected_tests.py`, which runs the same discover with strictly more checks, and each took 6.6 to 9.6 minutes. Inside each pass, `test_released_text.ReleaseSteps` ran `expected_tests.py` on a released copy of the repo, so the full suite ran again: 260 of 527 seconds locally, about 49%. The job `base` runs one more pass. The options were: 1, remove the plain `unittest discover` step from `own`; 2, move the run of the full suite on a released copy out of the suite, into a step or a job of its own that runs once on each pull request and push to `main` and that the job `checks` needs; 3, a further change beyond those two. The question, verbatim, in Swedish:

> A. Gör 1 och 2 (rekommenderas) / B. Bara 1 / C. 1, 2 och 3 direkt

Translation:

> A. Do 1 and 2 (recommended) / B. Only 1 / C. 1, 2 and 3 at once

## Answer

> Ja på rek

Translation:

> Yes to the recommendation

That is option A.

## What follows

- The job `own` runs the suite once, with `checks/expected_tests.py`, which is its suite step. The step that ran `unittest discover` before it is removed: every test it ran, `expected_tests.py` runs too, and checks that each one ran and passed.
- The run of `expected_tests.py` on a released copy of the repo moves out of `ReleaseSteps` into `released_copy_case` in `checks/test_released_text.py`, a test that discover does not collect. It takes the same release steps, with every assertion they made, and then runs the full suite in the copy. The job `released` runs it once on each pull request and each push to `main`, and the job `checks`, the one the ruleset on `main` requires, needs `released` and is red unless it passed. The release workflow runs it before it tags, as it ran inside its suite before.
- The job `base` runs the base branch's `test_released_text.py --released-copy` in the tree of the code, after the base's `expected_tests.py`, as `checks/from_base.py` lists. Before, the base's suite in that tree held `ReleaseSteps` and so ran the suite on a released copy of the tree of the code: the base's tests with the pull request's code of the checks. Without this command, that pass would be lost, and a fault in the pull request's code of the checks that shows only on a released copy would pass the base (round 1 of the review of #147). `checks/from_base.py` comes from the base, so the command takes effect from the pull request after the one that adds it. Until then the base is `main` before it, whose suite still holds the nested run inside `ReleaseSteps`, so no pull request is judged without it.
- This loosens nothing. Every assertion of the old test still runs in the tree of the pull request, in the job `released`, on every pull request and every push to `main`, and on a pull request also in the tree of the code, in the job `base`, and both jobs are required for the merge through the job `checks`. A test fails when `checks` does not need `released`, when `released` no longer runs the suite on the copy, or when the run on a released copy leaves the commands of the tree of the code. The ruleset on `main` still requires only the job `checks`, so no setting of the host changes.
- What is saved is the duplicate `unittest discover` step and the nested run inside every pass of the suite. The job `base` now runs two passes of the suite in the tree of the code, one after the other, and the jobs `own`, `base` and `released` run in parallel, so the time a pull request waits is about that of the longest job.
- Like every change to the workflow, the pull request that makes this change cannot be judged by the base branch's checks: its job `checks` is red by design, and the maintainer reads it and merges it as an administrator.
