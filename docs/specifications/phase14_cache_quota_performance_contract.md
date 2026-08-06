# Phase 14 Cache, Quota and Performance Contract

Status: candidate; implementation authorization is separate.

Cache entries are content-addressed by a canonical key containing source hash,
range/crop, renderer/template/version and quality profile. A mismatching input
is a cache miss; it never returns stale output. Preview and production profiles
use disjoint keys. Cache eviction is planned through the lifecycle registry and
never touches protected artifacts.

Quota reporting is read-only first: project/cache byte totals, reclaimable
bytes and disk-pressure state. Hard-limit render admission and automatic
eviction require a separately accepted mutation package. Performance evidence
must measure a fixed REPLAY fixture before/after an optimization and reject an
optimization that changes the verified output hash. No provider, queue/retry,
FULL-render API or hardware-encode claim is authorized.
