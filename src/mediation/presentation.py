"""Code-owned localized wording and evidence rendering. The LLM never builds either."""

import re

from . import grounding
from .models import MAX_REFERENCE_LABELS


FALLBACK_NOTICE = ("Natural-language mediation was unavailable for this turn; "
                   "showing the standard response.")
EVIDENCE_STATUSES = ("SUCCESS", "PARTIAL", "NO_DATA")

TEXTS = {
    "en": {
        "capability_required": (
            "Do you want a financial analysis (totals, summaries, breakdowns) or an anomaly "
            "screening (unusual values)? You can answer, for example, “financial analysis” "
            "or “anomalies”."),
        "dataset_required": (
            "Which data should I use: the Receiver General accounting records or the Company "
            "Financials sales records?"),
        "screening_scope_required": (
            "Which values should I screen for unusual entries: Receiver General accounting "
            "amounts, Sales or Profit?"),
        "clarification": "I need a more specific request. Guidance from the system: {message}",
        "evidence_reference": (
            "Which flagged record do you mean? Use one of the labels A1–A{count}, for example "
            "“Why was A1 flagged?”."),
        "no_evidence_reference": (
            "There is no screened result to refer to right now. Please run a screening first, "
            "for example “Are there unusual Profit values?”."),
        "restate": (
            "I can't safely tell what that refers to. Please state the complete request, for "
            "example “total sales by country”."),
        "dataset_selected": "Dataset selected for this local conversation.",
        "dataset_selection_failed": "That dataset is not currently eligible for dynamic financial analysis.",
        "dynamic_dataset": "Select one exact eligible dataset ID before analysis. Available IDs: {choices}",
        "dynamic_mediation_unavailable": (
            "The dynamic request was not executed because safe language mediation was unavailable. "
            "The current dataset selection, if any, was left unchanged."),
        "stale_dynamic_dataset": (
            "The selected dynamic dataset is no longer current or executable. Select an exact "
            "eligible dataset before continuing."),
        "dynamic_anomaly_deferred": (
            "Conversational anomaly screening for onboarded datasets is deferred to Step 68. "
            "No dynamic anomaly screening was executed."),
        "missing_confirmed_profit": (
            "Profit anomaly screening is unavailable because no confirmed supplied Profit "
            "measure is currently ready for this dataset."),
        "missing_confirmed_sales": (
            "Sales anomaly screening is unavailable because no confirmed supplied Sales "
            "measure is currently ready for this dataset."),
        "insufficient_numeric_records": (
            "Anomaly screening is unavailable because the selected measure has too few usable "
            "numeric records for the approved policy."),
        "zero_iqr": (
            "Anomaly screening is unavailable because the approved Tukey-IQR reference has a "
            "zero interquartile range."),
        "incompatible_currency": (
            "Anomaly screening is unavailable because the dataset contains incompatible "
            "confirmed currencies; no conversion was performed."),
        "CASH_FLOW_FORECASTING": (
            "Cash-flow forecasting is not available. The current data has no verified actual "
            "cash inflows or outflows, and its currency is not established; sales records are "
            "not treated as cash. No forecast was produced."),
        "DOCUMENT_RETRIEVAL": (
            "Document questions are not available. There is no approved financial-document "
            "collection, so no invoice, contract or statement can be read or cited."),
        "arbitrary_execution": (
            "I can't run that. Only the registered financial capabilities can be used; SQL, "
            "code, shell commands, tools and file access are not supported."),
        "unverified_claim": (
            "Screening can only point out statistical candidates for review; it cannot "
            "determine fraud, errors or wrongdoing."),
        "unsupported": "I can't run that request. Reason given by the system: {message}",
        "SESSION_EXPIRED": (
            "The previous conversation context has expired. Please state a complete new request."),
        "INVALID_ANSWER": "That answer doesn't match the pending question.",
        "NO_PENDING_CLARIFICATION": "There is no pending question to answer. Please state your request.",
        "UNKNOWN_REFERENCE": "That reference is not valid for the current result.",
        "STALE_REFERENCE": (
            "That reference can no longer be reproduced from the current data. Please run the "
            "screening again."),
        "session_error": "That could not be completed. Please state a complete new request.",
        "replaced": "Starting a new request; the pending question was replaced.",
    },
    "pt-BR": {
        "capability_required": (
            "Você quer uma análise financeira (totais, resumos, agrupamentos) ou uma triagem de "
            "anomalias (valores fora do padrão)? Responda, por exemplo, “análise financeira” "
            "ou “anomalias”."),
        "dataset_required": (
            "Quais dados devo usar: os registros contábeis do Receiver General ou os registros de "
            "vendas da Company Financials?"),
        "screening_scope_required": (
            "Quais valores devo triar em busca de registros fora do padrão: valores contábeis do "
            "Receiver General, vendas ou lucro?"),
        "clarification": "Preciso de um pedido mais específico. Orientação do sistema: {message}",
        "evidence_reference": (
            "Qual registro sinalizado você quer ver? Use um dos rótulos A1–A{count}, por "
            "exemplo “Por que o A1 foi sinalizado?”."),
        "no_evidence_reference": (
            "Não há um resultado de triagem para consultar agora. Faça uma triagem primeiro, por "
            "exemplo “Tem algum lucro fora do padrão?”."),
        "restate": (
            "Não consigo identificar com segurança a que isso se refere. Descreva o pedido "
            "completo, por exemplo “vendas totais por país”."),
        "dataset_selected": "Dataset selecionado para esta conversa local.",
        "dataset_selection_failed": "Esse dataset não está elegível agora para análise financeira dinâmica.",
        "dynamic_dataset": "Selecione um ID exato de dataset elegível antes da análise. IDs disponíveis: {choices}",
        "dynamic_mediation_unavailable": (
            "O pedido dinâmico não foi executado porque a mediação segura de linguagem ficou "
            "indisponível. A seleção atual, se existir, foi preservada."),
        "stale_dynamic_dataset": (
            "O dataset dinâmico selecionado não está mais atual ou executável. Selecione um "
            "dataset elegível por seu ID exato antes de continuar."),
        "dynamic_anomaly_deferred": (
            "A triagem conversacional de anomalias para datasets incorporados foi adiada para o "
            "Step 68. Nenhuma triagem dinâmica foi executada."),
        "missing_confirmed_profit": (
            "A triagem de anomalias de Lucro não está disponível porque nenhuma medida de Lucro "
            "fornecida e confirmada está pronta neste dataset."),
        "missing_confirmed_sales": (
            "A triagem de anomalias de Vendas não está disponível porque nenhuma medida de Vendas "
            "fornecida e confirmada está pronta neste dataset."),
        "insufficient_numeric_records": (
            "A triagem de anomalias não está disponível porque a medida selecionada tem poucos "
            "registros numéricos utilizáveis para a política aprovada."),
        "zero_iqr": (
            "A triagem de anomalias não está disponível porque a referência Tukey-IQR aprovada "
            "tem intervalo interquartil zero."),
        "incompatible_currency": (
            "A triagem de anomalias não está disponível porque o dataset contém moedas confirmadas "
            "incompatíveis; nenhuma conversão foi realizada."),
        "CASH_FLOW_FORECASTING": (
            "Previsão de fluxo de caixa não está disponível. Os dados atuais não têm entradas e "
            "saídas de caixa efetivas verificadas, e a moeda não está estabelecida; registros de "
            "vendas não são tratados como caixa. Nenhuma previsão foi produzida."),
        "DOCUMENT_RETRIEVAL": (
            "Perguntas sobre documentos não estão disponíveis. Não há um acervo aprovado de "
            "documentos financeiros, então nenhuma fatura, contrato ou extrato pode ser lido ou "
            "citado."),
        "arbitrary_execution": (
            "Não posso executar isso. Só as capacidades financeiras registradas podem ser usadas; "
            "SQL, código, comandos de shell, ferramentas e acesso a arquivos não são suportados."),
        "unverified_claim": (
            "A triagem só aponta candidatos estatísticos para revisão; ela não determina fraude, "
            "erros ou irregularidades."),
        "unsupported": "Não posso executar esse pedido. Motivo informado pelo sistema: {message}",
        "SESSION_EXPIRED": (
            "O contexto anterior da conversa expirou. Descreva um novo pedido completo."),
        "INVALID_ANSWER": "Essa resposta não corresponde à pergunta pendente.",
        "NO_PENDING_CLARIFICATION": "Não há pergunta pendente. Descreva seu pedido.",
        "UNKNOWN_REFERENCE": "Essa referência não é válida para o resultado atual.",
        "STALE_REFERENCE": (
            "Essa referência não pode mais ser reproduzida a partir dos dados atuais. Faça a "
            "triagem novamente."),
        "session_error": "Não foi possível concluir. Descreva um novo pedido completo.",
        "replaced": "Iniciando um novo pedido; a pergunta pendente foi substituída.",
    },
}


def text(language, key, **values):
    return TEXTS[language][key].format(**values)


def _first_error(result):
    for group in result.get("errors") or ():
        for item in group.get("items") or ():
            return item
    for step in result.get("results") or ():
        for item in step["response"].get("errors") or ():
            return item
    return {}


def _clarification_code(result):
    routing = result["routing"]
    if routing["status"] == "CLARIFICATION_REQUIRED":
        return routing["reason_code"], routing["message"]
    clarification = result.get("clarification") or {}
    return clarification.get("code"), clarification.get("question") or ""


def bears_evidence(outcome):
    """True when a single authoritative result exists that may be verbalized."""
    result = outcome.get("result")
    if outcome.get("operation") in {"dynamic_financial_analysis", "dynamic_anomaly_screen"}:
        return (outcome.get("status") in EVIDENCE_STATUSES and type(result) is dict
                and type(result.get("delegated_result")) is dict)
    if outcome["operation"] == "follow_up":
        return outcome["status"] == "SUCCESS" and type(result) is dict
    return (type(result) is dict and result.get("execution_status") in EVIDENCE_STATUSES
            and len(result.get("results") or ()) == 1)


def outcome_text(outcome, language):
    """Deterministic wording for outcomes without evidence to explain."""
    result = outcome.get("result")
    status = outcome["status"]
    if outcome.get("operation") in {"dynamic_financial_analysis", "dynamic_anomaly_screen"}:
        error = outcome.get("error") or {}
        if type(result) is dict:
            errors = result.get("errors") or []
            error = errors[0] if errors else error
        code = error.get("code")
        if (outcome.get("operation") == "dynamic_anomaly_screen"
                and code in TEXTS[language]):
            return text(language, code)
        return text(language, "unsupported", message=error.get("message") or status)
    if type(result) is not dict or "routing" not in result:
        return text(language, status if status in TEXTS[language] else "session_error")
    if status == "CLARIFICATION_REQUIRED":
        code, message = _clarification_code(result)
        if code in ("capability_required", "dataset_required", "screening_scope_required"):
            return text(language, code)
        return text(language, "clarification", message=message)
    if status == "CAPABILITY_UNAVAILABLE":
        capability = result["routing"]["steps"][0]["capability"]["identifier"]
        return text(language, capability)
    error = _first_error(result)
    if error.get("code") in ("arbitrary_execution", "unverified_claim"):
        return text(language, error["code"])
    return text(language, "unsupported", message=error.get("message") or status)


# ---------------------------------------------------------------------------
# Structured presentation: every value below is read from authoritative evidence.

TABLE_ROW_LIMIT = 15
LABEL_WIDTH = 40
LABELS = {
    "en": {
        "records": "Records", "ref": "Ref", "row": "Source row", "value": "Value",
        "global": "Global", "peer": "Peer", "rank": "Rank", "amount": "Amount",
        "effective_date": "Effective date", "debit_credit": "DR/CR", "voucher_type": "Voucher type",
        "department": "Department", "total": "total", "count": "records with a value",
        "sum": "total", "mean": "average", "median": "median", "min": "minimum", "max": "maximum",
        "negative_count": "Negative Profit records", "zero_count": "Zero Profit records",
        "positive_count": "Positive Profit records", "record_count": "Records",
        "unresolved_placeholder_count": "Unresolved placeholders",
        "omitted": "… {count} more rows not shown.",
        "missing_group": "(value missing in source)",
        "peer_group": "Peer group", "observed": "Observed {measure}",
        "assessment": "{mode} assessment", "fences": "fences {lower} to {upper}",
        "reference": "Q1 {q1}, Q3 {q3}, IQR {iqr}; {size} numeric records",
        "not_assessed": "not assessed: {reason}",
        "screening_summary": ("Global screening: {g_c} CANDIDATE, {g_n} NOT_SELECTED, {g_a} NOT_ASSESSED. "
                              "Peer screening: {p_c} CANDIDATE, {p_n} NOT_SELECTED, {p_a} NOT_ASSESSED."),
        "candidates_shown": "Showing {shown} of {total} records flagged CANDIDATE by at least one assessment.",
        "notes": "Notes:",
        "currency": ("Currency: UNKNOWN. The source denomination is not established, so values are "
                     "not labelled with any currency."),
        "currency_confirmed": "Currency: CONFIRMED ({code}), copied from approved dataset evidence.",
        "coverage": "Coverage: {used} of {candidates} records used; {excluded} excluded ({reasons}).",
        "missing_dimension": ("{count} records have no {grouping} value in the source; they appear as "
                              "“(value missing in source)”."),
        "candidate": ("CANDIDATE = statistical screening candidate for review; it is not fraud, an error, "
                      "misconduct, a certainty or a probability."),
        "not_assessed_note": "NOT_ASSESSED = the stated screening assessment could not be performed for that record.",
        "disclosures": "Source disclosures apply: {fields}.",
        "follow_hint": "Ask, for example, “Why was A1 flagged?” or “Tell me more about A2.”.",
        "interpreted": "Interpreted request: “{request}”. Complete evidence: python -m src.cli ask \"{request}\" --full",
        "reference_line": ("Evidence reference {label}, re-resolved against a fresh, same-snapshot screening "
                           "({intent})."),
        "labels": "Natural follow-up labels for these references:",
    },
    "pt-BR": {
        "records": "Registros", "ref": "Ref", "row": "Linha", "value": "Valor",
        "global": "Global", "peer": "Pares", "rank": "Posição", "amount": "Valor",
        "effective_date": "Data efetiva", "debit_credit": "D/C", "voucher_type": "Tipo de voucher",
        "department": "Departamento", "total": "total", "count": "registros com valor",
        "sum": "total", "mean": "média", "median": "mediana", "min": "mínimo", "max": "máximo",
        "negative_count": "Registros com lucro negativo", "zero_count": "Registros com lucro zero",
        "positive_count": "Registros com lucro positivo", "record_count": "Registros",
        "unresolved_placeholder_count": "Marcadores não resolvidos",
        "omitted": "… mais {count} linhas não exibidas.",
        "missing_group": "(valor ausente na fonte)",
        "peer_group": "Grupo de pares", "observed": "{measure} observado",
        "assessment": "Avaliação {mode}", "fences": "limites {lower} a {upper}",
        "reference": "Q1 {q1}, Q3 {q3}, IQR {iqr}; {size} registros numéricos",
        "not_assessed": "não avaliado: {reason}",
        "screening_summary": ("Triagem global: {g_c} CANDIDATE, {g_n} NOT_SELECTED, {g_a} NOT_ASSESSED. "
                              "Triagem por pares: {p_c} CANDIDATE, {p_n} NOT_SELECTED, {p_a} NOT_ASSESSED."),
        "candidates_shown": ("Exibindo {shown} de {total} registros marcados como CANDIDATE por pelo menos "
                             "uma avaliação."),
        "notes": "Notas:",
        "currency": ("Moeda: UNKNOWN. A denominação da fonte não está estabelecida; os valores não são "
                     "atribuídos a nenhuma moeda."),
        "currency_confirmed": "Moeda: CONFIRMED ({code}), copiada da evidência aprovada do dataset.",
        "coverage": "Cobertura: {used} de {candidates} registros usados; {excluded} excluídos ({reasons}).",
        "missing_dimension": ("{count} registros não têm valor de {grouping} na fonte; aparecem como "
                              "“(valor ausente na fonte)”."),
        "candidate": ("CANDIDATE = candidato estatístico para revisão; não é fraude, erro, má conduta, "
                      "certeza nem probabilidade."),
        "not_assessed_note": "NOT_ASSESSED = a avaliação indicada não pôde ser realizada para aquele registro.",
        "disclosures": "Ressalvas da fonte: {fields}.",
        "follow_hint": "Pergunte, por exemplo, “Por que o A1 foi sinalizado?” ou “Me fala mais sobre o A2.”.",
        "interpreted": ("Pedido interpretado: “{request}”. Evidência completa: "
                        "python -m src.cli ask \"{request}\" --full"),
        "reference_line": ("Referência {label}, reconstruída a partir de uma nova triagem sobre o mesmo "
                           "snapshot ({intent})."),
        "labels": "Rótulos para perguntas de acompanhamento sobre estas referências:",
    },
}
NAMES = {
    "en": {"sales": "Sales", "profit": "Profit", "discounts": "Discounts", "gross_sales": "Gross sales",
           "cogs": "COGS", "accounting_amount": "Accounting amount", "units_sold": "Units sold",
           "country": "Country", "segment": "Segment", "product": "Product", "period": "Period",
           "debit_credit": "Debit/credit", "voucher_type": "Voucher type", "department": "Department",
           "discount_band": "Discount band", "general_ledger_account": "General ledger account",
           "subledger_account": "Subledger account", "financial_coding_block": "Financial coding block",
           "control_data_type": "Control data type", "global": "Global", "peer": "Peer"},
    "pt-BR": {"sales": "Vendas", "profit": "Lucro", "discounts": "Descontos", "gross_sales": "Vendas brutas",
              "cogs": "CPV", "accounting_amount": "Valor contábil", "units_sold": "Unidades vendidas",
              "country": "País", "segment": "Segmento", "product": "Produto", "period": "Período",
              "debit_credit": "Débito/crédito", "voucher_type": "Tipo de voucher", "department": "Departamento",
              "discount_band": "Faixa de desconto", "general_ledger_account": "Conta contábil",
              "subledger_account": "Subconta", "financial_coding_block": "Bloco de codificação",
              "control_data_type": "Tipo de dado de controle", "global": "global", "peer": "por pares"},
}
QUIET_WARNINGS = ("currency_unknown", "descriptive_screening", "assessment_unavailable")
TERMS = {
    "en": {"entity_scope": "no verified company identity", "provenance": "provenance unresolved",
           "record_granularity": "record grain unresolved", "profit": "Profit sign convention",
           "units_sold": "quantity semantics", "unresolved_placeholder": "unresolved placeholder",
           "source_missing": "missing in source", "why_selected": "why it was selected",
           "record_detail": "record detail"},
    "pt-BR": {"entity_scope": "sem identidade de empresa verificada",
              "provenance": "proveniência não resolvida",
              "record_granularity": "granularidade dos registros não resolvida",
              "profit": "convenção de sinal do lucro", "units_sold": "semântica de quantidade",
              "unresolved_placeholder": "marcador não resolvido", "source_missing": "ausente na fonte",
              "why_selected": "motivo da seleção", "record_detail": "detalhe do registro"},
}


def term(language, key):
    return TERMS[language].get(key, key.replace("_", " "))


def _reason(language, reason):
    """'measure:profit:unresolved_placeholder' -> 'unresolved placeholder (Profit)'."""
    parts = reason.split(":")
    if len(parts) == 3:
        return f"{term(language, parts[2])} ({name(language, parts[1])})"
    return term(language, reason)


def label(language, key, **values):
    return LABELS[language][key].format(**values)


def name(language, key):
    return NAMES[language].get(key, key.replace("_", " "))


def grouped(value, language):
    """Locale digit grouping by string manipulation only; the exact digits are unchanged."""
    match = re.fullmatch(r"(-?)(\d+)(?:\.(\d+))?", str(value)) if value is not None else None
    if match is None:
        return "—" if value is None else str(value)
    sign, whole, fraction = match.groups()
    thousands, decimal = (",", ".") if language == "en" else (".", ",")
    parts = []
    while whole:
        parts.insert(0, whole[-3:])
        whole = whole[:-3]
    return sign + thousands.join(parts) + ("" if fraction is None else decimal + fraction)


def _cell(value):
    text = str(value)
    return text if len(text) <= LABEL_WIDTH else text[:LABEL_WIDTH - 1] + "…"


def _table(headers, rows, numeric):
    cells = [[_cell(value) for value in row] for row in rows]
    widths = [max([len(headers[i])] + [len(row[i]) for row in cells]) for i in range(len(headers))]

    def line(values):
        return "  ".join(value.rjust(widths[i]) if i in numeric else value.ljust(widths[i])
                         for i, value in enumerate(values)).rstrip()

    return "\n".join([line(headers), "-" * len(line(["-" * width for width in widths])),
                      *(line(row) for row in cells)])


def _limit(rows, language):
    shown = rows[:TABLE_ROW_LIMIT]
    omitted = len(rows) - len(shown)
    return shown, ([label(language, "omitted", count=omitted)] if omitted else [])


TAILS = {"en": {"upper": "upper", "lower": "lower"}, "pt-BR": {"upper": "superior", "lower": "inferior"}}


def _assessment_cell(assessment, language):
    tail = assessment.get("tail")
    return assessment["status"] + (f" ({TAILS[language][tail]})" if tail else "")


def _groups(view, hint, language):
    groups = grounding.ordered_groups(view)
    measures = list(groups[0]["measures"]) if groups else []
    stats = [(measure, statistic) for measure in measures
             for statistic in ("sum", "mean", "min", "max") if statistic in groups[0]["measures"][measure]]
    rows = []
    for group in groups:
        key = group["key"]
        title = label(language, "missing_group") if key.get("value") is None else key["value"]
        rows.append([title] + [grouped(group["measures"][m].get(s), language) for m, s in stats]
                    + [grouped(group.get("record_count"), language)])
    shown, omitted = _limit(rows, language)
    headers = ([name(language, view.grouping or "group")]
               + [f"{name(language, m)} ({label(language, s)})" for m, s in stats]
               + [label(language, "records")])
    if hint == "TABLE":
        return [_table(headers, shown, set(range(1, len(headers)))), *omitted]
    return [f"- {row[0]}: " + "; ".join(f"{headers[i]} {row[i]}" for i in range(1, len(row)))
            for row in shown] + omitted


def _records(view, language):
    rows = []
    for item in view.evidence["result"]["items"]:
        rows.append([str(item["rank"]), grouped(grounding.record_amount(item), language), item.get("effective_date") or "—",
                     item.get("debit_credit") or "—", item.get("voucher_type") or "—",
                     item.get("department") or "—", str(item["source_row_number"])])
    headers = [label(language, key) for key in ("rank", "amount", "effective_date", "debit_credit",
                                                 "voucher_type", "department", "row")]
    shown, omitted = _limit(rows, language)
    return [_table(headers, shown, {0, 1, 6}), *omitted]


def _summary(view, language):
    body = view.evidence["result"]
    lines = []
    for measure, facts in body["measures"].items():
        for statistic in ("sum", "mean", "median", "min", "max", "count"):
            if statistic in facts:
                lines.append(f"- {name(language, measure)} — {label(language, statistic)}: "
                             f"{grouped(facts[statistic], language)}")
    for field in ("record_count", "negative_count", "zero_count", "positive_count",
                  "unresolved_placeholder_count"):
        if body.get(field) is not None:
            lines.append(f"- {label(language, field)}: {grouped(body[field], language)}")
    return lines


def _screening(view, hint, language, labels):
    evidence = view.evidence
    candidates = grounding.screening_candidates(evidence)
    refs = list(labels) if labels else ["—"] * min(len(candidates), MAX_REFERENCE_LABELS)
    rows = [[ref, str(item["lineage"]["source_row_number"]), grouped(item.get("observed_value"), language),
             _assessment_cell(item["assessments"]["global"], language),
             _assessment_cell(item["assessments"]["peer"], language)]
            for ref, item in zip(refs, candidates)]
    summary = evidence["result"]["summary"]
    lines = [label(language, "screening_summary",
                   **{f"{mode[0]}_{key[0]}": grouped(summary[mode][status], language)
                      for mode in ("global", "peer")
                      for key, status in (("c", "candidate"), ("n", "not_selected"), ("a", "not_assessed"))})]
    if not rows:
        return lines
    headers = [label(language, key) for key in ("ref", "row", "value", "global", "peer")]
    if hint == "TABLE":
        lines.append(_table(headers, rows, {1, 2}))
    elif hint == "LIST":
        lines.extend(f"- {row[0]}: {headers[1]} {row[1]}; {headers[2]} {row[2]}; "
                     f"{headers[3]} {row[3]}; {headers[4]} {row[4]}" for row in rows)
    lines.append(label(language, "candidates_shown", shown=len(rows), total=len(candidates)))
    return lines


def _dynamic_screening(view, hint, language, labels):
    evidence = view.evidence
    candidates = grounding.dynamic_screening_candidates(evidence)
    refs = list(labels) if labels else ["—"] * min(len(candidates), MAX_REFERENCE_LABELS)
    rows = [[
        ref, str(item["source_row_number"]), grouped(item.get("observed_value"), language),
        _assessment_cell(item, language),
    ] for ref, item in zip(refs, candidates)]
    counts = evidence["result"]["counts"]
    lines = [(
        f"Global screening: {grouped(counts['candidate'], language)} CANDIDATE, "
        f"{grouped(counts['not_selected'], language)} NOT_SELECTED, "
        f"{grouped(counts['not_assessed'], language)} NOT_ASSESSED."
        if language == "en" else
        f"Triagem global: {grouped(counts['candidate'], language)} CANDIDATE, "
        f"{grouped(counts['not_selected'], language)} NOT_SELECTED, "
        f"{grouped(counts['not_assessed'], language)} NOT_ASSESSED."
    )]
    if not rows:
        return lines
    headers = [label(language, key) for key in ("ref", "row", "value", "global")]
    if hint == "TABLE":
        lines.append(_table(headers, rows, {1, 2}))
    elif hint == "LIST":
        lines.extend(
            f"- {row[0]}: {headers[1]} {row[1]}; {headers[2]} {row[2]}; "
            f"{headers[3]} {row[3]}" for row in rows
        )
    lines.append(label(language, "candidates_shown", shown=len(rows), total=counts["candidate"]))
    return lines


def _followup(view, language):
    detail = view.detail
    peers = "; ".join(f"{name(language, key)} {value.get('value') if type(value) is dict else value}"
                      for key, value in (detail.get("peer_values") or {}).items())
    lines = [f"- {label(language, 'row')}: {detail['lineage']['source_row_number']}",
             f"- {label(language, 'observed', measure=name(language, detail['measure']))}: "
             f"{grouped(detail.get('observed_value'), language)}"]
    if peers:
        lines.append(f"- {label(language, 'peer_group')}: {peers}")
    for mode, entry in detail["assessments"].items():
        assessment, reference = entry["assessment"], entry.get("reference") or {}
        heading = label(language, "assessment", mode=name(language, mode))
        if assessment["status"] == "NOT_ASSESSED":
            lines.append(f"- {heading}: NOT_ASSESSED — "
                         + label(language, "not_assessed", reason=_reason(language, assessment.get("reason") or "")))
            continue
        lines.append(f"- {heading}: {_assessment_cell(assessment, language)} — "
                     + label(language, "fences", lower=grouped(reference.get("lower_fence"), language),
                             upper=grouped(reference.get("upper_fence"), language))
                     + " (" + label(language, "reference", q1=grouped(reference.get("q1"), language),
                                    q3=grouped(reference.get("q3"), language),
                                    iqr=grouped(reference.get("iqr"), language),
                                    size=grouped(reference.get("numeric_size"), language)) + ")")
    return lines


def structured(view, hint, language, labels=()):
    if hint == "TEXT":
        return []
    if view.kind == "groups":
        return _groups(view, hint, language)
    if view.kind == "records":
        return _records(view, language)
    if view.kind == "summary":
        return _summary(view, language)
    if view.kind == "screening":
        return _screening(view, hint, language, labels)
    if view.kind == "dynamic_screening":
        return _dynamic_screening(view, hint, language, labels)
    if view.kind == "followup":
        return _followup(view, language)
    return []


def notes(view, language, labels=()):
    """Required disclosures, rendered deterministically whatever the model wrote."""
    evidence = view.evidence
    lines = []
    if grounding.currency_status(view) == "UNKNOWN":
        lines.append(label(language, "currency"))
    elif grounding.currency_status(view) == "CONFIRMED":
        currency = view.evidence.get("currency") or {}
        code = currency.get("code")
        if type(code) is str and code:
            lines.append(label(language, "currency_confirmed", code=code))
    records = evidence.get("records") or {}
    if records.get("excluded"):
        reasons = ", ".join(f"{_reason(language, reason)}: {count}"
                            for reason, count in (records.get("exclusion_reasons") or {}).items())
        lines.append(label(language, "coverage", used=grouped(records.get("used"), language),
                           candidates=grouped(records.get("candidates"), language),
                           excluded=grouped(records["excluded"], language), reasons=reasons))
    if view.kind == "groups":
        missing = (evidence["result"].get("dimension_coverage") or {}).get("unavailable")
        if missing:
            lines.append(label(language, "missing_dimension", count=grouped(missing, language),
                               grouping=name(language, view.grouping or "group").casefold()))
    if view.kind in ("screening", "dynamic_screening", "followup"):
        lines.append(label(language, "candidate"))
        lines.append(label(language, "not_assessed_note"))
    fields = []
    for warning in grounding.quality_warnings(view):
        code, raw_field = warning.get("code"), warning.get("field") or "dataset"
        field = (term(language, raw_field) if code == "source_semantics_unresolved"
                 else f"{term(language, code)} ({name(language, raw_field)})")
        if code not in QUIET_WARNINGS and field not in fields:
            fields.append(field)
    if fields:
        lines.append(label(language, "disclosures", fields=", ".join(fields)))
    if view.kind in ("screening", "dynamic_screening") and labels:
        lines.append(label(language, "follow_hint"))
    return lines


def compose(view, message, language, *, hint, labels=(), interpreted=None, reference=None):
    """Validated prose + evidence-rendered structure + mandatory notes."""
    parts = [message]
    body = structured(view, hint, language, labels)
    if body:
        parts.append("\n".join(body))
    footer = [label(language, "notes"), *("- " + line for line in notes(view, language, labels))]
    if reference is not None:
        footer.append(label(language, "reference_line", label=reference[0],
                            intent=term(language, reference[1])))
    elif interpreted:
        footer.append(label(language, "interpreted", request=interpreted))
    parts.append("\n".join(footer))
    return "\n\n".join(parts)


def deterministic_dynamic(view, language):
    """Code-rendered fallback for dynamic evidence; every displayed value is copied."""
    anomaly = view.kind == "dynamic_screening"
    message = (
        ("Dynamic anomaly screening completed from authoritative evidence."
         if anomaly else "Dynamic financial analysis completed from authoritative evidence.")
        if language == "en" else
        ("A triagem dinâmica de anomalias foi concluída com evidência autoritativa."
         if anomaly else "A análise financeira dinâmica foi concluída com evidência autoritativa.")
    )
    if view.kind == "count":
        value = grouped(view.evidence["result"]["record_count"], language)
        body = f"- {label(language, 'record_count')}: {value}"
        footer = [label(language, "notes"), *(
            "- " + line for line in notes(view, language)
        )]
        return "\n\n".join((message, body, "\n".join(footer)))
    return compose(view, message, language, hint=PRESENTATION_DEFAULTS[view.kind])


PRESENTATION_DEFAULTS = {
    "summary": "LIST", "groups": "TABLE", "records": "TABLE",
    "screening": "TABLE", "followup": "LIST",
    "dynamic_screening": "TABLE",
}
