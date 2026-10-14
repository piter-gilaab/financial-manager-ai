# Phase 12 — Step 37: LLM mediation contract

## Purpose and central invariant

Phase 12 lets a locally hosted language model act as the **conversational
mediator** between a user and the existing deterministic Financial Manager. The
model may understand natural language and explain authoritative results. It is
never the financial engine.

> **Structured evidence is authoritative truth. LLM output is non-authoritative
> communication.** A mediator proposal only selects among approved, code-owned
> operations; a mediator explanation is displayed only after it passes a
> deterministic grounding guard; any failure falls back to the existing
> deterministic behavior.

This contract extends, and does not replace, the
[security boundaries](security_privacy_boundaries.md), the
[conversation state contract](conversation_state_contract.md) and the
[conversational CLI contract](conversational_cli_contract.md).

## Architecture and authority flow

```text
user language
  -> CLI command check (slash commands stay deterministic, never sent to the LLM)
  -> LLM interpretation (local provider only)
  -> strict MediationIntent validation (closed schema, allowlists, session context)
  -> code-owned dispatch to one existing FinancialManagerSession operation
  -> FinancialManagerAgent -> fresh routing -> capability registry
  -> Financial Core / AnomalyService
  -> authoritative structured result
  -> deterministic GroundedResponsePacket (fact catalog)
  -> LLM verbalization (NaturalResponse JSON)
  -> grounding guard
  -> deterministic presentation (tables/lists/notes from evidence) + validated prose
  -> user
```

Authority hierarchy (a lower level never overrides a higher one):

1. approved source data / snapshot;
2. Financial Core / AnomalyService structured evidence;
3. manager structured outcome (status, capability availability, clarification);
4. conversational mediation (validated intent, bounded alias context);
5. natural-language explanation.

## Mediator responsibilities

The mediator MAY:

- interpret natural user language in English or Portuguese and normalize
  paraphrases;
- choose one **approved request identifier** from a closed, code-owned catalog;
- identify that clarification is needed, from a closed list of clarification kinds;
- map a natural reply to the canonical value of a clarification that the session
  currently holds;
- request one of the two existing evidence follow-ups for one session-issued
  reference label;
- request a presentation style from `TEXT`, `TABLE` or `LIST`;
- write a short explanation from a fact catalog, in the user's language and tone,
  and summarize warnings naturally.

The mediator MUST NOT: execute SQL or shell commands; import code; call tools,
functions or capabilities directly; read the database; perform authoritative
arithmetic (totals, averages, differences, shares, rankings); invent values;
infer or name a currency; override capability status; classify anomalies or turn
CANDIDATE into fraud, error, misconduct, certainty or probability; fabricate
document evidence; or unlock Forecasting or Document Retrieval.

## Closed request catalog (decision)

**No LLM-authored string ever reaches routing, the session or the manager.**
Every LLM proposal is an enumerated key that code maps to a fixed canonical
English request already accepted by the existing grammar:

| Request ID family | Canonical requests (examples) | Capability |
|---|---|---|
| `RG_*` | `Receiver General record count`, `Receiver General amounts by department` | Financial Analysis |
| `CF_*` | `Total sales by country`, `Profit summary`, `Discounts by discount band` | Financial Analysis |
| `SCREEN_*` | `Screen accounting amounts`, `Screen sales`, `Screen profit` | Anomaly Detection |
| `CASH_FLOW_FORECAST` | `Forecast cash flow next month` | Cash Flow Forecasting (BLOCKED) |
| `DOCUMENT_QUESTION` | `What does the invoice say?` | Document Retrieval (BLOCKED) |
| `USER_TEXT` | the user's own unchanged words | decided by the deterministic router |

`USER_TEXT` is the explicit pass-through: the user's exact text goes through the
deterministic router, exactly as in Phase 11. It is used for requests the
catalog cannot express (for example explicit filters) and for anything
unsupported, blocked or suspicious, so that the existing refusals stay
authoritative.

A free-text `normalized_request` field was considered and rejected. It would let
the model compose new requests: a mistranslation could add a filter or change a
measure without the user noticing. The closed catalog gives up some
expressiveness for a property that can be checked: the model can only choose
among requests the project already approved, and the chosen canonical request is
shown to the user (`Interpreted request: …`).

The catalog cannot create contracts, does not reference Python functions or
SQL, and does not bypass anything: every catalog request still goes through
`FinancialManagerSession`, fresh Step 18 routing, the registry, Step 13
contract validation or the anomaly validator.

## Structured intent (`MediationIntent` version 1.0)

The interpretation output is one JSON object with exactly these keys. All are
required, and `null` is used where a key does not apply. Unknown, missing or
duplicate keys, wrong types, non-finite numbers, non-allowlisted values or
output over 4 KiB reject the whole proposal. The only wrapper tolerated is one
` ```json ` fence around the entire object, a common local-model habit. Prose
around the object is rejected, and nothing is ever repaired.

The conceptual fields in the request map as follows: `normalized_request` becomes
the closed catalog key `intent` (see above); `clarification` is split into
`clarification_answer` (a reply to the session's pending question) and
`clarification_kind` (a request for a new code-owned clarification), so that one
field never carries two meanings.

| Key | Type | Allowed values |
|---|---|---|
| `version` | string | `"1.0"` |
| `operation` | enum | `NEW_REQUEST`, `ANSWER_CLARIFICATION`, `EVIDENCE_FOLLOWUP`, `REQUEST_CLARIFICATION` |
| `intent` | enum or null | a catalog request ID (`NEW_REQUEST` only) |
| `capability_hint` | enum or null | must equal the catalog entry's capability when present |
| `clarification_answer` | enum or null | one canonical choice of the currently pending clarification (`ANSWER_CLARIFICATION` only) |
| `clarification_kind` | enum or null | `CAPABILITY_CHOICE`, `EVIDENCE_REFERENCE`, `RESTATE_REQUEST` (`REQUEST_CLARIFICATION` only) |
| `evidence_reference` | enum or null | an issued reference label such as `A3` (`EVIDENCE_FOLLOWUP` only) |
| `follow_up_intent` | enum or null | `why_selected`, `record_detail` (`EVIDENCE_FOLLOWUP` only) |
| `presentation_hint` | enum or null | `TEXT`, `TABLE`, `LIST` |
| `response_language` | enum | `en`, `pt-BR` |

Per-operation consistency is enforced. For example, `ANSWER_CLARIFICATION` is
invalid when nothing is pending, and its answer must exactly equal one of the
session's canonical choices (`FINANCIAL_ANALYSIS`, `ANOMALY_DETECTION`,
`receiver_general` or `company_financials`). The answer is then passed to the
existing `session.answer`, which re-validates it. An ambiguous reply leads to a
clarification, and a clearly unrelated reply is a `NEW_REQUEST`, which replaces
the pending clarification under the Phase 10 lifecycle.

`REQUEST_CLARIFICATION` dispatch:

- `CAPABILITY_CHOICE` submits the canonical vague request `Check my financial
  data.`, so the **session** creates and owns the approved pending clarification;
- `EVIDENCE_REFERENCE` and `RESTATE_REQUEST` show a fixed, code-owned localized
  question and call no session operation.

## Bounded mediation context

The only new state is a `MediationContext`: a typed, data-only, in-memory record
that maps short labels (`A1`…`A10`) to the opaque anomaly handles the session
issued for the current result. It contains no financial values, no question text
and no transcript.

It is valid only while all of these are true, checked against
`session.status()` before every use: the session is ACTIVE; its session ID equals
the one that issued the labels; its active context is the anomaly evidence
context; and its reference count equals the number of labels. Otherwise the
context is deleted. Reset, cancel, expiry, a new request and a session rotation
all invalidate it. The authoritative check remains `session.follow_up`, which
re-executes and re-validates the reference. A label is therefore navigation
metadata, never evidence.

The mediator creates no other memory system. Natural follow-ups are supported
only when they can be rebuilt from this context: a specific label, or a single
issued reference when the user says "why was that flagged?". Anything else
(for example "And Canada?") leads to a clarification, not a guess.

## Grounded response generation

Only results that carry evidence are verbalized by the model: a single-step
Financial Analysis or Anomaly Detection result with SUCCESS, PARTIAL or NO_DATA,
and a successful evidence follow-up. Clarifications, BLOCKED capabilities,
unsupported/invalid requests and session lifecycle outcomes use **code-owned
localized templates**. For refusals and clarifications without a dedicated
template, the template quotes the router's own controlled message, a fixed
application string written in English and never exception text. This keeps "can you forecast?" style prose, the area where
hallucination is most dangerous, completely deterministic.

The model receives a `GroundedResponsePacket`, never raw application state:

```text
GroundedResponsePacket
  packet_version, language, user_question (bounded), interpreted_request,
  capability, status, subject {dataset, measure, grouping},
  facts:    [Fact {id "F<n>", label, value, unit, semantic_type, source}]
  warnings: [Fact {id "W<n>", ...}]  (currency state, quality, screening terms)
  allowed_presentations, default_presentation, terminology rules
```

The provider message has three sections: the system message holds the rules,
and the JSON data holds `user_input` (the user's words) and `structured_evidence`
(the packet without the question).

Facts are built by deterministic code from authoritative evidence. Values stay
exact source strings. A categorical ranking fact (`rank`) is produced by exact
`Decimal` comparison in code, so the model never ranks. Collections are bounded
(at most 25 groups and 25 ranked records, each with an explicit omitted-count
fact). Hashes,
paths, record IDs, raw formatted tokens such as `" $16,185.00 "`, quality flag
row lists and contract identifiers are excluded.

The model must return `NaturalResponse` JSON with exactly the keys `message`,
`used_fact_ids`, `warning_fact_ids`, `presentation_hint` and `language`.

### Grounding guard

The output is displayed only if every check passes:

- strict schema, sizes (message ≤ 1,200 characters, ≤ 12 lines, raw output ≤ 16 KiB);
- every listed fact or warning ID exists, the declared language matches the packet, and a
  conservative lexical guard does not find an obvious English/pt-BR prose mismatch;
- **every numeral is grounded in a fact the response declares in
  `used_fact_ids`/`warning_fact_ids`**: it matches that fact exactly or as a
  correct rounding/abbreviation (`25,03 milhões`, `25.03 million`,
  `24,887,654.89`) *with the same sign*, and percentages match only percentage
  facts. Derived differences, shares, sign-dropped values and invented counts
  are rejected;
- no currency codes, symbols or currency names (`USD`, `$`, `R$`, `dollars`,
  `reais`, …). At this historical Phase 12 checkpoint, every available
  denomination was `UNKNOWN`, so there was no legitimate reason to name one.
  Steps 66–69 later extended the guard to render explicitly approved
  `CONFIRMED` dynamic currency from evidence without inferring it;
- no fraud, error, misconduct, certainty, probability or suspicion language;
- no multiplicative comparisons written in words (`twice`, `half`, `o dobro`,
  `metade`, `3 vezes`), which are arithmetic the model may not perform;
- no forecasting, cash-flow or document claims;
- no internal identifiers (snake_case keys, contract codes, 64-hex digests,
  paths), no markdown tables or code fences, and no control characters.

On any failure, nothing the model wrote is shown. The turn uses the existing
Phase 11 deterministic presentation instead.

The response prompt also binds every sentence to the packet language and asks for
normal analyst communication: direct answer first, relevant evidence, material
coverage/exclusions, then a relevant warning or supported next action when useful.
It avoids router/schema vocabulary and does not duplicate the evidence-rendered
table or list. The lexical guard is intentionally small: it catches prose dominated
by common words of the other supported language, not mixed source names or short
language-neutral text. It is a fail-closed backstop, not a general language classifier.

### Presentation

The model can only *request* `TEXT`, `TABLE` or `LIST`, chosen from the packet's
`allowed_presentations`. Tables and lists are rendered by code **directly from
the authoritative evidence**, using exact values with locale digit grouping
(string grouping only; no arithmetic). Defaults: record count → text; summary →
text plus metric list; grouped result → text plus table (categorical groups
ordered by exact value, periods in evidence order); extreme records and anomaly
candidates → bounded table; follow-up → list. Required disclosures are always
added deterministically: UNKNOWN currency, coverage/exclusions, CANDIDATE /
NOT_ASSESSED terminology and the interpreted request.

## Failure model

The financial system must remain usable when the model is unavailable, times
out, returns malformed or invalid JSON, proposes an unsupported or inconsistent
intent, includes prohibited fields, or violates grounding.

| Failure point | Fallback |
|---|---|
| interpretation provider error, timeout or oversize | `session.new_request(original text)`, which is the exact Phase 11 behavior |
| invalid / inconsistent / prohibited intent | same as above |
| unresolvable follow-up label | code-owned clarification; no session operation |
| response provider error or grounding violation | Phase 11 deterministic concise presentation of the same authoritative outcome |

A fallback never retries the model, never shows the model's text or error
details, and shows only a fixed one-line notice. Provider failures cannot make
the financial system unavailable. Without `--llm-model`, chat behaves exactly
as in Phase 11.

## Provider and privacy model

```text
MediationProvider (complete(request) -> raw text)
├── LocalHTTPProvider     LOCAL      active category; loopback only
├── ScriptedProvider      LOCAL      deterministic test provider
├── PRIVATE provider      disabled   no implementation; needs separate approval
└── EXTERNAL provider     disabled   no implementation; needs separate approval
```

The existing `ProviderLocation` vocabulary is reused. The mediator refuses any
provider whose location is not LOCAL before calling it. `LocalHTTPProvider`:

- calls an explicitly configured OpenAI-compatible chat-completions endpoint;
- accepts only `http`/`https` URLs whose host is `localhost`, `127.0.0.0/8` or
  `::1`, with no credentials in the URL, so other hosts are rejected at
  construction;
- ignores proxy environment variables and refuses redirects, so data cannot
  silently leave loopback;
- uses a bounded timeout (default 30 s, maximum 120 s) applied both per socket
  operation and as a whole-call deadline, a bounded request and response size
  (64 KiB), temperature 0 and JSON response format;
- makes no retries, sends no API key, and maps every error to a fixed message
  without echoing exception text.

`localhost` is resolved by the operating system. A modified hosts file is a
host-configuration risk outside the application boundary. Use `127.0.0.1` to
avoid name resolution entirely.

Nothing is persisted: no prompt or response logging, no transcript, no telemetry.
Financial facts are sent only to the configured loopback model. Automated tests
use `ScriptedProvider` or an injected transport, with no network, model, GPU or
credentials.

## Prompt-injection boundary

Prompts separate **SYSTEM RULES** (system message) from **DATA** (one JSON user
message). For interpretation, the data is `allowed_requests`,
`pending_clarification_choices`, `issued_reference_labels` and `user_input`, with
no evidence or values. For responses, the data is the `GroundedResponsePacket`. User text,
dataset strings, evidence labels and source values are data and never
instructions. The injection defense does not depend on the model obeying: an
injected instruction can at most change which allowlisted enum the model emits
or what prose it writes, and both pass through the validators above.

## Language

Language is a mediation/presentation property (`en`, `pt-BR`). Financial logic is
never duplicated per language. Canonical requests are English because the
deterministic grammar is English. Templates, notes, table headers and digit
grouping are localized. Natural response prose is both prompted and validated:
an obvious mismatch falls back without displaying model text. Source names and
values may remain unchanged.

## Test seams (agreed for Steps 38–41)

1. `parse_intent(raw, context)` and `validate_natural_response(raw, packet)`: pure validators.
2. `LocalHTTPProvider.complete` with an injected transport, and URL validation.
3. `build_packet(outcome, …)`: the fact catalog built from real evidence.
4. `ConversationMediator.handle(text)`: real session/manager plus `ScriptedProvider`.
5. `src.cli.main(["chat"], session=…, mediator=…)` and one real subprocess.

## Non-goals

No financial calculation by the model, arbitrary SQL/tools, direct database
access, persistent memory or transcripts, external/private providers,
Forecasting, RAG, anomaly algorithm changes, currency inference, fraud detection,
web UI, or Phase 13 work.

## Phase 17 Steps 66–67: structured intent version 1.1

Version 1.1 is additive and the validator continues to accept the exact legacy
version-1.0 shape. The provider-facing schema now adds two operations,
`SELECT_DYNAMIC_DATASET` and `DYNAMIC_FINANCIAL_ANALYSIS`, and four nullable
fields: `dataset_id`, `dynamic_operation`, `period_granularity` and
`missing_dimension`. Dataset IDs are per-turn enums from the bounded catalog;
operations are the exact nine `SALES_RECORD` values; parameter enums remain
`MONTH|YEAR` and `BUCKET|EXCLUDE`. Unknown keys/values and inconsistent field
combinations still reject the whole proposal.

Interpretation context adds only safe catalog metadata (limit 20), one current
opaque selection, one last closed operation, and exact IDs found by code in the
current turn. It contains no filename, path, row, value, sample, profile, mapping
or transcript. Multiple, malformed, unknown, path-derived and out-of-catalog IDs
fail closed. With no explicit/current selection, even one catalog entry requires
the user to select its exact ID. A current/explicit dynamic target cannot be
silently redirected by the model to a legacy analysis or anomaly request.

Validated dynamic analysis calls the session's deterministic resolver and then
`FinancialManagerAgent.execute_dataset_request`; the mediator never constructs
an executable string. Dynamic evidence feeds the unchanged fact catalog and
grounding guard. `UNKNOWN` and approved `CONFIRMED` currency are rendered from
evidence; currency is never inferred. If response generation fails, code renders
the same authoritative evidence. If interpretation fails while a dynamic target
is present, nothing is executed rather than substituting a legacy dataset.

At the Steps 66–67 checkpoint, dynamic anomaly language returned a code-owned
Step-68 deferral and never invoked `execute_dataset_anomaly_request`. The next
section supersedes that historical boundary. Forecasting and Document Retrieval
keep their existing deterministic blockers.

## Phase 17 Steps 68–69: structured intent version 1.2

Version 1.2 adds only `DYNAMIC_ANOMALY_SCREEN` and extends the existing
`dynamic_operation` enum with `SALES_ANOMALY_SCREEN|PROFIT_ANOMALY_SCREEN`.
Exact version-1.0 and version-1.1 shapes remain accepted. Dataset IDs remain
per-turn catalog enums. The action accepts no algorithm, threshold, peer group,
filter, source column or executable request text.

The historical `DYNAMIC_ANOMALY_DEFERRED` clarification remains valid only in an
exact version-1.1 compatibility payload. It is absent from the provider-facing
version-1.2 schema and rejected when proposed under version 1.2.

The safe catalog entry adds anomaly state and currently supported anomaly
operation identifiers; the 20-entry bound and row/value/path exclusions remain.
`EVIDENCE_FOLLOWUP` is reused for `why_selected|record_detail` only when a current
A1–A10 label exists. Grounding receives bounded facts derived from authoritative
Phase 16 evidence. Provider failure, invented IDs/labels/operations and fraud or
numeric fabrication execute nothing or fall back to code-owned presentation.
