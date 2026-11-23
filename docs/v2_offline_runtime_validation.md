# Financial Manager AI V2 — Offline Runtime Validation

Status: **PASS** for local-first, offline-capable runtime after provisioning.

## Controlled conditions

Dependencies and the production Web build were already installed. Ten backend
workflow tests ran successfully inside a new Linux network namespace with no
external route. A second 11-test Chromium E2E run set `HTTP_PROXY`, `HTTPS_PROXY`
and `ALL_PROXY` to a closed loopback endpoint while `NO_PROXY` allowed only
`127.0.0.1,localhost`. This preserved Browser -> Next.js -> FastAPI loopback while
making ordinary external HTTP access unavailable. Static review found no mandatory
runtime direct-socket/external fetch path.

The host sandbox could not bring loopback up inside the isolated namespace, so
backend no-network execution and real loopback browser execution were exercised
as complementary controlled runs rather than one namespace. This is a test-method
limitation, not a runtime dependency.

## Validated workflows

| Workflow | Evidence | Result |
|---|---|---|
| Backend creation and health | in-process ASGI plus real Uvicorn E2E startup | PASS |
| Frontend start/build | installed production build and real Next E2E server | PASS |
| Dataset list/detail | real HTTP browser flow | PASS |
| CSV onboarding/profile | isolated backend and real browser flow | PASS |
| Constrained XLSX and sheet choice | isolated backend and real browser flow | PASS |
| Semantic/domain/qualifier confirmation and readiness | isolated backend plus browser flow | PASS |
| `SALES_RECORD` analysis | real FastAPI HTTP/browser | PASS |
| All six `PAYABLE` operations | isolated backend; representative browser HTTP | PASS |
| All six `RECEIVABLE` operations | isolated backend; representative browser HTTP | PASS |
| All six `CASH_TRANSACTION` operations | isolated backend; representative browser HTTP | PASS |
| Sales/Profit anomaly | isolated backend plus real browser HTTP | PASS |
| Conversation/provider unavailable | controlled local behavior | PASS |

## Network authority inventory

- Required local loopback: browser/Next.js to FastAPI (`127.0.0.1:8000`).
- Optional local loopback: local OpenAI-compatible model, default
  `127.0.0.1:11434`; redirects, proxies and non-loopback endpoints are refused.
- Installation/development only: Python/npm registries, Git hosting, documented
  publisher links and optional browser installation.
- Unexpected external mandatory runtime paths: none found.

## Approved claim

Financial Manager AI V2 is **local-first and offline-capable after installation
and data provisioning**. It is not offline-only. Clone, package installation,
updates and obtaining the private legacy bundle may require authorized network or
custodian access; mandatory deterministic runtime financial analysis does not.
