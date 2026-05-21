# app/utils/formatting.py
"""
Utilitários de formatação para a interface Streamlit.
Centraliza formatação de números, cores e textos da UI.
"""

from __future__ import annotations
import locale


def fmt_currency(value: float | int | None) -> str:
    """Formata um número como moeda brasileira (R$ 1.234,56)."""
    if value is None:
        return "—"
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return str(value)


def fmt_number(value: float | int | None) -> str:
    """Formata número inteiro com separador de milhar."""
    if value is None:
        return "—"
    try:
        return f"{int(value):,}".replace(",", ".")
    except (ValueError, TypeError):
        return str(value)


def fmt_percent(value: float | None) -> str:
    """Formata porcentagem com 2 casas decimais."""
    if value is None:
        return "—"
    return f"{float(value):.2f}%"


def status_color(rate: float) -> str:
    """
    Retorna uma cor semântica baseada na taxa de conciliação.
    ≥ 90% → verde, ≥ 70% → amarelo, < 70% → vermelho
    """
    if rate >= 90:
        return "normal"
    elif rate >= 70:
        return "off"
    return "inverse"


def truncate_df_for_display(df, max_rows: int = 500):
    """
    Limita exibição de DataFrames grandes na interface.
    Streamlit fica lento com muitas linhas no st.dataframe.
    """
    if df is None or df.empty:
        return df
    if len(df) > max_rows:
        return df.head(max_rows)
    return df