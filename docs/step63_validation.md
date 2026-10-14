# Step 63 — dynamic anomaly readiness validation

## Result

PASS. Dataset capability discovery now evaluates exactly
`SALES_ANOMALY_SCREEN` and `PROFIT_ANOMALY_SCREEN` through a trusted,
non-presenting adapter probe. `ANOMALY_DETECTION` becomes
`AVAILABLE_WITH_LIMITATIONS` only when at least one current operation is
executable; otherwise it is `BLOCKED`.

## Validated behavior

- Sales supported with Profit absent produces partial capability availability.
- Profit can remain supported when the supplied Sales series has zero IQR,
  provided the shared `SALES_RECORD` domain approval remains valid.
- both operations can be independently supported or blocked;
- 29 usable values block and 30 with positive IQR support each operation;
- zero IQR and precision-60 arithmetic infeasibility block before availability;
- UNKNOWN and one CONFIRMED denomination allow otherwise valid screening;
  CONFIRMED_MULTIPLE blocks scalar readiness;
- Profit revocation blocks only Profit; Sales/domain-anchor revocation blocks the
  domain; approved restoration recovers through fresh evaluation;
- changed source bytes and registry corruption revoke readiness; exact source
  restoration recovers without a cached fence or authorization;
- an unavailable compatible adapter/policy is never reported supported;
- readiness JSON contains no record assessments or candidate references;
- human and JSON dataset capability discovery expose typed operation states and
  controlled reasons.

Financial Analysis remains the fixed nine-operation dynamic catalog. The legacy
Receiver General and Company Financials anomaly service is unchanged.
Forecasting and Document Retrieval/RAG remain blocked.

## Scope boundary

No Financial Manager anomaly execution method, conversation route, session
reference, anomaly execution CLI, peer grouping, additional measure, algorithm,
network call or external model was added. Step 64 remains unimplemented.

## Verification

- Step 63 focused readiness/onboarding/capability/CLI/anomaly suites: **114
  passed, 0 failed, 0 errors, 0 skipped**.
- Complete project regression: **647 passed, 0 failed, 0 errors, 0 skipped** in
  470.396 seconds. This is the 615-test baseline plus 32 Step 62–63 tests.
- Existing security/privacy suite: **18 passed**.
- `git diff --check`: passed.
- Security static scan: no new executable dispatch, shell, subprocess, dynamic
  import, eval/exec or SQL path; the only match was the existing deterministic
  retrieval method name.
- Unfinished-marker scan: passed.

The parallel Standards review found no hard violation. Its duplicated catalog
and CLI rendering findings were corrected by reusing the anomaly registration
projection and one bounded presentation helper. The parallel Spec review found
one operation-independence defect: shared compatibility incorrectly required
both adapter operations. Compatibility is now checked per operation; a
Sales-only compatible adapter leaves Sales supported and Profit unsupported.
Stale-profile and incompatible-policy acceptance were also added.
The final audit then removed a persisted dataset capability state from screening
evidence so an older valid readiness report cannot be presented as fresh
execution evidence or treated as authority.
