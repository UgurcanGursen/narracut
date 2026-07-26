# Phase 1 Post-Audit Test Hardening Report

Date: 2026-07-26
Base SHA: `7b4ad0fcc68f0a183e44857459f8a2d8a9e7612f`
Base commit: `feat: add generated client and Studio UI shell`
Independent generated-client/UI audit result: `PASS_WITH_FINDINGS`
Forensic classification: `SALVAGE_READY_WITH_FIXES`

## Scope

The dirty post-audit candidate was preserved and completed. The final intended
scope is limited to:

- `studio-ui/README.md`
- `studio-ui/src/api/studioApi.live.test.ts`
- `studio-ui/src/test/liveTestBaseUrl.ts`
- `studio-ui/src/test/liveTestBaseUrl.test.ts`
- `tests/test_v2_to_v3_migrator.py`
- `baseline/phase1_post_audit_test_hardening_report.md`

The production Studio API facade, generated client, OpenAPI/schema artifacts,
backend, runtime migrator implementation, package manifests, lockfile, domain
packs, samples, docs, `main.py`, `v2/`, and `norm_words_debug.json` were not
changed.

## Preflight and Backup

- Branch: `main`
- HEAD: `7b4ad0fcc68f0a183e44857459f8a2d8a9e7612f`
- `origin/main`: `7b4ad0fcc68f0a183e44857459f8a2d8a9e7612f`
- Live remote `refs/heads/main`: `7b4ad0fcc68f0a183e44857459f8a2d8a9e7612f`
- Baseline tag peeled target: `f0d7a3100b0855a84432f09ca22001d0913aa1aa`
- Staged diff before mutation: empty
- Expected dirty state: exact three tracked files plus two hardening untracked
  files and pre-existing `norm_words_debug.json`
- Pre-existing cache warnings: `.pytest_cache/` and
  `shared-schemas/.pytest_cache/` permission denied; unchanged and out of scope

Salvage backup:
`C:\tmp\kurgu_phase1_salvage_backup_20260726_194545`

The backup contains `git diff --binary`, `git diff --stat`, `git diff --numstat`,
`git status --porcelain=v2 --untracked-files=all`, and byte/hash/newline/BOM
inventory for the five pre-existing hardening files. `norm_words_debug.json`
was not read or copied.

Validation checkout:
`C:\tmp\kurgu_phase1_validation_20260726_194745\checkout`

## Findings and Fix

Original P2 finding 1: live tests could create projects against an unsafe remote
endpoint if `KURGU_STUDIO_API_BASE_URL` was supplied by mistake.

Original P2 finding 2: generated client/UI checks needed explicit evidence that
production HTTP behavior, OpenAPI, generated output, and package lock were not
changed by the live-test guard.

Dirty-tree forensic result: the existing candidate correctly kept validation in
the live-test layer, left production `createStudioApi` unchanged, and made the
migrator EOL portability fix only in tests.

Remaining bug fixed here: WHATWG URL canonicalization returns an empty
`URL.port` for explicit default HTTP port `:80`. The live-test guard now still
uses WHATWG `URL` as the parser, but determines explicit port presence from the
raw authority before canonical default-port elision. Credentials are still
rejected separately and cannot bypass validation.

Accepted live base URLs:

- `http://127.0.0.1:80`
- `http://localhost:80`
- `http://[::1]:80`
- `http://127.0.0.1:8000`
- `http://localhost:8000`
- `http://[::1]:8000`

Rejected classes include non-HTTP URLs, non-loopback hosts, missing port,
credentials, path, query, fragment, malformed port, out-of-range port, file
URLs, Windows paths, whitespace-padded values, and invalid URLs.

Rejected raw URLs are not echoed in public errors.

## Frontend Validation

All commands ran under the C:\tmp validation checkout, not the source repo.

- `npm ci --ignore-scripts`: PASS, 167 packages, install audit summary
  `found 0 vulnerabilities`
- `npm run verify:toolchain`: PASS, Node `v24.11.1`
- `npm run check:client`: PASS
- Generated aggregate SHA:
  `0ba1a9bb20d1bef1a01d366cfb5a5cb139aa9cc549db357630008a6809f80b1a`
- OpenAPI SHA:
  `c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128`
- `npm run verify:http-boundary`: PASS, 30 files, 5 production files
- `npm run typecheck`: PASS
- `npm test`: PASS, 4 files, 53 tests
- `npm run build`: PASS, 32 modules
- `npm install --package-lock-only --ignore-scripts`: PASS, lockfile stable
- Package-lock SHA:
  `5404b6f9cf7d32692be5c197468eecdfb3b5ce70303f203da2b25b4508c46d95`

Exact standalone `npm audit --audit-level=low`: PASS.

- Audit workdir:
  `C:\tmp\kurgu_phase1_validation_20260726_194745\checkout\studio-ui`
- Audit exit code: `0`
- Audit result: `found 0 vulnerabilities`
- Temp `package.json` SHA before/after:
  `4cde6d9102463ada49c4e5e39e5a1f5de249a89997097e0cc9198704d62d9d00`
- Temp `package-lock.json` SHA before/after:
  `5404b6f9cf7d32692be5c197468eecdfb3b5ce70303f203da2b25b4508c46d95`
- Audit did not mutate the source repository. No `npm audit fix`, dependency
  install, upgrade, or lockfile change was run.

## Network Safety and Live HTTP

Remote negative:

- Environment: `KURGU_STUDIO_API_BASE_URL=https://example.com`
- Command: `npm run test:live`
- Native result: `EXIT_CODE=1`
- Failure location: `requireLiveTestBaseUrl`
- Failure speed: before project create
- Public error: generic validator message only; raw URL not echoed

Local live HTTP:

- Locked venv: `C:\tmp\kurgu_phase1_validation_20260726_194745_venv`
- Port: `127.0.0.1:65314`
- Uvicorn target: `kurgu_studio_api.app:create_app --factory`
- TCP readiness: PASS
- `npm run test:live`: PASS, 1 test
- Owned Uvicorn PID: `7504`
- Cleanup: PASS, PID not alive after cleanup

## Migrator EOL Portability

The runtime migrator implementation was not changed. The archive checkout was
created from `HEAD`, then only the final hardening candidate files were copied
into it.

Contract/migrator suite:

- `pytest tests/test_jsonschema_dependency.py tests/test_v3_contracts.py tests/test_v2_to_v3_migrator.py`: PASS, `213 passed, 1 skipped`

Demo output:

- CLI status: `SUCCESS_WITH_LOSS`
- `inspection_summary.txt`: expected CRLF 9, actual CRLF 0, canonical LF hash
  `ace77c57f8f1e9579805ce780e58e78aef783b069b0c0a2c2a69b73a67dc7636`
- `migration_report.md`: expected CRLF 335, actual CRLF 0, canonical LF hash
  `5df7477ddadb9cc8db29474bb3f5682cf13d78eeaced0e326102068bae8e9143`
- `migration_result.json`: expected CRLF 1188, actual CRLF 0, canonical LF hash
  `0e637270c6c350a2c97f64976eb5f78d2eb05aca70f65cb3532d8fc84b34a2ef`
- `workspace.json`: expected CRLF 506, actual CRLF 0, canonical LF hash
  `14085c0dcbd3c2f130be979c062b3f9c133a767d60f3e57f06ec9a14b07546de`

Textual byte parity is canonical expected LF bytes versus actual LF bytes.
Binary/hash parity behavior is unchanged.

## Python Regression

All accepted Python commands used `PYTHONDONTWRITEBYTECODE=1`; pytest used
cacheprovider disabled where applicable.

- Focused Project API: PASS, `55 passed, 3 deselected, 1 warning`
- Foundation: PASS, `18 passed`
- Studio toolchain script: PASS
- Studio toolchain tests: PASS, `3 passed, 1 warning`
- Schema sync: PASS, 16 schemas
- OpenAPI exporter: PASS, SHA
  `c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128`
- Contract/migrator: PASS, `213 passed, 1 skipped`

Full Python discovery was attempted in a separate full venv populated from root
`requirements.txt` and `studio-api/requirements.lock`; `pip check` passed. Full
collection stopped with pre-existing manifest gap:

- `tests/test_adversarial_alignment.py` imports `v2.audio_engine`
- `tests/test_audio.py` imports `v2.audio_engine`
- `tests/test_v2_core.py` imports `v2.main`, which imports `v2.audio_engine`
- `v2/audio_engine.py` imports undeclared `pyloudnorm`
- Error: `ModuleNotFoundError: No module named 'pyloudnorm'`

No dependency manifest was changed and no ad hoc dependency was added.
Changed files do not import `pyloudnorm` or affect this legacy import chain.
Full render was not run.

## Static and Protected Paths

- `studio-ui/package-lock.json`: unchanged,
  `5404b6f9cf7d32692be5c197468eecdfb3b5ce70303f203da2b25b4508c46d95`
- `shared-schemas/openapi/openapi.json`: unchanged,
  `c64d9713dbaa7e7afbd1ad5eb07faf1da404e5871466a8012ddb5e3a00f05128`
- Generated aggregate: unchanged,
  `0ba1a9bb20d1bef1a01d366cfb5a5cb139aa9cc549db357630008a6809f80b1a`
- Production `studioApi.ts`: diff 0,
  SHA `2c5957e60dc363998e2ca2517b37e4e606329dc503e816770874a5e9e91e2f96`
- Runtime migrator files: diff 0
- Backend, schema, shared-schemas, domain-packs, samples, docs, `main.py`,
  `v2/`, and requirements: diff 0
- `schema/v3` `$ref` count: 159
- OpenAPI `$ref` count: 23
- Changed files contain no `eval(`, `exec(`, `shell: true`, `child_process`, or
  `pyloudnorm`
- Original repo has no `node_modules`, venv, `dist`, or coverage artifact from
  this task
- `git diff --check`: no whitespace error; only the pre-existing Git line
  ending warning for `tests/test_v2_to_v3_migrator.py`

## Repository Mutation Result

Source repository changed files are the intended six-file scope after adding
this report. The pre-existing `norm_words_debug.json` remains untracked and was
not read, copied, staged, or modified. Cache permission warnings remain
pre-existing and out of scope.

Proposed commit message:

`fix: harden phase 1 test boundaries`

Post-push SHA: pending at commit creation.

Independent mini re-audit gate: pending after commit/push.
