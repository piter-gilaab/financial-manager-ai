# Phase 12 — Step 38 validation

## Decision

**PASS.** The provider abstraction and the closed `MediationIntent` schema are
implemented in `src/mediation/` as the [contract](llm_mediation_contract.md)
specifies. No financial, routing, session or anomaly code changed.

## Implemented

- `catalog.py`: 25 code-owned canonical requests (20 analysis, 3 screening,
  2 blocked) plus the `USER_TEXT` pass-through. The LLM selects a key; it never
  writes a request.
- `models.py`: closed vocabularies (operations, clarification kinds, follow-up
  intents, presentations `TEXT`/`TABLE`/`LIST`, languages `en`/`pt-BR`;
  capabilities derived from the manager's `Capability` enum) and typed records.
  `InterpretationContext` accepts only tuples of text.
- `validation.parse_intent`:
  - accepts one JSON object of at most 4 KiB, optionally wrapped in a single
    ```` ```json ```` fence;
  - requires the exact key set and version `1.0`;
  - checks every value against an allowlist;
  - enforces per-operation fields;
  - accepts a clarification answer only if it is a canonical choice that is
    currently pending, and a reference only if it is an issued label;
  - accepts a capability hint only if it equals the catalog entry's capability;
  - rejects duplicate keys and NaN.
- `provider.py`: `ProviderRequest`, `ProviderFailure`, the `MediationProvider`
  protocol, and the deterministic `ScriptedProvider` (LOCAL, no network).
- `local_provider.LocalHTTPProvider`:
  - talks to a loopback-only OpenAI-compatible endpoint; credentials, other
    hosts and invalid ports are rejected without echoing the URL;
  - uses no proxy and refuses redirects;
  - bounds each socket operation and the whole call;
  - caps requests and responses at 64 KiB;
  - sends `temperature 0` and `response_format json_object`;
  - makes one attempt, sends no API key, and reports every failure with one
    fixed message.
- `prompts.py`: versioned system prompts built with the RSCIT and few-shot
  pattern from `llm-prompt-optimizer`. Rules live only in the system message;
  the user message is a JSON data document.

## Tests

`tests/test_mediation_intent.py`, 20 tests:

- schema acceptance;
- malformed, oversized, duplicate, unknown and missing fields;
- SQL-, shell- and import-shaped values;
- pending-choice and issued-label rules;
- operation consistency and the fence tolerance;
- URL allow and deny lists, including `127.0.0.1@evil`, `0.0.0.0` and
  credentials;
- the request body and the absence of credentials;
- fixed transport errors with no retries;
- malformed and oversized envelopes, and prompt-size refusal;
- a proxy environment that is ignored, and redirects that are refused;
- a trickling server cut off by the deadline (injected opener, no socket);
- the prompt boundary;
- every catalog text routing to its declared capability.

No test uses a network, model, account, key or GPU.

## Review

The boundary `code-review` found no path to a non-loopback host. Fixes applied:

- type checks on `InterpretationContext`;
- the whole-call deadline;
- the catalog routing regression test;
- one shared capability vocabulary and a single permitted/required table;
- documentation of the fence tolerance, the `localhost` resolution risk and the
  field renames.
