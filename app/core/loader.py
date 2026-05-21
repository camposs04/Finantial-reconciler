# app/core/loader.py
"""
Responsável por carregar e validar os arquivos Excel.

Separar a leitura da lógica de negócio é um princípio fundamental:
se amanhã você precisar ler de um banco de dados ou CSV, só muda aqui.
"""

from __future__ import annotations

import io
import logging
from typing import Optional

import pandas as pd

from config.settings import (
    CLIENT_ACCOUNT_COL, CLIENT_DEBIT_COL, CLIENT_CREDIT_COL,
    COMPANY_ACCOUNT_COL, COMPANY_DEBIT_COL, COMPANY_CREDIT_COL,
    ALLOWED_EXTENSIONS,
)
from app.core.models import ValidationResult

logger = logging.getLogger(__name__)

# Colunas obrigatórias mínimas para cada planilha
_CLIENT_REQUIRED_COLS = {CLIENT_ACCOUNT_COL, CLIENT_DEBIT_COL}
_COMPANY_REQUIRED_COLS = {COMPANY_ACCOUNT_COL, COMPANY_DEBIT_COL}


def load_excel(file_bytes: bytes, filename: str) -> pd.DataFrame:
    """
    Lê um arquivo Excel e retorna um DataFrame bruto (sem transformações).
    
    Por que bytes e não path?
    - O Streamlit entrega os arquivos como objetos BytesIO em memória
    - Não salvar em disco é mais seguro e portável
    
    Args:
        file_bytes: Conteúdo do arquivo em bytes
        filename: Nome do arquivo (usado apenas para log)
    
    Returns:
        DataFrame com os dados brutos da planilha
    
    Raises:
        ValueError: Se o arquivo não puder ser lido
    """
    try:
        df = pd.read_excel(
            io.BytesIO(file_bytes),
            dtype=str,          # Lê TUDO como string primeiro — evita conversões indevidas
            keep_default_na=False,  # Não converter strings vazias em NaN automaticamente
        )
        logger.info(f"Arquivo '{filename}' carregado: {len(df)} linhas, {len(df.columns)} colunas")
        return df
    except Exception as e:
        raise ValueError(f"Não foi possível ler o arquivo '{filename}': {e}") from e


def validate_client_file(df: pd.DataFrame) -> ValidationResult:
    """Valida se o DataFrame do cliente tem as colunas obrigatórias."""
    return _validate(df, _CLIENT_REQUIRED_COLS, "cliente")


def validate_company_file(df: pd.DataFrame) -> ValidationResult:
    """Valida se o DataFrame da empresa tem as colunas obrigatórias."""
    return _validate(df, _COMPANY_REQUIRED_COLS, "empresa")


def _validate(df: pd.DataFrame, required: set[str], source: str) -> ValidationResult:
    """
    Validação genérica de um DataFrame.
    
    Lógica:
    1. Verifica colunas obrigatórias
    2. Verifica se há dados (não só cabeçalho)
    3. Emite avisos sobre colunas opcionais ausentes
    """
    errors: list[str] = []
    warnings: list[str] = []
    detected = list(df.columns)

    # Normaliza os nomes das colunas do arquivo para comparação
    normalized_cols = {c.strip().lower(): c for c in df.columns}
    
    missing_required = []
    for col in required:
        if col.strip().lower() not in normalized_cols:
            missing_required.append(col)

    if missing_required:
        errors.append(
            f"Planilha do {source}: coluna(s) obrigatória(s) não encontrada(s): "
            f"{', '.join(missing_required)}"
        )

    if len(df) == 0:
        errors.append(f"Planilha do {source} está vazia.")

    return ValidationResult(
        is_valid=len(errors) == 0,
        errors=errors,
        warnings=warnings,
        detected_columns=detected,
        row_count=len(df),
    )


def normalize_column_names(df: pd.DataFrame) -> pd.DataFrame:
    """
    Normaliza os nomes das colunas removendo espaços extras.
    
    Por que isso é importante?
    - Excel frequentemente adiciona espaços invisíveis nos cabeçalhos
    - Uma coluna chamada " Débito" (com espaço) não é igual a "Débito"
    """
    df.columns = [str(c).strip() for c in df.columns]
    return df