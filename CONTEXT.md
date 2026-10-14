# Financial Manager AI

Vocabulário para gestão e análise financeira empresarial, distinguindo fatos de origem, interpretações financeiras e incertezas.

## Gestão financeira

**Empresa**:
Organização cujos fatos financeiros são objeto da gestão e análise.

**Conta financeira**:
Conta na qual são registrados saldos e movimentos de recursos da empresa.

**Financial Manager**:
Orquestrador das capacidades de gestão e análise financeira disponíveis, responsável por interpretar solicitações e apresentar resultados produzidos pelos módulos especializados.

**Fornecedor**:
Pessoa ou organização à qual a empresa deve uma obrigação de pagamento.

**Obrigação a pagar**:
Compromisso financeiro com um fornecedor, com valor e vencimento. Sua existência não significa que houve pagamento ou saída de caixa.
_Evitar_: despesa ou pagamento como sinônimos.

**Pagamento**:
Liquidação total ou parcial de uma obrigação a pagar. Não equivale ao reconhecimento de uma nova despesa.

**Receita**:
Valor reconhecido como receita segundo a regra financeira adotada pela empresa. Não implica recebimento na mesma data.

**Despesa**:
Valor reconhecido como despesa segundo a regra financeira adotada pela empresa. Não implica pagamento na mesma data.

**Movimento de caixa**:
Entrada ou saída efetiva de recursos de uma conta financeira.
_Evitar_: receita ou despesa como sinônimos.

**Lançamento financeiro**:
Registro de receita ou despesa, associado a uma data de reconhecimento e às classificações disponíveis.

**Saldo pendente**:
Parcela de uma obrigação a pagar que ainda não foi liquidada, considerando os pagamentos e ajustes reconhecidos.

**Categoria financeira**:
Classificação da natureza de uma receita ou despesa.

**Departamento**:
Área organizacional à qual um valor financeiro pode ser atribuído. Não equivale necessariamente a um centro de custo.

**Período financeiro**:
Intervalo usado para delimitar uma análise, segundo o calendário e a regra de datas adotados.

## Planejamento e análise

**Orçamento**:
Conjunto de valores planejados para períodos e dimensões financeiras identificados, pertencente a uma versão definida.

**Realizado**:
Valor observado e agregado segundo uma base financeira explicitada. Pode representar competência ou caixa, que não devem ser combinados silenciosamente.

**Desvio orçamentário**:
Diferença entre realizado e orçado para períodos, dimensões e bases comparáveis. Seu sinal não determina, por si só, se o resultado é favorável.

**Anomalia financeira**:
Observação considerada fora do padrão por um modelo e um critério identificados. Não constitui comprovação de erro ou fraude.

**Triagem estatística de anomalias**:
Avaliação observacional que compara valores a uma política estatística identificada, sem alterar os fatos de origem nem atribuir fraude, erro, suspeita ou probabilidade de ilícito.

**Candidato de triagem (`CANDIDATE`)**:
Registro elegível e avaliado que satisfez a regra estatística identificada; indica somente necessidade potencial de investigação.
_Evitar_: fraude, suspeita, erro, irregularidade, risco.

**Não selecionado (`NOT_SELECTED`)**:
Registro elegível e avaliado que não satisfez a regra estatística identificada.
_Evitar_: normal, seguro, correto, legítimo.

**Não avaliado (`NOT_ASSESSED`)**:
Registro que não pôde participar validamente de uma avaliação estatística identificada; não equivale a resultado negativo nem a ausência de anomalia.

**Previsão de fluxo de caixa**:
Estimativa de entradas, saídas e saldos futuros, associada a uma data de referência e a hipóteses explícitas.

**Cenário**:
Conjunto identificado de hipóteses que modifica uma projeção financeira. Não altera os fatos financeiros observados.

## Informação documental

**Documento financeiro**:
Contrato, relatório, política ou outro documento relevante para a análise financeira, com origem e versão identificáveis.

**Evidência documental**:
Trecho recuperado de um documento financeiro, acompanhado de referência à sua origem. Não equivale automaticamente a um fato financeiro estruturado.

## Origem dos dados

**Dataset em onboarding**:
Fonte tabular local cuja estrutura pode ser perfilada, mas cuja semântica financeira ainda não foi aprovada.
_Evitar_: dataset operacional, fato financeiro aprovado.

**Perfil estrutural de dataset**:
Descrição determinística e versionada da forma, parseabilidade, cobertura e padrões observados de um dataset, sem atribuir significado financeiro às colunas.

**Mapeamento semântico**:
Associação versionada entre uma coluna de origem e um papel de uma ontologia fechada, distinguindo sugestão de significado aprovado.

**Domínio canônico**:
Tipo financeiro aprovado que preserva o significado e o grão próprios de uma fonte, sem convertê-la em uma transação universal.

**Decisão semântica**:
Registro explícito que confirma, corrige ou rejeita uma sugestão de significado, acompanhado da origem da decisão e de uma nova versão do mapeamento.

**Confirmação semântica**:
Decisão semântica que aprova uma associação entre coluna e significado; uma rejeição permanece uma decisão, mas não uma confirmação.

**Readiness semântica**:
Estado que indica se os significados mínimos de um domínio ou capacidade foram aprovados; não implica que exista implementação capaz de executar essa capacidade.

**Readiness de execução**:
Estado que indica se existe um caminho determinístico implementado e validado para executar uma capacidade sobre um dataset semanticamente elegível.

**Readiness dinâmica de anomalia**:
Projeção atual, específica por dataset e operação, de que uma triagem estatística aprovada pode ser executada com os artefatos, valores, moeda e política correntes. Não constitui classificação de registros nem autorização persistente.

**Solicitação dinâmica de anomalia**:
Pedido explícito que identifica exatamente um dataset aprovado e uma operação fechada de triagem estatística, sem escolher medida, algoritmo, limiar ou agrupamento.

**Ativação dinâmica de capacidade**:
Projeção determinística, específica por dataset e reversível, das operações que podem ser executadas no estado corrente do registro, do mapeamento, do vinculador e do adaptador.
_Evitar_: chave global, decisão do LLM, equivalência com toda a capacidade legada.

**Vinculação dinâmica de consulta**:
Associação determinística entre uma operação financeira estruturada, um dataset registrado e um adaptador permitido, sem executar cálculos nem tornar a capacidade globalmente disponível.
_Evitar_: roteamento conversacional, inferência de consulta, ativação de capacidade.

**Solicitação de execução vinculada**:
Pedido somente de dados que registra a identidade e as versões aprovadas usadas para traduzir uma consulta estruturada em uma solicitação aceita pelo adaptador.
_Evitar_: plano executável, SQL, chamada de função escolhida pelo usuário.

**Lote de importação**:
Conjunto identificado de registros recebidos de uma origem em uma importação, associado ao resultado de sua validação.

**Registro contábil Receiver General**:
Registro da fonte Receiver General que pode representar detalhe de voucher ou informação contábil agrupada; a relação exata entre esses tipos permanece não verificada.
_Evitar_: pagamento, despesa ou movimento de caixa como sinônimos.

**Registro de vendas Company Financials**:
Observação de vendas com segmento, país, produto, faixa de desconto, período e medidas fornecidas pela fonte, sem identidade empresarial verificada.
_Evitar_: demonstração financeira de empresa ou histórico de empresa.

**Moeda desconhecida**:
Estado em que a denominação de um valor monetário não foi estabelecida por evidência; símbolos de formatação e países não bastam para atribuí-la.

**Moeda inferida**:
Denominação proposta por uma interpretação com evidência explícita, ainda sem confirmação autoritativa. Não equivale a moeda confirmada.

**Moeda confirmada**:
Denominação estabelecida por evidência autoritativa identificável. A confirmação não altera o valor monetário original.

**Valor monetário original**:
Montante e informação de moeda preservados da observação de origem. Um eventual valor convertido é uma observação derivada distinta.

**Taxa de câmbio**:
Quantidade de moeda de destino correspondente a uma unidade da moeda de origem, para uma data e uma origem de cotação identificadas. A taxa, seu tipo quando informado e sua proveniência não estabelecem a moeda de uma observação financeira desconhecida.

## Interação

**Evidência estruturada**:
Resultado produzido pelas capacidades determinísticas a partir do snapshot aprovado ou de artefatos dinâmicos autenticados; é a fonte autoritativa dos fatos financeiros apresentados.

**Mediação conversacional**:
Interpretação da linguagem do usuário e explicação de evidências estruturadas por um modelo de linguagem, sem autoridade sobre valores, moedas, classificações ou disponibilidade de capacidades.
_Evitar_: agente financeiro autônomo, cálculo pelo LLM.
