# Financial Manager AI V2 — Reproducibility and Regression Validation

Status: **PASS** (2026-11-22).

## Clean environments

- Python: CPython 3.14.8, pip 26.2.1, a new venv under `/tmp`, followed by
  `pip install -r requirements.txt`, application imports, provisioning,
  Application/API tests and full repository regression.
- Web: Node 26.13.0, npm 11.20.0, a new source tree under `/tmp`, `npm ci` from
  the lockfile (507 packages, zero audit vulnerabilities), type generation,
  typecheck, lint, 33 unit/component tests and production build.
- Framework pins: Next.js 16.4.6, React/React DOM 19.3.1, TypeScript 5.9.3,
  Tailwind CSS 4.3.5 and Playwright 1.65.1.

Package installation is distinct from offline runtime and may contact configured
registries. `npm ci --offline` also succeeded from the available cache; the clean
Python install used the configured package index because no usable pip cache was
available.

## Final gates

| Gate | Result |
|---|---|
| Python compileall | PASS |
| Provisioning/import/discovery | PASS; 773 tests discovered, zero import errors |
| Complete Python unittest regression | 773 passed, 0 failed, 0 errors, 0 skipped |
| Web type generation/typecheck | PASS |
| ESLint | PASS |
| Vitest | 33 passed in 10 files |
| Next.js production build | PASS; 9 routes generated |
| Chromium real-API E2E | 11/11 passed |
| Offline-simulated real-API E2E | 11/11 passed |
| OpenAPI generation/closed schema checks | PASS |

## Startup and real HTTP

The documented two-terminal commands start Uvicorn on `127.0.0.1:8000` with an
explicit loopback CORS origin and Next.js on `127.0.0.1:3000`. Playwright starts
those actual servers, uses the actual `/api/v1` adapter and covers onboarding,
four-domain analysis, anomaly and chat; it does not release-validate against mocks.

## Integrity and stale state

Regression coverage mutates source/profile/mapping/registry artifacts and verifies
that readiness/execution fail closed, then recover only from current approved
artifacts. Exact Decimal, currency, source rows, mapping/catalog/policy versions
and limitations retain their meaning from source through API and browser.

## Performance characterization

The bounded local flows remained practical with no observed material regression.
The Phase 3 synthetic characterization was health 39.295 ms, datasets 187.024 ms,
readiness 37.605 ms, simple analysis 95.095 ms, aging 39.831 ms, net cash 40.890
ms, upload/profile 6.973 ms and grounded session turn 284.032 ms. Final browser
flows completed in seconds and the production build completed in seconds on this
host. These are descriptive observations, not release thresholds; local LLM
latency remains model/hardware dependent.
