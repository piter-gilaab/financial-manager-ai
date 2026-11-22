# V2 Phase 4 — Web Implementation

Phase 4 implements the local **Institutional Financial Workspace** in `web/`
with Next.js App Router, strict TypeScript and Tailwind CSS. It is a presentation
adapter over the existing `/api/v1`; it does not reproduce Manager, readiness,
currency, anomaly or financial logic.

## Modules and seams

- `web/lib/api-client.ts` is the single HTTP seam. It owns the configured base
  URL, JSON/multipart transport and structured failure mapping.
- `web/openapi.json` is exported from the actual FastAPI application and
  `web/lib/api-schema.ts` is generated from it.
- `web/components/workspace-provider.tsx` owns runtime-only portfolio and
  selected-dataset presentation state.
- route modules own product interaction; reusable evidence and workflow modules
  keep transport details and result-shape handling local.

The interface is intentionally small: callers choose a closed action and
receive the authoritative envelope. There is no frontend adapter selection,
formula, SQL, arbitrary grouping or financial computation.

## Local development

Backend, from the repository root:

```sh
source .venv/bin/activate
FINANCIAL_API_CORS_ORIGINS=http://127.0.0.1:3000 python -m src.api
```

Frontend, in a second terminal:

```sh
cd web
cp .env.example .env.local
npm install
npm run dev
```

Open `http://127.0.0.1:3000`. CORS remains off when the backend environment
variable is absent. Its development parser accepts explicit HTTP loopback
origins only and rejects wildcard, remote, path-bearing or HTTPS values.

## Commands

```sh
cd web
npm run contracts
npm run typecheck
npm run lint
npm test
npm run build
npm run test:e2e
```

The Playwright gate starts an isolated FastAPI application with synthetic data;
it does not use or persist private project data.
