# Phase 12 — Step 37 validation

## Decision

**PASS.** The LLM mediation architecture is explicit before any implementation:
[LLM mediation contract](llm_mediation_contract.md), the
[closed-catalog ADR](adr/0002-llm-como-mediador-com-catalogo-fechado.md) and two
glossary terms in `CONTEXT.md` (*Evidência estruturada*, *Mediação
conversacional*). No production code changed in this step.

## Context reconstructed

The contract was derived from the repository rather than from the request alone:

- `FinancialManagerSession` already owns the clarification/evidence lifecycle,
  expiry and the two approved clarification types. The mediator dispatches to its
  public operations and adds no second chat memory.
- Step 18 routing and the Step 13 grammar are bounded English. Every proposed
  canonical catalog request was checked against the live manager. All 25
  canonical requests route as intended (20 analysis variants, 3 screening
  targets, 2 blocked capabilities). `Check my financial data.` yields the
  approved `capability_required` clarification.
- Group evidence is returned in key order, not value order. Ranking facts are
  therefore defined as deterministic `Decimal` comparisons in code, not as model
  judgement.
- The existing `ProviderLocation` (LOCAL/PRIVATE/EXTERNAL) vocabulary and the
  "non-LOCAL fails closed before invocation" rule are reused.
- The runtime is standard-library-only. The local provider therefore uses
  `urllib`, with proxies and redirects disabled.

## Requirement coverage

| Requirement | Contract section |
|---|---|
| Mediator MAY / MUST NOT | Mediator responsibilities |
| Authority model and hierarchy | Architecture and authority flow |
| Failure model and fallback | Failure model |
| Privacy / provider categories | Provider and privacy model |
| Conversation model (reuse session; typed, expiring mediation context) | Bounded mediation context |
| Structured intent schema | Structured intent |
| Capability/contract mapping | Closed request catalog |
| Grounded packet, fact catalog, natural response, guard | Grounded response generation |
| Presentation contract | Presentation |
| Prompt-injection boundary | Prompt-injection boundary |
| Language | Language |
| Test seams for TDD | Test seams |

## Skills

`domain-modeling` produced the glossary terms and an ADR that meets all three
ADR criteria: hard to reverse, surprising without context, and a real trade-off.
`codebase-design` was used to decide where the mediator plugs in. There is one
deep module, `ConversationMediator.handle(text)`, behind which interpretation,
validation, dispatch, grounding and rendering are hidden. It has one real
provider seam with two adapters (local HTTP and scripted test). The `tdd` skill
asks for test seams to be agreed before tests are written. They are recorded in
the contract because the user requested sequential completion without
intermediate approval.

## Open limitations accepted by the contract

- Catalog requests are unfiltered. Filtered or period-specific analysis remains
  available only through `USER_TEXT` in the deterministic English grammar.
- The guard verifies numerals, currency, terminology and capability claims. It
  cannot fully verify non-numeric associations, for example which entity a
  correct number is attributed to. The evidence-rendered table remains the
  authoritative view.
- A valid but semantically wrong catalog choice can answer a different
  *approved* question. The interpreted request is always displayed.
