# Phase 1 Project API Eligibility Hardening Report

Date: 2026-07-26
Status: PASS / PENDING POST-COMMIT INDEPENDENT RE-AUDIT
Scope: public Project API domain/version/profile eligibility

## Revision Evidence

- Starting SHA:
  `22ae36d314fc57a8603cd888576110e3fd1476b9`
- Intended commit message:
  `fix: enforce project domain eligibility`
- Post-push SHA: pending
- Baseline tag peeled target:
  `f0d7a3100b0855a84432f09ca22001d0913aa1aa`

## Audit Blockers

The independent audit of the initial Project API slice found two fail-open
paths:

1. `business-tech@0.1.0` accepted the schema-valid but semantically unrelated
   `dpf_core_default` profile ID.
2. Registry discovery made the non-production
   `true-crime-legal@0.0.1-contract` example available to public project
   creation.

Both paths created a `ready` project and therefore blocked generated
TypeScript client and React HTTP-only shell work.

## Root Cause

The domain adapter synthesized profile `domain_id` and
`domain_pack_version` from the outer request before calling
`DomainPolicyResolver`. The resolver could verify only those synthesized
values; it had no application-owned binding between a requested profile ID and
the selected production pack.

The runtime also treated every successfully discovered registry pack as
eligible for public creation. Discovery is an internal contract mechanism and
does not establish production eligibility.

## Eligibility Architecture

`DomainEligibilityPolicy` is a dedicated immutable infrastructure boundary.
Its declaration is fixed by application wiring and is not derived from:

- registry discovery;
- client input;
- environment variables;
- arbitrary configuration paths; or
- `contract_status` string interpretation.

The policy validates its own declarations at construction, rejects duplicate
or malformed entries, and stores the resulting bindings in an immutable
mapping.

Domain-pack creation now follows this fail-closed sequence:

```text
strict HTTP request validation
-> canonical profile contract validation
-> production domain/version eligibility
-> profile binding
-> registry lookup
-> public DomainPolicyResolver
-> canonical policy snapshot validation
-> project validation
-> repository insert
```

Canonical profile validation remains before eligibility so a malformed
profile ID continues to return the established
`CONTRACT_VALIDATION_FAILED / SCHEMA_PATTERN` result. Eligibility is checked
before registry lookup and policy resolution.

## Exact Eligible Matrix

```text
business-tech@0.1.0
  allowed_profile_ids:
    - dpf_business_default
```

No other domain-pack is currently eligible for public Project API creation.
`core_only` remains separate from this matrix and continues to use
`core-generic@0.0.0 / dpf_core_default`.

## Dynamic Behavior

### Eligible business-tech

- Result: `201 Created`
- Profile: `dpf_business_default`
- Snapshot ID: `dps_d18e9981c3f4bcca8e3f`
- Persistence scope: `process_lifetime`

### Real profile mismatch

- Request: `business-tech@0.1.0 / dpf_core_default`
- Result: `422 DOMAIN_PROFILE_MISMATCH`
- Issue pointer: `/domain/profile/profile_id`
- Registry lookup: not reached
- Repository residue: 0
- Raw requested profile ID: not echoed
- Eligible profile list: not exposed

### Discovered but ineligible pack

- Request:
  `true-crime-legal@0.0.1-contract / dpf_true_crime_default`
- Result: `422 DOMAIN_UNKNOWN`
- Registry lookup: not reached
- Repository residue: 0
- Public response is identical to a genuinely unknown domain response.
- Contract-example status, manifest path, registry root, and discovery state:
  not exposed

### Core-only

- Result: `201 Created`
- Domain: `core-generic@0.0.0`
- Profile: `dpf_core_default`
- Domain-pack eligibility allowlist: not consulted

## Error and No-Leak Boundary

`DOMAIN_PROFILE_MISMATCH` is now reachable through a real public request and
uses the existing centralized error envelope with HTTP 422. Non-eligible
domain/version combinations deliberately use the same sanitized
`DOMAIN_UNKNOWN` response as absent packs.

Dynamic tests verify that responses contain no raw profile ID, eligible
profile list, contract-example status, manifest or registry path, traceback,
or exception representation. An environment variable named as an eligibility
override does not expand the immutable policy.

## Tests and Quality Gates

- Focused Project API:
  `55 passed, 1 existing warning`
- Shared schema/OpenAPI foundation:
  `18 passed`
- Studio toolchain:
  `3 passed, 1 existing warning`
- Contract/migrator regression:
  `213 passed, 1 skipped`
- Full discovery:
  `345 passed, 1 skipped, 1 existing warning`
- Existing warning:
  Starlette deprecates the current HTTPX TestClient path.
- Schema sync:
  PASS, 16 schemas
- OpenAPI check:
  PASS
- Full video render:
  not run, as required

The focused suite retains the original 42 tests and adds 13 eligibility,
profile-binding, immutability, malformed/duplicate declaration, residue, and
no-leak cases.

## OpenAPI and Protected Paths

The request/response DTOs and routes did not change. The committed OpenAPI
artifact remains byte-identical:

- Bytes: 18,490
- SHA-256:
  `c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128`

Canonical schemas, distributed schemas, schema manifest, engine contracts,
domain packs, samples, locks, Studio UI, V2, migration code, and roadmap docs
were not changed.

## Remaining Limitations

- Persistence remains instance-local and process-lifetime only.
- No WorkspaceStore, SQLite, authentication, artifact creation, render/job
  orchestration, generated TypeScript client, or React UI exists.
- `business-tech` remains a Phase 1 declarative skeleton; this hardening
  establishes API eligibility, not full production domain intelligence.
- The existing TestClient deprecation warning remains non-blocking.

## Re-Audit Gate

Implementation result: PASS.

Generated TypeScript client and React HTTP-only shell work remain gated on a
post-commit independent re-audit of the eligibility hardening commit. The
post-push SHA must be recorded from the real remote state; it is not predicted
in this report.
