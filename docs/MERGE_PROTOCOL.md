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

A docket may be prepared before merge with merge-specific fields marked `PENDING`. After merge, those fields may be completed by one of two finite closure mechanisms:

- a docket-only administrative pull request that is exempt from creating a second docket, provided it changes only `docs/dockets/` and does not alter executable behavior; or
- an approved repository automation that writes the final merge SHA and post-merge result without opening another governed pull request.

The exemption applies only to the recursive docket requirement. Scope, review, verification, approval, and rollback recording still apply to the administrative change.

## Gate Sequence

A change may enter `main` only after the following gates are satisfied in order:

- **Scope Gate:** The pull request has one coherent purpose.
- **Receipt Gate:** Applicable evidence is present. Each of source, tests, documentation, demonstration, failure case, and known limitations must be either supplied or marked `N/A` with a specific rationale. A vague or convenience-based `N/A` does not satisfy the gate.
- **Review Gate:** Actionable findings are either fixed or explicitly rejected with evidence.
- **Verification Gate:** Required CI jobs pass for the final head commit.
- **Approval Gate:** The required approval is recorded.
- **Merge Gate:** The merge uses the verified final head SHA.
- **Main Gate:** The resulting `main` commit is checked after merge.
- **Archive Gate:** A docket is stored under `docs/dockets/`, using one of the finite closure mechanisms above for post-merge fields.

## Evidence Applicability

The receipt package must match the change type instead of manufacturing irrelevant artifacts.

- Executable changes normally require source, automated tests, a verification command, a demonstration, a failure case, documentation, and known limitations.
- Documentation-only and administrative changes may mark source-code changes, new automated tests, runtime demonstrations, or runtime failure cases as `N/A`, but each omission must state why existing verification is sufficient and why adding an artifact would expand scope without improving evidence.
- Workflow, packaging, and configuration changes require verification appropriate to the affected system even when application source code is unchanged.

## Failure Rules

- A failed verification blocks merge.
- A new commit invalidates earlier approval and verification receipts until rechecked.
- Unresolved review threads block merge unless the docket records a justified rejection.
- Missing post-merge status must be recorded as unknown, never rewritten as success.
- A broken `main` requires repair before new feature work.
- A docket-only administrative pull request loses its recursion exemption if it changes anything outside `docs/dockets/`.

## Rollback

The default rollback method is a normal Git revert of the merge commit. History rewriting is prohibited unless repository corruption makes a revert impossible.

## Brother Ape Clause

No green run, no banana. No docket, no institutional memory. Atmosphere does not satisfy a gate. Bureaucracy must terminate. 📜🍌
