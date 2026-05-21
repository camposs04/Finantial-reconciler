# app/core/models.py
"""
Modelos de dados da aplicação.

Por que usar dataclasses?
- Representam claramente o "contrato" de dados entre as camadas
- Evitam passar dicionários avulsos que são difíceis de documentar
- Facilitam autocompletar na IDE e detecção de erros
"""

from dataclasses import dataclass, field
from typing import Optional
import pandas as pd


@dataclass
class ReconciliationResult:
    """
    Encapsula todos os resultados de uma conciliação.
    
    Cada atributo é um DataFrame pandas com os registros classificados.
    Um DataFrame vazio (não None) indica que aquela categoria não tem registros.
    """
    
    # Registros que existem nas duas planilhas com valores correspondentes
    conciliated: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Registros que existem nas duas planilhas mas com valores divergentes
    divergent: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Registros que existem apenas na planilha da empresa (faltam no cliente)
    missing_in_client: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Registros que existem apenas na planilha do cliente (faltam na empresa)
    missing_in_company: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Registros duplicados detectados em qualquer planilha
    duplicates: pd.DataFrame = field(default_factory=pd.DataFrame)
    
    # Metadados do processamento
    total_client_records: int = 0
    total_company_records: int = 0
    processing_errors: list[str] = field(default_factory=list)

    @property
    def total_conciliated(self) -> int:
        return len(self.conciliated)

    @property
    def total_divergent(self) -> int:
        return len(self.divergent)

    @property
    def total_missing_client(self) -> int:
        return len(self.missing_in_client)

    @property
    def total_missing_company(self) -> int:
        return len(self.missing_in_company)

    @property
    def total_duplicates(self) -> int:
        return len(self.duplicates)

    @property
    def has_errors(self) -> bool:
        return len(self.processing_errors) > 0

    @property
    def reconciliation_rate(self) -> float:
        """Taxa de conciliação: porcentagem de registros que batem."""
        total = self.total_client_records + self.total_company_records
        if total == 0:
            return 0.0
        matched = self.total_conciliated * 2  # cada conciliado aparece nas duas planilhas
        return round((matched / total) * 100, 2)


@dataclass
class ValidationResult:
    """Resultado da validação de um arquivo Excel antes do processamento."""
    is_valid: bool
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    detected_columns: list[str] = field(default_factory=list)
    row_count: int = 0