# The Aviary Merge Protocol

Status: Active
Authority: Brother Ape Governance Rule
Scope: All changes entering `main`

## Purpose

A merge is not complete merely because GitHub accepts it. A merge is complete when the change has evidence, review, verification, a durable record, and a known rollback boundary.

## Required Docket

Every pull request entering `main` must have a merge docket containing:

1. Pull request number and title.
2. Base and head branches.
3. Final head commit SHA.
4. Approval state.
5. Resolved review findings.
6. Verification workflow and result.
7. Test count or verification command.
8. Known limitations.
9. Merge commit SHA.
10. Post-merge verification result.
11. Rollback instruction.

## Gate Sequence

A change may enter `main` only after the following gates are satisfied in order:

- **Scope Gate:** The pull request has one coherent purpose.
- **Receipt Gate:** Source, tests, documentation, demonstration, failure case, and known limitations are present.
- **Review Gate:** Actionable findings are either fixed or explicitly rejected with evidence.
- **Verification Gate:** Required CI jobs pass for the final head commit.
- **Approval Gate:** The required approval is recorded.
- **Merge Gate:** The merge uses the verified final head SHA.
- **Main Gate:** The resulting `main` commit is checked after merge.
- **Archive Gate:** A docket is stored under `docs/dockets/`.

## Failure Rules

- A failed verification blocks merge.
- A new commit invalidates earlier approval and verification receipts until rechecked.
- Unresolved review threads block merge unless the docket records a justified rejection.
- Missing post-merge status must be recorded as unknown, never rewritten as success.
- A broken `main` requires repair before new feature work.

## Rollback

The default rollback method is a normal Git revert of the merge commit. History rewriting is prohibited unless repository corruption makes a revert impossible.

## Brother Ape Clause

No green run, no banana. No docket, no institutional memory. Atmosphere does not satisfy a gate.
