# V2 Phase 4 — Overview and Datasets

The Overview reports only safe workspace metadata: registered dataset count,
current approved-domain distribution, local API health and explicit runtime
dataset context. It contains no invented revenue, profit, growth, balance,
expense or cash KPI.

`/datasets` is a dense table of actual API fields: source filename, exact
dataset ID, approved domain, lifecycle, readiness, operation count and currency
state. IDs may truncate visually but remain available through title text and
exact route selection.

`/datasets/[datasetId]` loads detail, bounded profile, heterogeneous mapping
history and operation-specific readiness concurrently. It shows backend reasons
for blocked operations, safe digests and limitations. Server paths are filtered
from technical presentation. Analysis is offered only when the backend reports
an executable `SUPPORTED` or `READY` operation.

Empty and API-offline states lead to the relevant next action without assuming
that Sales, Payables, Receivables and Cash coexist.
