# Financial Manager AI V1 Demo Walkthrough

This is a bounded **5–10 minute** technical portfolio walkthrough. It uses the
approved local legacy snapshot plus a temporary synthetic `SALES_RECORD` file.
It does not require a live LLM, external service or private demo dataset.

## Before the timed demo

From the repository root, activate the CPython 3.14.7 environment and verify the
approved legacy setup:

```sh
source .venv/bin/activate
python -m src.provisioning
```

Create and onboard the temporary synthetic file by following Sections 7–10 of
the [`V1 usage guide`](v1_usage_guide.md). Keep the returned dataset ID available:

```sh
DATASET_ID=ds_replace_with_the_returned_id
```

The generated file has 31 rows, all eight demo columns, Sales values 0–29 plus
100, and Profit values 0–29 plus 200. It is synthetic, disposable and never committed.

If a compatible local model is already running, keep its model name available.
Otherwise use the scripted-provider acceptance command in Step 7 below.

## 1. Establish the scope — about 30 seconds

```sh
python -m src.cli capabilities
```

Point out:

- Financial Analysis and Anomaly Detection are available.
- Forecasting and Document Retrieval are visibly blocked.
- Global capability state is not dynamic dataset readiness.

## 2. Show deterministic legacy analysis — about 45 seconds

```sh
python -m src.cli ask "How many Company Financials records are there?"
```

The approved snapshot returns `SUCCESS` and 700 source records. Explain that the
count, coverage, warnings and lineage are deterministic structured evidence; the
presentation does not recalculate them.

Optional structured form:

```sh
python -m src.cli ask "How many Company Financials records are there?" --json
```

## 3. Show safe onboarding — about 90 seconds

If onboarding was prepared before the demo, show its current artifacts instead
of creating another copy:

```sh
python -m src.cli dataset status "$DATASET_ID" --json
python -m src.cli dataset profile "$DATASET_ID" --json
python -m src.cli dataset mappings "$DATASET_ID" --json
```

Explain the separation:

1. ingestion preserves source bytes;
2. profiling reports structure without asserting financial meaning;
3. semantic decisions record explicit evidence and versions;
4. registration/readiness happens only after required confirmation.

For a live-from-zero demo, run the generator, `dataset add` and confirmation
commands from the usage guide. Do not confirm roles for a real file merely to
make the demonstration pass.

## 4. Show operation-specific readiness — about 45 seconds

```sh
python -m src.cli dataset capabilities "$DATASET_ID"
```

The complete synthetic mapping supports exactly nine Financial Analysis
operations and two anomaly operations. Show that currency remains `UNKNOWN`
because no denomination evidence exists, and that Forecasting/RAG stay blocked.

## 5. Show conversational dynamic analysis — about 90 seconds

When a compatible local model is already available:

```sh
python -m src.cli chat --llm-model YOUR_LOCAL_MODEL
```

Enter the actual runtime ID:

```text
Use dataset ds_<runtime-generated-id>.
Show sales by country.
Now by product.
/status
```

Explain that the model selects a closed intent; the session and Manager resolve
the exact dataset, recompute readiness and delegate to deterministic execution.
No row values, paths or full profile enter the interpretation prompt.

If no local model is available, do not download one. Continue with Step 7's
scripted-provider validation and describe these prompts as the human-facing form
of that same tested route.

## 6. Show anomaly screening and follow-up — about 90 seconds

In the same mediated chat:

```text
Check Sales for anomalies.
Why was A1 selected?
/follow A1 record_detail
Check Profit for anomalies.
```

For the documented synthetic fixture, the deterministic test records a Sales
upper-tail candidate with observed value `100` and a Profit candidate with value
`200`. `A1` may be used only after the current result issues it.

State the safety boundary explicitly:

> `CANDIDATE` means statistical candidate for review. It does not mean fraud,
> error or suspicious activity.

The `why_selected` result is bounded to the observed value, applicable fence,
tail and policy. `record_detail` is not an arbitrary row lookup.

## 7. Reproduce the full conversation without a live model — about 30 seconds

This focused acceptance test uses a deterministic `ScriptedProvider`, temporary
onboarding artifacts and the same Manager/session/mediation interfaces:

```sh
python -B -m unittest \
  tests.test_conversational_dynamic_execution_end_to_end.ConversationalDynamicExecutionEndToEndTests.test_primary_persisted_flow_all_nine_financial_operations_and_anomalies
```

Expected bounded result:

```text
Ran 1 test

OK
```

The test executes exact dataset selection, all nine dynamic Financial Analysis
operations, both anomaly screens and `why_selected`. It asserts the known
synthetic candidate values instead of inventing demo output.

## 8. Demonstrate fail-closed product gates — about 45 seconds

```sh
python -m src.cli ask "Forecast cash flow next month"
python -m src.cli ask "Read invoice 123"
```

Both commands return controlled `CAPABILITY_UNAVAILABLE` outcomes. A selected
dataset or model phrasing cannot activate Forecasting or Document Retrieval/RAG.

## 9. Close with the authority model — about 30 seconds

Summarize the demonstrated chain:

```text
language -> closed intent -> Manager -> current readiness
         -> deterministic Core/anomaly engine -> structured evidence
         -> bounded presentation
```

The LLM can interpret and explain; it cannot create financial truth. Raw values,
confirmed semantics, exact decimals, policy versions, candidate classifications
and lineage stay under deterministic code authority.

## Cleanup

The synthetic source can be removed from `/tmp` using the operator's normal
file-management workflow. Its accepted copy and registry state remain in the
Git-ignored `data/onboarding/` directory until the operator deliberately manages
that local state. This walkthrough never deletes user data automatically.

## Demo boundaries

- No live model is required; real local-model latency is hardware-dependent.
- No private dataset is displayed or committed.
- No external provider, telemetry or download is used.
- No arbitrary SQL/filter/algorithm is available.
- Only approved `SALES_RECORD` has generic dynamic execution.
- Dynamic anomaly remains GLOBAL-only Tukey-IQR v1.0 for Sales/supplied Profit.
- Forecasting and Document Retrieval/RAG remain blocked and deferred to V2.
