# Orientação da V1

> Registro histórico de planejamento (2026-09-16). As hipóteses de empresa única,
> moeda BRL e seis capacidades não descrevem os datasets nem o registro atual da V1.
> Consulte o [guia técnico](../financial_manager_ai_guide.md) para o estado validado.
> Este documento continua sem autorizar novas implementações.

Atualizado em 2026-09-16. Este documento registra direção e pendências, não é uma especificação final nem autorização para implementação.

## Objetivo e capacidades

Gestão e análise financeira empresarial via CLI, coordenadas pelo Financial Manager:

1. Accounts Payable: obrigações, vencimentos, fornecedores e atrasos.
2. Financial Data Analysis: receitas, despesas, categorias, departamentos, períodos e consultas em linguagem natural.
3. Budget Variance: comparação de orçado e realizado e identificação dos principais desvios.
4. Financial Document RAG: consulta de contratos, relatórios e políticas com evidências documentais.
5. Financial Anomaly Detection: identificação de observações fora do padrão usando ML separado do LLM.
6. Cash Flow Forecast: previsão de caixa e análise de cenários.

## Escolhas aprovadas provisoriamente pelo usuário

- Python.
- SQLite como persistência local inicial.
- Pandas para EDA e transformação.
- Uma única empresa.
- Moeda BRL.
- Accounts Payable inicialmente somente para consulta, sem execução de pagamentos nem operações de gestão de obrigações pelo orquestrador.
- Um único Financial Manager/orquestrador com ferramentas especializadas, sem arquitetura multiagente.

São escolhas revisáveis após a análise dos dados; não exigem instalação ou criação de código agora. Rastreabilidade entre dados importados, obrigações e pagamentos ainda precisa ser especificada.

## Princípios estabelecidos

O LLM interpreta e explica; ferramentas fazem cálculos e consultas. RAG recupera informações documentais e modelos de ML ficam separados do LLM. A preparação dos dados antecede a operação. O desenho deve permitir evolução para PostgreSQL e SaaS sem construir essas fases antecipadamente.

## Decisões abertas

- Datasets, origens, formatos, acesso, sensibilidade, cobertura histórica e qualidade.
- Schema final, identificadores, deduplicação e relações entre lançamentos, obrigações, pagamentos e movimentos de caixa.
- Base de reconhecimento por análise, calendário, datas, sinais, precisão e arredondamento monetário.
- Granularidade, versões e dimensões do orçamento, incluindo interpretação dos desvios.
- Modelo de anomalias, atributos, população comparável, critérios e avaliação.
- Forecast: horizonte, frequência, saldo inicial, compromissos e recebimentos conhecidos, método, cenários e avaliação temporal.
- Documentos/RAG: corpus, formatos, OCR, versões, recuperação, indexação e avaliação.
- Provedor e modelo de LLM, privacidade, custo e permissões de envio de dados.
- Contratos finais das ferramentas e critérios de aceitação de cada capacidade.

Não estão aprovados algoritmo específico de ML, banco vetorial, biblioteca de orquestração, SQL gerado livremente nem schemas sugeridos anteriormente.

## Próxima decisão de projeto

Escolher quais fontes e amostras de dados serão usadas para avaliar a viabilidade da V1, com suas condições de acesso e uso. Primeiro faça o inventário: conteúdo, dicionário de campos, período, volume, granularidade, identificadores e restrições de privacidade.

Depois de autorizado, o diagnóstico/EDA deve verificar duplicidades, ausências, consistência de valores e datas, ligação entre registros e cobertura necessária às seis capacidades. Esse resultado orientará schema e escopo; não presuma que histórico de receitas e despesas basta para prever saldo de caixa.

## Ponto de parada

A autorização atual abrange configuração das skills e documentação local. Não iniciar implementação, scaffolding, dependências, migrações ou publicação de issues. Apresentar os arquivos alterados e aguardar a próxima orientação do usuário.
