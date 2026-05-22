# 💼 Sistema de Conciliação Financeira

Aplicação web para **comparação e conciliação de dados financeiros** entre duas planilhas Excel — a planilha do cliente e a planilha gerada pela empresa. Desenvolvida em Python com interface Streamlit, o sistema identifica automaticamente divergências, registros ausentes e duplicidades entre os lançamentos.

---

## 🎯 Objetivo

Automatizar o processo de conciliação contábil, eliminando conferências manuais em planilhas. A ferramenta cruza os lançamentos de débito de ambas as origens e classifica cada registro em uma de quatro categorias: **conciliado**, **divergente**, **ausente** ou **duplicado**.

---

## ✨ Funcionalidades

- Upload de duas planilhas Excel (`.xlsx` / `.xls`) via interface web
- Validação automática da estrutura dos arquivos antes do processamento
- Limpeza e normalização dos dados (formatos BR/EN, espaços, maiúsculas, nulos)
- Comparação por **chave composta** (nome da conta + valor do débito), resistente a duplicatas
- Filtro automático de registros com débito `!= 0` (regra de negócio central)
- Relatórios interativos na interface com métricas visuais
- Exportação do resultado completo em Excel formatado com 6 abas coloridas
- Mensagens de erro amigáveis e rastreamento de problemas por linha de origem

---

## 🗂️ Estrutura do Projeto

```
financial_reconciliation/
│
├── main.py                        # Ponto de entrada — interface Streamlit
├── requirements.txt               # Dependências do projeto
│
├── config/
│   ├── __init__.py
│   └── settings.py                # Configurações centralizadas (colunas, cores, tolerâncias)
│
└── app/
    ├── __init__.py
    ├── utils/
    │   ├── __init__.py
    │   └── formatting.py          # Utilitários de formatação para a UI
    │
    └── core/
        ├── __init__.py
        ├── models.py              # Dataclasses: ReconciliationResult, ValidationResult
        ├── loader.py              # Leitura e validação estrutural dos arquivos Excel
        ├── cleaner.py             # Limpeza e normalização dos dados
        ├── reconciler.py          # Motor de conciliação (algoritmo principal)
        └── exporter.py            # Geração do Excel de saída com formatação openpyxl
```

### Papel de cada módulo

| Arquivo | Responsabilidade |
|---|---|
| `main.py` | Interface Streamlit: upload, botões, métricas, abas e download |
| `settings.py` | Única fonte da verdade para nomes de colunas, cores e tolerâncias |
| `models.py` | Contratos de dados entre camadas (sem lógica) |
| `loader.py` | Lê bytes do arquivo e valida colunas obrigatórias |
| `cleaner.py` | Normaliza strings, converte números BR/EN, filtra débitos |
| `reconciler.py` | Algoritmo de contagem por chave composta e classificação |
| `exporter.py` | Monta o Excel final com múltiplas abas e formatação profissional |

---

## 📊 Estrutura das Planilhas

### Planilha do Cliente

| Coluna-chave | Nome |
|---|---|
| Conta | `Plano de conta nº. 04` |
| Débito | `Débito` |
| Crédito | `Crédito` |
| Data | `Dt. Movimento` |
| Documento | `Nr. Documento` |

### Planilha da Empresa

| Coluna-chave | Nome |
|---|---|
| Conta | `nomec` |
| Débito | `valdeb` |
| Crédito | `valcre` |
| Data | `datalan` |
| Documento | `numelan` |

> A equivalência entre as planilhas é feita pela coluna `Plano de conta nº. 04` (cliente) ↔ `nomec` (empresa).

---

## ⚙️ Algoritmo de Conciliação

O sistema usa uma abordagem de **contagem de ocorrências por chave composta**, que resolve o problema de múltiplos lançamentos com o mesmo nome de conta:

1. **Chave composta** é formada por `(nome_da_conta, valor_debito_arredondado_2_casas)`
2. As chaves são **contadas** em cada planilha separadamente
3. As contagens são **comparadas**:
   - Mesma quantidade nos dois lados → **Conciliado**
   - Quantidades diferentes → **Divergente**
   - Existe só no cliente → **Ausente na Empresa**
   - Existe só na empresa → **Ausente no Cliente**
4. Chaves com 2+ ocorrências no mesmo lado → **Duplicidade**

Esta abordagem evita o problema do `pd.merge` simples, que geraria combinações cartesianas incorretas com registros duplicados.

---

## 📁 Relatório de Saída (Excel)

O arquivo exportado contém 6 abas:

| Aba | Conteúdo | Cor |
|---|---|---|
| **Resumo** | Métricas executivas e taxa de conciliação | Dinâmica (verde/amarelo/vermelho) |
| **Conciliados** | Registros que batem entre as planilhas | 🟢 Verde |
| **Divergências** | Mesma chave com quantidade diferente de lançamentos | 🔴 Vermelho |
| **Ausentes no Cliente** | Registros presentes só na empresa | 🟡 Amarelo |
| **Ausentes na Empresa** | Registros presentes só no cliente | 🟡 Amarelo |
| **Duplicidades** | Chaves com múltiplas ocorrências em qualquer planilha | 🟩 Verde claro |

---

## 🚀 Como Executar Localmente

### Pré-requisitos

- Python 3.11+
- pip

### Instalação

```bash
# 1. Clone o repositório
git clone https://github.com/seu-usuario/seu-repositorio.git
cd seu-repositorio

# 2. (Opcional) Crie um ambiente virtual
python -m venv .venv
source .venv/bin/activate      # Linux/macOS
.venv\Scripts\activate         # Windows

# 3. Instale as dependências
pip install -r requirements.txt

# 4. Inicie a aplicação
streamlit run main.py
```

A interface estará disponível em `http://localhost:8501`.

---

## ☁️ Deploy no Streamlit Community Cloud (Gratuito)

1. Suba o repositório no **GitHub** com todos os arquivos e pastas
2. Acesse [share.streamlit.io](https://share.streamlit.io) e faça login com sua conta GitHub
3. Clique em **"Create app"**
4. Selecione o repositório, a branch e informe o caminho principal: `main.py`
5. Clique em **"Deploy"**

> **Importante:** todos os diretórios (`config/`, `app/`, `app/core/`, `app/utils/`) devem conter um arquivo `__init__.py` para que o Python reconheça os módulos corretamente.

---

## 🛠️ Tecnologias Utilizadas

| Biblioteca | Versão mínima | Uso |
|---|---|---|
| `streamlit` | 1.32.0 | Interface web |
| `pandas` | 2.2.0 | Manipulação de dados |
| `openpyxl` | 3.1.2 | Leitura e geração de Excel com formatação |
| `xlsxwriter` | 3.2.0 | Engine alternativo para ExcelWriter |
| `numpy` | 1.26.0 | Operações numéricas e tratamento de NaN |

---

## 🔧 Manutenção e Extensão

### Alterar nomes de colunas

Edite apenas o arquivo `config/settings.py`. As constantes `CLIENT_*_COL` e `COMPANY_*_COL` são usadas em todo o projeto — uma única alteração propaga automaticamente.

### Adicionar uma nova coluna à chave de comparação

No arquivo `app/core/reconciler.py`, modifique a função `_add_keys()` para incluir a nova coluna na formação de `_KEY_COMPOSITE`.

### Ajustar tolerância numérica

Altere `NUMERIC_TOLERANCE` em `config/settings.py`. Valores abaixo desta diferença são tratados como iguais (padrão: `0.01`).

### Adicionar nova aba ao relatório

Em `app/core/exporter.py`, adicione uma chamada a `_write_sheet()` dentro do bloco `with pd.ExcelWriter(...)` e defina a cor correspondente em `config/settings.py`.

---

## 📋 Tratamentos de Qualidade de Dados

- **Espaços extras** em células e nomes de colunas são removidos automaticamente
- **Maiúsculas/minúsculas** são normalizadas (comparação case-insensitive)
- **Formatos numéricos** BR (`1.234,56`) e EN (`1,234.56`) são detectados e convertidos
- **Símbolos de moeda** (`R$`) são removidos antes da conversão numérica
- **Valores nulos e vazios** são tratados como `0.0` nas colunas de valor
- **Datas inválidas** são convertidas para `NaT` sem interromper o processamento
- **Índice de linha original** é preservado em `_original_row` para rastreabilidade

---

## 📄 Licença

Este projeto está disponível para uso interno. Adapte conforme as necessidades da sua organização.