from app.core.cleaner import clean_client_df, clean_company_df, filter_nonzero_debits
from app.core.reconciler import reconcile
from app.core.exporter import export_to_excel
import streamlit as st
from datetime import datetime

# Importa as configurações necessárias para os filtros
from config.settings import CLIENT_DEBIT_COL, COMPANY_DEBIT_COL

# Importa as funções que você expôs no app/core/__init__.py
from app.core.loader import (
    load_excel as load_excel, 
    validate_client_file as validate_client_file, 
    validate_company_file as validate_company_file, 
    normalize_column_names as normalize_column_names
)
# 1. Configuração da Página do Streamlit
st.set_page_config(
    page_title="Conciliador Fiscal", 
    page_icon="📊", 
    layout="wide"
)

st.title("📊 Sistema de Conciliação de Planilhas Contábeis")
st.markdown("Carregue os arquivos do cliente e da empresa para realizar a validação e o cruzamento dos débitos.")
st.markdown("---")

# 2. Área de Upload dos Arquivos (Lado a Lado)
col1, col2 = st.columns(2)

with col1:
    st.subheader("📁 Planilha do Cliente")
    client_file = st.file_uploader(
        "Selecione o arquivo Excel do Cliente", 
        type=["xlsx", "xls"], 
        key="uploader_cliente"
    )

with col2:
    st.subheader("📁 Planilha da Empresa")
    company_file = st.file_uploader(
        "Selecione o arquivo Excel da Empresa", 
        type=["xlsx", "xls"], 
        key="uploader_empresa"
    )

# 3. Execução do Pipeline de Dados
if client_file and company_file:
    
    # Botão de ação destacado
    if st.button("🚀 Executar Conciliação", type="primary", use_container_width=True):
        
        # Cria uma barra de carregamento visual no Streamlit
        with st.spinner("Processando e cruzando dados... Por favor, aguarde."):
            try:
                # PASSO 1: Carregar os bytes brutos (conforme sua função load_excel espera)
                df_client_raw = load_excel(client_file.getvalue(), client_file.name)
                df_company_raw = load_excel(company_file.getvalue(), company_file.name)

                # PASSO 2: Normalizar nomes das colunas (remover espaços invisíveis do Excel)
                df_client_raw = normalize_column_names(df_client_raw)
                df_company_raw = normalize_column_names(df_company_raw)

                # PASSO 3: Validação estrutural de colunas obrigatórias
                valid_client = validate_client_file(df_client_raw)
                valid_company = validate_company_file(df_company_raw)

                # Se houver erros de estrutura, interrompe o Streamlit e mostra na tela
                if not valid_client.is_valid or not valid_company.is_valid:
                    st.error("❌ Falha na validação de estrutura das planilhas:")
                    if not valid_client.is_valid:
                        for err in valid_client.errors:
                            st.error(f"Cliente: {err}")
                    if not valid_company.is_valid:
                        for err in valid_company.errors:
                            st.error(f"Empresa: {err}")
                    st.stop() # Para a execução aqui

                # PASSO 4: Limpeza e Normalização dos dados internos
                df_client_clean = clean_client_df(df_client_raw)
                df_company_clean = clean_company_df(df_company_raw)

                # PASSO 5: Filtragem de registros (Apenas débitos != 0)
                df_client_filtered = filter_nonzero_debits(df_client_clean, CLIENT_DEBIT_COL)
                df_company_filtered = filter_nonzero_debits(df_company_clean, COMPANY_DEBIT_COL)

                # PASSO 6: Executar o Motor de Conciliação
                result = reconcile(df_client_filtered, df_company_filtered)

                # Se o motor reportar erros graves pós-processamento
                if result.has_errors:
                    for err in result.processing_errors:
                        st.error(f"Erro no processamento: {err}")
                    st.stop()

                # ── INTERFACE DE RESULTADOS ───────────────────────────────────
                st.success("✨ Conciliação concluída com sucesso!")

                # Exibição de Métricas em Cards Visuais
                m_col1, m_col2, m_col3, m_col4 = st.columns(4)
                m_col1.metric("Taxa de Conciliação", f"{result.reconciliation_rate}%")
                m_col2.metric("Pares Conciliados", result.total_conciliated)
                m_col3.metric("Chaves Divergentes", result.total_divergent)
                m_col4.metric("Duplicidades Identificadas", result.total_duplicates)

                # Abas para pré-visualização rápida no painel do Streamlit
                tab_divergent, tab_duplicates, tab_info = st.tabs([
                    "⚠️ Ver Divergências", 
                    "🔄 Ver Duplicadas", 
                    "ℹ️ Detalhes do Processo"
                ])
                
                with tab_divergent:
                    if not result.divergent.empty:
                        st.dataframe(result.divergent, use_container_width=True)
                    else:
                        st.info("Nenhuma divergência de quantidade de lançamentos encontrada.")

                with tab_duplicates:
                    if not result.duplicates.empty:
                        st.dataframe(result.duplicates, use_container_width=True)
                    else:
                        st.info("Nenhuma duplicidade de chave encontrada nas planilhas.")

                with tab_info:
                    st.write(f"**Registros analisados do Cliente (pós-filtro):** {result.total_client_records}")
                    st.write(f"**Registros analisados da Empresa (pós-filtro):** {result.total_company_records}")

                # PASSO 7: Gerar o Excel Formatado via openpyxl (Retorna bytes)
                excel_bytes = export_to_excel(result)
                
                # Botão de Download do arquivo final gerado em memória
                st.markdown("---")
                st.markdown("### 📥 Baixar Relatório Final Formatado")
                
                data_atual = datetime.now().strftime("%Y%m%d_%H%M%S")
                st.download_button(
                    label="⬇️ Baixar Relatório de Conciliação (.xlsx)",
                    data=excel_bytes,
                    file_name=f"Relatorio_Conciliacao_{data_atual}.xlsx",
                    mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                    use_container_width=True
                )

            except Exception as e:
                st.error(f"Ocorreu um erro inesperado durante o processamento: {e}")
                st.exception(e) # Mostra o traceback se você estiver em ambiente de desenvolvimento

else:
    st.info("💡 Aguardando o upload de ambas as planilhas para liberar a conciliação.")