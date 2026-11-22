# V2 Phase 4 — Web Validation

## Acceptance matrix

| ID | Capability | Result |
|---|---|---|
| A | Next.js App Router foundation | PASS |
| B | TypeScript strict validation | PASS |
| C | Central design tokens | PASS |
| D | Institutional Financial Workspace style | PASS |
| E | Responsive app shell | PASS |
| F | Sidebar navigation | PASS |
| G | API health | PASS |
| H | Typed central API client | PASS |
| I | Generated OpenAPI contract alignment | PASS |
| J | Dataset-aware Overview | PASS |
| K | Dataset list | PASS |
| L | Dataset detail | PASS |
| M | Readiness visualization | PASS |
| N | CSV upload | PASS |
| O | XLSX upload | PASS |
| P | Multi-sheet clarification | PASS |
| Q | Bounded profile view | PASS |
| R | Explicit semantic mapping | PASS |
| S | Explicit domain confirmation | PASS |
| T | Qualifiers/value mappings | PASS |
| U | Readiness completion | PASS |
| V | SALES_RECORD analysis | PASS |
| W | PAYABLE analysis | PASS |
| X | RECEIVABLE analysis | PASS |
| Y | CASH_TRANSACTION analysis | PASS |
| Z | Period visualization | PASS |
| AA | Dimension visualization | PASS |
| AB | Aging visualization | PASS |
| AC | Coverage | PASS |
| AD | Limitations | PASS |
| AE | Safe lineage | PASS |
| AF | Sales anomaly | PASS |
| AG | Profit anomaly | PASS |
| AH | Candidate table | PASS |
| AI | Candidate detail/follow-up | PASS |
| AJ | Chat session | PASS |
| AK | Exact dataset chat context | PASS |
| AL | Chat clarification | PASS |
| AM | Closed chat follow-up | PASS |
| AN | Provider failure UX | PASS |
| AO | Exact Decimal display | PASS |
| AP | Currency display | PASS |
| AQ | Blocked state | PASS |
| AR | Unsupported state | PASS |
| AS | No-data state | PASS |
| AT | API-offline state | PASS |
| AU | 1440 responsive | PASS |
| AV | 1024 responsive | PASS |
| AW | 768 responsive | PASS |
| AX | 390 responsive | PASS |
| AY | Accessibility/security/privacy | PASS |
| AZ | Backend authority preserved | PASS |

## Validation scope

Vitest covers transport serialization, exact decimals, currency, status,
operation blocking, clarification, onboarding transitions, result rendering,
candidate terminology, chat session/provider states, privacy and the no-financial-
arithmetic scan. Playwright uses real HTTP for the critical upload, detail,
four-domain analysis, two anomaly, session/clarification and responsive paths.

Responsive screenshots are captured at 1440, 1024, 768 and 390 pixels plus
dataset detail, ready onboarding, analysis evidence, anomaly result and chat
clarification states. Keyboard labels, semantic headings, focus visibility,
textual status, mobile drawer and horizontal table overflow are checked in code
and browser interaction.

Final command totals: TypeScript typecheck PASS; ESLint PASS; Vitest 10 files,
33 tests PASS; Next.js production build PASS; Playwright Chromium 11 tests PASS;
Python regression 773 tests PASS. The responsive visual pass found and corrected
a screenshot timing defect in the mobile drawer and removed the development-only
indicator from validation captures.

Security/privacy inspection found no `dangerouslySetInnerHTML`, user-supplied
endpoint, API secret, external font, telemetry, analytics, browser transcript
persistence or arbitrary URL fetch. React renders malicious labels and prompt
text as inert text.
