## Purpose

Describe the single coherent change entering the sanctuary.

## Scope

- [ ] The pull request has one primary purpose.
- [ ] Unrelated work is excluded.

## Receipt Package

For every item, either provide the artifact or mark it `N/A` with a specific rationale. Do not invent irrelevant evidence merely to satisfy the form.

- [ ] Source code — provided, or `N/A` because:
- [ ] Automated tests — provided, or `N/A` because:
- [ ] Verification command — provided, or `N/A` because:
- [ ] Documentation — provided, or `N/A` because:
- [ ] Demonstration — provided, or `N/A` because:
- [ ] Failure case — provided, or `N/A` because:
- [ ] Known limitations — provided, or `N/A` because:

## Verification

Command:

```text
python verify.py
```

Result:

```text
PENDING
```

Final verified head SHA: `PENDING`

## Review Findings

List each actionable finding and its disposition. Unresolved findings block merge.

## Approval

- [ ] Required approval recorded
- [ ] Final head SHA has not changed since verification
- [ ] All review threads resolved or formally rejected with evidence

## Post-Merge

- [ ] Resulting `main` commit checked
- [ ] Post-merge workflow result recorded
- [ ] Merge docket added under `docs/dockets/`

A docket-only follow-up that changes only `docs/dockets/` is exempt from creating another docket. Any additional file change cancels that exemption.

## Rollback

State the exact revert or recovery procedure.

> No green run, no banana. Bureaucracy must terminate. 📜🍌
