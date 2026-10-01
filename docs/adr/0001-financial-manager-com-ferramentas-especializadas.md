---
status: accepted
---

# Financial Manager com ferramentas especializadas

O projeto integra seis capacidades que exigem cálculos reproduzíveis, evidências documentais e modelos financeiros separados. A direção da V1, aprovada provisoriamente em 2026-09-16, é um único Financial Manager que interpreta solicitações e chama ferramentas de módulos especializados; o LLM não executa cálculos financeiros diretamente.

## Alternativas e motivo

Uma arquitetura com agentes autônomos por capacidade acrescentaria coordenação e dificultaria a rastreabilidade sem uma necessidade demonstrada. Delegar cálculos ao LLM comprometeria a reprodução dos resultados. As ferramentas concentram as regras determinísticas, a recuperação documental e a execução dos modelos; o orquestrador interpreta pedidos e explica seus resultados.

## Consequências

Resultados numéricos devem vir das ferramentas, evidências documentais do RAG e scores/projeções dos modelos apropriados. A separação de responsabilidades deve permanecer explícita. Contratos, datasets, schema, modelos e provedor de LLM continuam abertos. Este ADR registra a direção aprovada da V1, revisável após a análise dos dados, e não autoriza implementação.
