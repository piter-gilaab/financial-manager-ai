# Documentação de domínio

## Leitura antes de explorar ou planejar

1. Leia `CONTEXT.md` para o vocabulário do domínio.
2. Leia os ADRs relevantes em `docs/adr/`.
3. Leia `docs/planning/v1-direction.md` para o estado das decisões e a autorização atual.

Se algum documento não existir, prossiga com as informações disponíveis. Crie documentos quando houver conteúdo concreto; não crie arquivos vazios para preencher uma estrutura.

## Organização

O projeto usa um contexto documental único, com `CONTEXT.md` e `docs/adr/` na raiz. Isso não impede módulos com responsabilidades distintas e não exige monorepo nem múltiplos contextos documentais.

## Glossário

Use os termos definidos em `CONTEXT.md` nas discussões, especificações e issues. O arquivo contém apenas conceitos de domínio, sem schemas, stack, planos ou decisões de implementação. Esclareça termos ambíguos antes de acrescentar definições.

## ADRs

Crie um ADR somente quando a decisão for custosa de reverter, precisar de contexto para ser entendida e resultar de alternativas reais. Use numeração sequencial e o formato da skill `domain-modeling`; explicite status provisório quando necessário. Se uma proposta contrariar um ADR, indique o conflito e discuta sua revisão.

## Decisões abertas

Mantenha hipóteses e decisões pendentes na orientação de planejamento. Não transforme escolhas de datasets, schema, modelos, RAG ou provedor de LLM em decisões aceitas antes da análise dos dados e da aprovação correspondente.
