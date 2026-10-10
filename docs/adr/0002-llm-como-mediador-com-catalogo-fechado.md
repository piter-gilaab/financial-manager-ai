---
status: accepted
---

# LLM como mediador conversacional com catálogo fechado de pedidos

Na Fase 12, o LLM local interpreta a linguagem do usuário e verbaliza resultados, mas cada proposta sua é uma chave enumerada de um catálogo de pedidos canônicos mantido pelo código, ou a passagem literal do texto do usuário ao roteador determinístico. Nenhum texto produzido pelo modelo chega ao roteamento, à sessão ou ao Financial Manager. A explicação gerada só é exibida após uma verificação determinística de fundamentação (números, moeda, terminologia de triagem e capacidades bloqueadas).

## Alternativas e motivo

Permitir que o modelo reescrevesse o pedido em inglês livre (`normalized_request`) aumentaria a cobertura, por exemplo de filtros em português, mas permitiria que uma tradução errada alterasse silenciosamente medida, filtro ou período. O catálogo fechado restringe o modelo a pedidos já aprovados e torna a validação verificável, ao custo de expressividade.

## Consequências

Pedidos fora do catálogo passam pelo texto literal do usuário e pelas recusas existentes. Falhas do modelo voltam ao comportamento da Fase 11. Ampliar o catálogo é uma mudança de código revisável, não uma capacidade do modelo.
