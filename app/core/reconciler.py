# app/core/reconciler.py
"""
Motor de conciliação financeira.

Este é o coração da aplicação. Aqui acontece a comparação real entre
as duas planilhas.

─── ALGORITMO DE CONCILIAÇÃO ────────────────────────────────────────────────

O problema central: como comparar registros que não têm um ID único comum?

ABORDAGEM ESCOLHIDA: "Contagem de ocorrências por chave composta"

1. Criamos uma CHAVE COMPOSTA: (nome_conta, valor_debito_arredondado)
   - Conta sozinha não é suficiente (múltiplas linhas por conta)
   - Valor sozinho não é suficiente (mesmo valor em contas diferentes)
   - Juntos, formam um identificador mais robusto

2. Contamos quantas vezes cada chave aparece em cada planilha
   - Se cliente tem 3x (ContaX, 100.00) e empresa tem 3x → 3 conciliados
   - Se cliente tem 2x e empresa tem 3x → 2 conciliados + 1 ausente no cliente

3. Comparamos as contagens para identificar:
   - Mínimo(qtd_cliente, qtd_empresa) → conciliados
   - Excesso no cliente → ausentes na empresa
   - Excesso na empresa → ausentes no cliente

4. Registros que existem só em um lado → ausentes

5. Duplicidades: chaves que aparecem mais de uma vez no mesmo lado

POR QUE NÃO USAR MERGE DIRETO?
- Um merge simples (pd.merge) une registros 1:1 pela posição
- Com duplicatas, isso gera combinações cartesianas incorretas
- Ex: 2 linhas idênticas no cliente × 2 na empresa = 4 pares (errado)
─────────────────────────────────────────────────────────────────────────────
"""

from __future__ import annotations

import logging

import numpy as np
import pandas as pd

from config.settings import (
    CLIENT_ACCOUNT_COL, CLIENT_DEBIT_COL,
    COMPANY_ACCOUNT_COL, COMPANY_DEBIT_COL,
    NUMERIC_TOLERANCE,
)
from app.core.models import ReconciliationResult

logger = logging.getLogger(__name__)

# Nomes internos das colunas-chave (padronizados após renomeação)
_KEY_ACCOUNT = "_key_account"
_KEY_DEBIT = "_key_debit"
_KEY_COMPOSITE = "_key_composite"
_COUNT_CLIENT = "_count_client"
_COUNT_COMPANY = "_count_company"


def reconcile(
    client_df: pd.DataFrame,
    company_df: pd.DataFrame,
) -> ReconciliationResult:
    """
    Ponto de entrada principal da conciliação.
    
    Args:
        client_df: DataFrame limpo e filtrado do cliente
        company_df: DataFrame limpo e filtrado da empresa
    
    Returns:
        ReconciliationResult com todos os DataFrames classificados
    """
    result = ReconciliationResult(
        total_client_records=len(client_df),
        total_company_records=len(company_df),
    )

    if client_df.empty and company_df.empty:
        result.processing_errors.append("Ambas as planilhas estão vazias após filtragem.")
        return result

    # PASSO 1: Padronizar as colunas-chave para um nome comum
    client_keyed = _add_keys(client_df, CLIENT_ACCOUNT_COL, CLIENT_DEBIT_COL)
    company_keyed = _add_keys(company_df, COMPANY_ACCOUNT_COL, COMPANY_DEBIT_COL)

    # PASSO 2: Detectar duplicidades dentro de cada planilha
    result.duplicates = _find_duplicates(client_keyed, company_keyed)

    # PASSO 3: Calcular contagens por chave composta
    client_counts = _count_keys(client_keyed, source="client")
    company_counts = _count_keys(company_keyed, source="company")

    # PASSO 4: Unir as contagens e classificar cada chave
    merged_counts = _merge_counts(client_counts, company_counts)

    # PASSO 5: Separar por categoria
    conciliated_keys, divergent_keys, missing_client_keys, missing_company_keys = (
        _split_by_category(merged_counts)
    )

    # PASSO 6: Montar os DataFrames de saída recuperando os dados originais
    result.conciliated = _build_output(
        client_keyed, company_keyed, conciliated_keys, "conciliado"
    )
    result.divergent = _build_divergent_output(
        client_keyed, company_keyed, divergent_keys
    )
    result.missing_in_client = _select_records(company_keyed, missing_client_keys)
    result.missing_in_company = _select_records(client_keyed, missing_company_keys)

    _log_summary(result)
    return result


# ── Funções internas ────────────────────────────────────────────────────────────

def _add_keys(df: pd.DataFrame, account_col: str, debit_col: str) -> pd.DataFrame:
    """
    Adiciona colunas de chave ao DataFrame.
    
    Chave composta = conta + débito arredondado
    O arredondamento é crucial: evita que 100.001 e 100.000 sejam tratados
    como valores diferentes por erro de ponto flutuante.
    """
    df = df.copy()
    df[_KEY_ACCOUNT] = df[account_col].fillna("").str.upper().str.strip()
    df[_KEY_DEBIT] = (
        pd.to_numeric(df[debit_col], errors="coerce")
        .fillna(0.0)
        .round(2)  # arredonda para 2 casas — padrão monetário
    )
    # Chave composta como string: mais fácil de usar como índice de dicionário
    df[_KEY_COMPOSITE] = df[_KEY_ACCOUNT] + "||" + df[_KEY_DEBIT].astype(str)
    return df


def _count_keys(df: pd.DataFrame, source: str) -> pd.Series:
    """
    Conta quantas vezes cada chave composta aparece no DataFrame.
    
    Returns:
        Series com chave composta como índice e contagem como valor
    """
    counts = df[_KEY_COMPOSITE].value_counts()
    logger.debug(f"{source}: {len(counts)} chaves únicas")
    return counts


def _merge_counts(
    client_counts: pd.Series, company_counts: pd.Series
) -> pd.DataFrame:
    """
    Une as contagens do cliente e da empresa em um único DataFrame.
    
    outer join: preserva chaves que existem em apenas um dos lados
    fillna(0): chave ausente em um lado = 0 ocorrências
    """
    merged = pd.DataFrame({
        _COUNT_CLIENT: client_counts,
        _COUNT_COMPANY: company_counts,
    }).fillna(0).astype(int)
    return merged


def _split_by_category(
    merged: pd.DataFrame,
) -> tuple[pd.Index, pd.Index, pd.Index, pd.Index]:
    """
    Classifica cada chave composta em uma das 4 categorias.
    
    Lógica:
    - Existe nos dois lados: pode ser conciliado ou divergente
      - Conciliado: contagens iguais OU sobreposição >= 1
      - Divergente: contagens diferentes (mais de um lado do que do outro)
        OBS: divergência aqui = QUANTIDADE diferente de lançamentos,
             não o valor em si (o valor já está na chave)
    - Existe só no cliente: ausente na empresa
    - Existe só na empresa: ausente no cliente
    """
    both_sides = merged[
        (merged[_COUNT_CLIENT] > 0) & (merged[_COUNT_COMPANY] > 0)
    ]
    only_client = merged[
        (merged[_COUNT_CLIENT] > 0) & (merged[_COUNT_COMPANY] == 0)
    ]
    only_company = merged[
        (merged[_COUNT_CLIENT] == 0) & (merged[_COUNT_COMPANY] > 0)
    ]

    # Entre os que existem nos dois lados, separa conciliados de divergentes
    conciliated_mask = both_sides[_COUNT_CLIENT] == both_sides[_COUNT_COMPANY]
    conciliated_keys = both_sides[conciliated_mask].index
    divergent_keys = both_sides[~conciliated_mask].index

    return (
        conciliated_keys,
        divergent_keys,
        only_company.index,   # missing in CLIENT = só na empresa
        only_client.index,    # missing in COMPANY = só no cliente
    )


def _select_records(df: pd.DataFrame, keys: pd.Index) -> pd.DataFrame:
    """Filtra o DataFrame retornando apenas os registros com chave na lista."""
    if keys.empty:
        return pd.DataFrame()
    return df[df[_KEY_COMPOSITE].isin(keys)].copy()


def _build_output(
    client_df: pd.DataFrame,
    company_df: pd.DataFrame,
    keys: pd.Index,
    label: str,
) -> pd.DataFrame:
    """
    Constrói o DataFrame de saída unindo registros do cliente e da empresa.
    
    Para conciliados: lista os pares lado a lado com prefixo de origem.
    """
    if keys.empty:
        return pd.DataFrame()

    client_filtered = client_df[client_df[_KEY_COMPOSITE].isin(keys)].copy()
    company_filtered = company_df[company_df[_KEY_COMPOSITE].isin(keys)].copy()

    # Prefixar colunas para distinguir as origens no relatório
    client_out = client_filtered.add_prefix("CLIENTE_")
    company_out = company_filtered.add_prefix("EMPRESA_")

    # Reset index para concat sequencial
    client_out = client_out.reset_index(drop=True)
    company_out = company_out.reset_index(drop=True)

    # Concatena lado a lado (axis=1) até o menor comprimento
    min_len = min(len(client_out), len(company_out))
    result = pd.concat(
        [client_out.iloc[:min_len], company_out.iloc[:min_len]],
        axis=1,
    )
    result["_status"] = label.upper()
    return result


def _build_divergent_output(
    client_df: pd.DataFrame,
    company_df: pd.DataFrame,
    keys: pd.Index,
) -> pd.DataFrame:
    """
    Para divergentes: mostra o que existe em cada lado e a diferença de quantidade.
    
    Uma chave "divergente" significa que a mesma combinação (conta, valor)
    aparece um número diferente de vezes em cada planilha.
    """
    if keys.empty:
        return pd.DataFrame()

    rows = []
    for key in keys:
        client_rows = client_df[client_df[_KEY_COMPOSITE] == key]
        company_rows = company_df[company_df[_KEY_COMPOSITE] == key]
        
        parts = key.split("||", 1)
        account = parts[0] if len(parts) > 0 else key
        debit = parts[1] if len(parts) > 1 else ""

        rows.append({
            "Conta": account,
            "Valor Débito": debit,
            "Qtd. no Cliente": len(client_rows),
            "Qtd. na Empresa": len(company_rows),
            "Diferença de Qtd.": len(client_rows) - len(company_rows),
            "Linha(s) Cliente": ", ".join(str(r) for r in client_rows.get("_original_row", [])),
            "Linha(s) Empresa": ", ".join(str(r) for r in company_rows.get("_original_row", [])),
            "_status": "DIVERGENTE",
        })

    return pd.DataFrame(rows)


def _find_duplicates(
    client_df: pd.DataFrame, company_df: pd.DataFrame
) -> pd.DataFrame:
    """
    Detecta registros duplicados (mesma chave composta aparecendo 2+ vezes).
    
    Duplicatas não são necessariamente erros — podem ser lançamentos legítimos.
    O relatório informa para que o usuário possa revisar.
    """
    frames = []
    for df, label in [(client_df, "CLIENTE"), (company_df, "EMPRESA")]:
        counts = df[_KEY_COMPOSITE].value_counts()
        dup_keys = counts[counts > 1].index
        if len(dup_keys) > 0:
            dup_df = df[df[_KEY_COMPOSITE].isin(dup_keys)].copy()
            dup_df["_dup_source"] = label
            dup_df["_dup_count"] = dup_df[_KEY_COMPOSITE].map(counts)
            frames.append(dup_df)

    if not frames:
        return pd.DataFrame()
    return pd.concat(frames, ignore_index=True)


def _log_summary(result: ReconciliationResult) -> None:
    logger.info(
        f"Conciliação concluída | "
        f"Conciliados: {result.total_conciliated} | "
        f"Divergentes: {result.total_divergent} | "
        f"Ausentes cliente: {result.total_missing_client} | "
        f"Ausentes empresa: {result.total_missing_company} | "
        f"Duplicidades: {result.total_duplicates}"
    )