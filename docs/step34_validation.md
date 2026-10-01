# Phase 11 — Step 34 validation

## Decision

**PASS.** The conversational CLI contract is internally consistent and compatible
with the validated Phase 10 `FinancialManagerSession` architecture. Step 35 may
implement this contract without changing session semantics. Step 36 is not part
of this decision and has not started.

## Repository evidence reviewed

The review compared the contract with:

- `CONTEXT.md`, the single-manager ADR and the technical guide;
- the Step 30 conversation-state contract;
- the Step 31 clarification-continuation contract;
- the Step 32 evidence-reference follow-up contract;
- the Step 33 bounded-conversation validation;
- the existing Step 20/27 CLI and presentation contracts;
- `FinancialManagerSession`, `FinancialManagerAgent`, CLI parsing/formatting and
  their behavior tests; and
- the current repository status and diff.

The existing worktree contained only the user-provided untracked `AGENTS.md`
before Step 34. It is not modified by this phase.

## Compatibility findings

| Step 34 decision | Phase 10 compatibility evidence |
|---|---|
| Plain text is always `new_request` | The session exposes a distinct method that discards prior context before fresh manager routing. |
| `/answer` is explicit | `answer` accepts only a live approved clarification and finite aliases; invalid answers do not execute. |
| `/follow` is explicit | `follow_up` accepts only a current session-issued handle and the two approved intents, then re-executes through `manager.ask`. |
| New text replaces pending state | This is the existing `new_request` transition and does not reinterpret text as an answer. |
| `/status` is redacted | Public `status()` already masks handles, lineage and evidence; the CLI additionally omits session identity. |
| `/cancel` and `/reset` delegate | Both lifecycle operations already exist and perform no financial execution. |
| Expiry is controlled | The session already enforces 30-minute inactivity and four-hour absolute limits and returns controlled outcomes. |
| Concise output is fixed | Conversation state expressly excludes presentation mode; existing Step 27 rendering can be reused per result. |
| No reference resolution in CLI | The session alone validates membership, logical snapshot, digest and fresh authoritative evidence. |
| No second router or engine | The proposed loop selects only explicit session operations and delegates all request meaning. |

## Domain-modeling result

No financial-domain definition changed. “Conversational CLI”, “slash command”
and “session lifecycle” are interface concepts rather than project-specific
financial vocabulary, so `CONTEXT.md` remains a glossary and is not changed.
No ADR is warranted: the additive local input adapter is reversible, follows the
already accepted single-manager architecture and introduces no new hard-to-reverse
architectural trade-off.

## Resolved interaction decisions

- Entry point: `python -m src.cli chat`.
- Chat presentation: concise human output only; chat rejects `--json`/`--full`.
- Prompt: ordinary prompt plus only a `[clarification]` indicator.
- Reserved slash prefix: malformed or unknown slash commands never become
  financial questions.
- Interrupt policy: Ctrl+C, EOF and `/exit` end cleanly; empty input is ignored.
- Expiry policy: no retry or implicit continuation; a later plain-text request is
  explicitly new, and `/reset` explicitly rotates the session.
- Status policy: use only the public redacted projection and omit session ID.
- Unsupported clarification policy: require a complete new request rather than
  reconstructing it in the CLI.

## Scope check

The contract adds no new capability, query contract, routing rule, dependency,
provider, storage, database access, financial calculation, anomaly behavior,
evidence authority or terminal/TUI framework. It preserves Forecasting and RAG
as blocked and keeps full/JSON evidence on the existing one-shot commands.

