# AI Development Execution Policy

## Role

The AI agent acts as a **credit-budgeted delivery architect**: it protects
acceptance quality while minimizing repeated context loading, duplicate audits,
and expensive end-to-end runs.

## Default delivery protocol

1. Freeze one bounded implementation package before coding: exact acceptance
   scenarios, owned files, and explicit non-goals.
2. Use one implementation owner per package. Parallel agents are reserved for
   independent workstreams with non-overlapping files.
3. Run at most two independent audits per package:
   - one authorization audit before implementation;
   - one final audit after targeted tests pass.
4. An audit finding is repaired as a grouped patch. Do not open a new audit for
   each sub-finding unless the repair changes the accepted scope or a blocker
   remains after the grouped repair.
5. Expensive integration/render tests run only at these gates:
   - implementation-ready checkpoint;
   - final acceptance checkpoint;
   - a targeted rerun after a fix that directly affects the render path.
6. Prefer focused unit/contract tests for negative paths. Mock subprocesses for
   timeout/non-zero cases; reserve real Remotion/FFmpeg execution for behavior
   that cannot be proven otherwise.
7. Each agent receives a compact current-phase brief and only the files needed
   for its task. Do not resend full historical audit trails by default.
8. Stop spec refinement when the authorized bounded acceptance scenarios are
   implementable and testable. New theoretical edge cases become a backlog item
   unless they break a stated acceptance criterion or create a security/data
   loss risk.

## Credit guardrails

- Default concurrency: 1 implementation agent plus at most 1 independent
  reviewer. Use 3+ agents only for genuinely independent file ownership.
- Before launching a new agent after an audit, state the exact finding it owns
  and why it cannot be included in the current repair package.
- If the same artifact is audited twice without code changes, do not audit it a
  third time; summarize the residual risk and seek a user decision only if it
  changes scope or acceptance.
- Maintain a concise `phase brief` in `NEXT_ACTIONS.md`: objective, acceptance
  gates, current commit, tests, and known blockers.

## Phase 4B application

Phase 4B will proceed as one frozen implementation package after its current
contract authorization is accepted. Its package-level gates are: deterministic
FULL REPLAY render; audio/video schedule fidelity; terminal cleanup and
overwrite protection; persistent artifact/output lineage; success/failure/
cancelled receipts; and one final independent audit. Additional speculative
contract refinement is deferred unless it invalidates one of these gates.
