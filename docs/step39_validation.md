# Phase 12 — Step 39 validation

## Decision

**PASS.** Natural language reaches the existing system only through
`ConversationMediator.handle(text)`, which performs at most one existing
`FinancialManagerSession` operation per turn.

## Implemented

- `src/mediation/mediator.py` dispatches each operation:
  - `NEW_REQUEST` calls `session.new_request` with a catalog text, or with the
    user's own words for `USER_TEXT`;
  - `ANSWER_CLARIFICATION` calls `session.answer` with an exact pending choice;
  - `EVIDENCE_FOLLOWUP` calls `session.follow_up` with the handle mapped from an
    issued `A1`–`A10` label, or with the single issued handle when no label is
    named;
  - `REQUEST_CLARIFICATION` either sends the canonical vague request, so that
    the session owns the capability clarification, or returns a code-owned
    question and runs no operation.
- Label context (`MediationContext`):
  - It is typed, data-only and in memory.
  - It is revalidated against `session.status()` on every turn: session ID,
    `ANOMALY_EVIDENCE` kind and reference count.
  - It is cleared by reset, cancel, expiry or any new request.
- Fallback: provider errors, a provider that is not the LOCAL enum member,
  oversized input and rejected proposals all run `session.new_request(original
  text)` with one fixed notice. This is exactly the Phase 11 behavior.
- CLI:
  - `chat --llm-model [--llm-url] [--llm-timeout]`.
  - Slash commands are handled before mediation and never reach the model.
  - An invalid configuration exits with code 2 and a fixed message.
  - An injected mediator shares its own session with the chat loop.
  - Without `--llm-model`, chat is unchanged.

## Tests

`tests/test_mediation_input.py`, 20 tests, using the real manager and session
with `ScriptedProvider`:

- five PT/EN paraphrases reaching the same CF-04 evidence;
- informal Profit screening;
- the capability clarification and the natural answer `anomalias`;
- an ambiguous reply that keeps the clarification pending;
- an unrelated request that replaces it, with a visible notice;
- Forecasting and RAG blocked, and Sales not accepted as cash;
- SQL, fake-tool and import proposals refused or falling back;
- provider failures, malformed output and oversized output falling back;
- non-LOCAL providers never invoked;
- labelled, unlabelled and ambiguous follow-ups;
- `And Canada?` answered with a clarification;
- reset and expiry clearing labels;
- multi-capability results kept deterministic;
- labels surviving a fallback;
- CLI behavior: slash commands, a PT clarification conversation, the fallback
  notice, configuration validation and the default loopback provider.

## Review and defects

The boundary review reproduced three defects. Each was fixed test-first using
the `diagnosing-bugs` loop:

- a multi-capability success was rendered as a refusal;
- the "pending replaced" notice was missing on text turns;
- labels were discarded after a deterministic fallback.

It also fixed an injected mediator that, given no session, created a second one.
