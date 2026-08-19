# Automatic style selection

Read this reference only when `--style=auto` applies.

## Subject-sufficiency test

Choose `simple` only when the subject and staged diff together make the change's intent, rationale, and material impact clear without a body.

Choose `full` when a body preserves material review or maintenance context. Treat any of these as a full-style signal:

- a breaking change, required footer, or known issue relationship;
- a cause, rationale, tradeoff, or before/after behavior that is not evident from the diff;
- security, performance, migration, compatibility, rollout, or operational impact;
- a coherent change across multiple components whose relationship needs explanation;
- a repository template or analogous recent commits that use bodies for this class of change.

Prefer `simple` when none of those signals apply and a body would only paraphrase the subject or diff. In a genuine tie, use analogous repository history; without a useful precedent, use `simple`.

**Complete when:** the selected style has at least one stated reason and `full` contains context that would otherwise be lost.
