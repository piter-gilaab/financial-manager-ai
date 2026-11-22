# V2 Phase 4 — Anomalies and Ask Financial Manager

`/anomalies` offers exactly `SALES_ANOMALY_SCREEN` and
`PROFIT_ANOMALY_SCREEN` for SALES_RECORD datasets. Its mandatory framing is
“Statistical candidates for review.” The table and detail panel show only
returned assessment, observed value, tail, fences, policy/version, counts and
bounded identifiers. No quartile, fence, probability, fraud, error, suspicion
or causal inference is calculated in the browser.

`/chat` creates one process-local API session on mount. Transcript and selected
context are held only in React memory; no cookie, localStorage or IndexedDB is
used. Dataset changes send an explicit exact-ID selection turn. User questions,
clarification answers and the two closed evidence follow-ups are delegated to
the session API.

`CLARIFICATION_REQUIRED` renders an interaction. Provider/network failure
renders a controlled state and never fabricates a response. Any financial
evidence shown in the transcript is the structured API payload. Small evidence
is rendered exactly; exceptionally large orchestration payloads use a bounded
structural projection so the transcript remains responsive, with the Analysis
workspace identified as the complete tabular evidence surface.
