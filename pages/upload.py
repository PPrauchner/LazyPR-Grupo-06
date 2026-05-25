"""
Página responsável pelo upload e ingestão de datasets CSV/JSON.

Esta interface permite que o usuário carregue arquivos contendo
pull requests públicos do GitHub. Após o upload, o pipeline
funcional inicia o processamento lazy dos registros utilizando
geradores Python, evitando carregamento completo em memória.
"""
import streamlit as st
from streamlit.runtime.uploaded_file_manager import UploadedFile

from core.transforms.cleaning import get_missing_columns
from services.ingestion import read_header_lazily, stream_csv
from core.pipeline.runner import run_pipeline, PipelineConfig
from services.storage import has_cached_analysis, load_results, save_results
from utils.hashing import hash_file_stream
from ui.components import status_banner

def _validate_schema(uploaded_file: UploadedFile) -> bool:
    """Valida o schema do dataset de forma lazy."""
    # Rebobina o ponteiro para garantir leitura segura do header
    uploaded_file.seek(0)
    header = read_header_lazily(uploaded_file)

    if not header:
        st.error("O arquivo enviado está vazio ou é inválido.")
        return False

    missing = get_missing_columns(header)
    if missing:
        st.error(f"Faltam colunas obrigatórias: **{', '.join(missing)}**")
        return False

    return True

def render_upload_page() -> None:
    """Renderiza os componentes visuais e orquestra o pipeline."""
    st.title("📂 Carregar Dataset")

    uploaded_file = st.file_uploader("Selecione o arquivo CSV", type=["csv"])

    if uploaded_file is None:
        st.info("Aguardando upload...")
        return

    # 1. Validação
    if not _validate_schema(uploaded_file):
        st.stop()

    st.success("Schema validado! O arquivo está pronto para o processamento.")

    if st.button("Iniciar Análise 🚀"):
        st.session_state["dataset_file"] = uploaded_file
        
        # 2. Rebobina o ponteiro e gera o hash para o sistema de cache
        uploaded_file.seek(0)
        with st.spinner("Verificando histórico de análises..."):
            file_hash = hash_file_stream(uploaded_file)
            
        # 3. Execução do Fluxo
        if has_cached_analysis(file_hash):
            status_banner("Resultados encontrados no cache. Carregando...", "info")
            st.session_state["analysis_results"] = load_results(file_hash)
            
        else:
            with st.spinner("Processando pipeline funcional e LLMs. Isso pode levar alguns minutos..."):
                status_banner("Iniciando limpeza e avaliação semântica...", "info")
                
                # Rebobina novamente, pois hash_file_stream consumiu a leitura
                uploaded_file.seek(0)
                source_stream = stream_csv(uploaded_file)
                
                # Ativa normalização e classificação do pipeline
                config = PipelineConfig(
                    enable_normalization=True, 
                    enable_classification=True
                )
                
                # Consome o gerador lazy e materializa numa tupla (estrutura imutável)
                resultados_lazy = run_pipeline(source_stream, config)
                resultados_finais = tuple(resultados_lazy)
                
                # Persistência
                save_results(file_hash, resultados_finais)
                st.session_state["analysis_results"] = resultados_finais

        status_banner("Análise concluída com sucesso!", "success")
        
        # 4. Redirecionamento 
        st.switch_page("pages/overview.py")

# Se main.py chama render_upload_page(), a chamada deve ser removida do final ou ajustada.
# Mantemos a chamada para casos de execução direta da página.
if __name__ == "__main__":
    render_upload_page()