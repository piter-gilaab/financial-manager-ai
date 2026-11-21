---
status: accepted
---

# FastAPI e Next.js na V2 local

A V2 usará FastAPI com contratos Pydantic v2 no adaptador HTTP local e Next.js
com TypeScript no Financial Workspace. A escolha mantém o backend junto do
runtime Python/Manager, fornece validação tipada e OpenAPI, e dá ao workspace uma
base web tipada para os fluxos interativos; as alternativas de servidor HTTP
manual, framework Python com menos contratos e SPA montada manualmente exigiriam
mais infraestrutura própria sem reduzir as fronteiras de autoridade.

## Consequências

FastAPI e Next.js são adaptadores nas seams de transporte e apresentação: não
recebem cálculo financeiro, readiness, inferência semântica nem classificação de
anomalias. A V2 continua local e single-user; a decisão não autoriza SaaS,
autenticação, multitenancy, instalação de dependências na Fase 1 nem mudança da
CLI V1. Versões exatas serão travadas e validadas nas fases de implementação.
