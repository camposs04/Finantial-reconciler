# app/core/cleaner.py
"""
Limpeza e normalização dos dados antes da comparação.

Este módulo é o mais crítico para a confiabilidade da conciliação.
Pequenas diferenças de formato (espaço extra, maiúscula, vírgula vs ponto)
podem fazer registros idênticos parecerem diferentes.

Filosofia: limpar cedo, limpar uma vez, limpar em um só lugar.
"""

from __future__ import annotations

import logging
import re
from typing import cast

import numpy as np
import pandas as pd

try:
    from config.settings import (
        CLIENT_ACCOUNT_COL, CLIENT_DEBIT_COL, CLIENT_CREDIT_COL,
        CLIENT_DATE_COL, CLIENT_DOC_COL, CLIENT_DESC_COL,
        COMPANY_ACCOUNT_COL, COMPANY_DEBIT_COL, COMPANY_CREDIT_COL,
        COMPANY_DATE_COL, COMPANY_DOC_COL, COMPANY_DESC_COL,
    )
except ImportError as e:
    logger_init = logging.getLogger(__name__)
    logger_init.error(f"Erro ao importar config.settings: {e}")
    raise

logger = logging.getLogger(__name__)

# Colunas numéricas de cada planilha
_CLIENT_NUMERIC_COLS = [CLIENT_DEBIT_COL, CLIENT_CREDIT_COL]
_COMPANY_NUMERIC_COLS = [COMPANY_DEBIT_COL, COMPANY_CREDIT_COL]


# ── Funções públicas ────────────────────────────────────────────────────────────

def clean_client_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completo de limpeza para a planilha do cliente.
    Retorna um novo DataFrame — nunca modifica o original (imutabilidade).
    """
    df = df.copy()
    df = _strip_all_strings(df)
    df = _normalize_numeric_cols(df, _CLIENT_NUMERIC_COLS)
    df = _normalize_text_col(df, CLIENT_ACCOUNT_COL)
    df = _parse_date_col(df, CLIENT_DATE_COL)
    df = _add_source_label(df, "CLIENTE")
    df = _add_row_index(df)
    logger.info(f"Cliente: {len(df)} registros após limpeza")
    return df


def clean_company_df(df: pd.DataFrame) -> pd.DataFrame:
    """
    Pipeline completo de limpeza para a planilha da empresa.
    Mesma filosofia do cliente, adaptada às colunas da empresa.
    """
    df = df.copy()
    df = _strip_all_strings(df)
    df = _normalize_numeric_cols(df, _COMPANY_NUMERIC_COLS)
    df = _normalize_text_col(df, COMPANY_ACCOUNT_COL)
    df = _parse_date_col(df, COMPANY_DATE_COL)
    df = _add_source_label(df, "EMPRESA")
    df = _add_row_index(df)
    logger.info(f"Empresa: {len(df)} registros após limpeza")
    return df


def filter_nonzero_debits(df: pd.DataFrame, debit_col: str) -> pd.DataFrame:
    """
    Filtra apenas registros com débito diferente de zero.
    
    Regra de negócio central: só comparamos débitos != 0.
    NaN é tratado como zero (registro sem débito = não comparável).
    """
    # Garante que a coluna existe e é numérica
    if debit_col not in df.columns:
        logger.warning(f"Coluna '{debit_col}' não encontrada. Retornando DataFrame vazio.")
        return df.iloc[0:0].copy()
    
    mask = df[debit_col].notna() & (df[debit_col].abs() > 1e-9)
    filtered = df[mask].copy()
    logger.info(f"Filtro débito != 0: {len(df)} → {len(filtered)} registros")
    return filtered


# ── Funções privadas (implementação) ───────────────────────────────────────────

def _strip_all_strings(df: pd.DataFrame) -> pd.DataFrame:
    """
    Remove espaços extras de todas as células de texto.
    
    Por que aplicar em todas as colunas?
    - Não sabemos antecipadamente quais colunas serão usadas como chave
    - Um espaço invisível pode causar falha de correspondência
    """
    str_cols = df.select_dtypes(include=["object"]).columns
    df[str_cols] = df[str_cols].apply(lambda col: col.str.strip())
    return df


def _normalize_numeric_cols(df: pd.DataFrame, cols: list[str]) -> pd.DataFrame:
    """
    Converte colunas de valor para float, tratando formatação brasileira.
    
    Problemas comuns:
    - "1.234,56" (padrão BR) vs "1234.56" (padrão EN)
    - Células vazias que devem virar 0.0
    - Símbolos de moeda: "R$ 100,00"
    - Parênteses para negativos: "(100,00)"
    """
    for col in cols:
        if col not in df.columns:
            continue
        df[col] = df[col].apply(_parse_numeric_value)
    return df


def _parse_numeric_value(value: object) -> float:
    """
    Converte um valor bruto em float, com suporte a formatos BR/EN.
    
    Estratégia:
    1. Se já for numérico, retorna direto
    2. Remove símbolos de moeda e espaços
    3. Detecta se é formato BR (vírgula decimal) ou EN (ponto decimal)
    4. Trata parênteses como negativo
    5. Retorna 0.0 em caso de falha (não propaga erro)
    """
    if value is None or value == "" or (isinstance(value, float) and np.isnan(value)):
        return 0.0
    
    if isinstance(value, (int, float)):
        return float(value) if not np.isnan(float(value)) else 0.0
    
    s = str(value).strip()
    
    # Trata parênteses como negativo: (100,00) → -100.00
    is_negative = s.startswith("(") and s.endswith(")")
    if is_negative:
        s = s[1:-1]
    
    # Remove símbolos de moeda e espaços
    s = re.sub(r"[R$\s]", "", s)
    
    # Detecta e converte formato:
    # Se tem vírgula E ponto: decide qual é decimal
    # Exemplo BR: "1.234,56" → ponto=milhar, vírgula=decimal
    # Exemplo EN: "1,234.56" → vírgula=milhar, ponto=decimal
    if "," in s and "." in s:
        # Assume que o último separador é o decimal
        last_comma = s.rfind(",")
        last_dot = s.rfind(".")
        if last_comma > last_dot:
            # Formato BR: 1.234,56
            s = s.replace(".", "").replace(",", ".")
        else:
            # Formato EN: 1,234.56
            s = s.replace(",", "")
    elif "," in s:
        # Só vírgula → decimal brasileiro: "1234,56"
        s = s.replace(",", ".")
    # Se só ponto: já está em formato EN, não precisa tratar
    
    try:
        result = float(s)
        return -result if is_negative else result
    except (ValueError, TypeError):
        logger.debug(f"Não foi possível converter '{value}' para número. Assumindo 0.0")
        return 0.0


def _normalize_text_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Normaliza uma coluna de texto:
    - Remove espaços extras internos (double spaces)
    - Converte para maiúsculas para comparação case-insensitive
    - Substitui valores nulos por string vazia
    """
    if col not in df.columns:
        return df
    df[col] = (
        df[col]
        .fillna("")
        .str.strip()
        .str.upper()
        .str.replace(r"\s+", " ", regex=True)  # múltiplos espaços → um único
    )
    return df


def _parse_date_col(df: pd.DataFrame, col: str) -> pd.DataFrame:
    """
    Tenta converter uma coluna de data para datetime.
    Erros de conversão são silenciados (data inválida → NaT).
    """
    if col not in df.columns:
        return df
    df[col] = pd.to_datetime(df[col], errors="coerce", dayfirst=True)
    return df


def _add_source_label(df: pd.DataFrame, label: str) -> pd.DataFrame:
    """Adiciona coluna identificando a origem do registro (para o relatório final)."""
    df["_source"] = label
    return df


def _add_row_index(df: pd.DataFrame) -> pd.DataFrame:
    """
    Preserva o índice original da planilha como coluna.
    
    Por que isso é importante?
    - Depois de filtros e merges, o índice pandas é reorganizado
    - Manter o número de linha original facilita auditoria
      ("linha 47 da planilha original tem divergência")
    """
    df = df.reset_index(drop=False)
    df = df.rename(columns={"index": "_original_row"})
    df["_original_row"] = df["_original_row"] + 2  # +2: 1 para header, 1 para base-1
    return df