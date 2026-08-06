# Phase 15 Validation/Observability Implementation Authorization

Decision: AUTHORIZED for one bounded local implementation.

Authorized deliverables:

1. `engine/validation/run_evidence.py` (or an equivalently narrow local module)
   implementing canonical observation serialization/loading, token/transition
   validation, safe evidence-reference envelopes, deterministic metric
   projection and the terminal decision reducer;
2. focused tests for all contract acceptance rows, including malformed bytes,
   identity/run/ordinal drift, unsafe fields, missing evidence, unsupported
   mode, terminal precedence, deterministic bytes and bounded Phase 4/14
   reference parsing;
3. no mutation of Phase 4 renderer semantics or Phase 14 lifecycle semantics.

The implementation may read typed Phase 4 receipts and Phase 14 evidence only
through their existing canonical validation boundaries. It must not open files
from caller paths, make a network call, execute retry/backoff, queue work,
start a thread/worker, decode media, add a Studio/FastAPI route, add UI code,
set Phase 16 thresholds or assert any Phase 17 product state.

Implementation acceptance remains separate.
