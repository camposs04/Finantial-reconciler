# config/settings.py
"""
Configurações centralizadas da aplicação.
Centralizar aqui facilita manutenção: uma mudança reflete em todo o projeto.
"""

from dataclasses import dataclass, field
from typing import Final

# ── Identidade da aplicação ────────────────────────────────────────────────────
APP_TITLE: Final[str] = "Conciliação Financeira"
APP_ICON: Final[str] = "💼"
APP_VERSION: Final[str] = "1.0.0"

# ── Mapeamento de colunas ──────────────────────────────────────────────────────
# Estas são as colunas-chave usadas na comparação.
# Alterar aqui propaga automaticamente para todo o sistema.

# Planilha do CLIENTE
CLIENT_ACCOUNT_COL: Final[str] = "Plano de conta nº. 04"
CLIENT_DEBIT_COL: Final[str] = "Débito"
CLIENT_CREDIT_COL: Final[str] = "Crédito"
CLIENT_DATE_COL: Final[str] = "Dt. Movimento"
CLIENT_DOC_COL: Final[str] = "Nr. Documento"
CLIENT_DESC_COL: Final[str] = "Descrição"
CLIENT_COST_CENTER_COL: Final[str] = "Centro de custo"

# Planilha da EMPRESA
COMPANY_ACCOUNT_COL: Final[str] = "nomec"
COMPANY_DEBIT_COL: Final[str] = "valdeb"
COMPANY_CREDIT_COL: Final[str] = "valcre"
COMPANY_DATE_COL: Final[str] = "datalan"
COMPANY_DOC_COL: Final[str] = "numelan"
COMPANY_DESC_COL: Final[str] = "historico"
COMPANY_COST_CENTER_COL: Final[str] = "clasc"

# ── Tolerâncias numéricas ──────────────────────────────────────────────────────
# Diferenças menores que este valor são tratadas como iguais (evita erros de float)
NUMERIC_TOLERANCE: Final[float] = 0.01

# ── Nomes das abas do Excel de saída ──────────────────────────────────────────
SHEET_CONCILIATED: Final[str] = "Conciliados"
SHEET_DIVERGENT: Final[str] = "Divergências"
SHEET_MISSING_CLIENT: Final[str] = "Ausentes no Cliente"
SHEET_MISSING_COMPANY: Final[str] = "Ausentes na Empresa"
SHEET_DUPLICATES: Final[str] = "Duplicidades"
SHEET_SUMMARY: Final[str] = "Resumo"

# ── Cores para formatação Excel ────────────────────────────────────────────────
# Padrão financeiro: fundo verde = OK, vermelho = erro, amarelo = atenção
COLOR_HEADER_BG: Final[str] = "1F3864"   # Azul escuro
COLOR_HEADER_FG: Final[str] = "FFFFFF"   # Branco
COLOR_CONCILIATED: Final[str] = "C6EFCE"  # Verde claro
COLOR_DIVERGENT: Final[str] = "FFCCCC"    # Vermelho claro
COLOR_MISSING: Final[str] = "FFEB9C"      # Amarelo claro
COLOR_DUPLICATE: Final[str] = "E2EFDA"    # Verde bem claro

# ── Configurações de interface ─────────────────────────────────────────────────
MAX_FILE_SIZE_MB: Final[int] = 50
ALLOWED_EXTENSIONS: Final[tuple] = (".xlsx", ".xls")