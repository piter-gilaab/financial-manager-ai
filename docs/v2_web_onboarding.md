# V2 Phase 4 — Dataset Onboarding Workspace

`/datasets/new` implements five explicit stages:

1. Upload — drag/drop or picker for bounded CSV/XLSX multipart upload.
2. Profile — rows, columns, duplicate candidates, missingness, cardinality and
   bounded source examples from the deterministic backend profile.
3. Semantics — source columns, suggestions, rationale and explicit
   confirm/correct/reject actions. Suggestions never become authority silently.
4. Confirm — explicit executable-domain choice and applicable qualifiers.
5. Ready — backend operation states and reasons, with Analyze enabled only for
   an executable operation.

HTTP 409 `CLARIFICATION_REQUIRED` with sheet choices becomes an XLSX sheet
selection interaction, not an error toast. Payable/Receivable screens expose
the closed `OUTSTANDING_BALANCE` and `dataset_reference_date` qualifiers; Cash
exposes the two API-approved amount conventions. Reference-date copy explains
that it is the approved observation date and that today is not substituted.

STATUS, CASH_DIRECTION and CURRENCY decisions pass only bounded observed-value
mappings to the actual semantic decision endpoint. The frontend does not infer
the mappings or domain.
