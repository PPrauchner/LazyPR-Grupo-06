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
from services.llm_client import SchemaRefusalError
from core.pipeline.runner import run_pipeline, PipelineConfig
from services.storage import has_cached_analysis, load_results, save_results
from utils.hashing import hash_file_stream
from ui.components import status_banner


def _validate_schema(uploaded_file: UploadedFile) -> bool:
    """Valida o schema do dataset de forma lazy."""
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

    # ---------------------------------------------------------
    # Análise já concluída
    # ---------------------------------------------------------

    if st.session_state.get("analysis_ready", False):

        st.success("✅ Análise pronta!")

        col1, col2 = st.columns(2)

        with col1:

            if st.button("📊 Ver Análise"):

                st.session_state["page_override"] = "📊 Overview"
                st.rerun()

        with col2:

            if st.button("📂 Novo Upload"):

                st.session_state.pop(
                    "analysis_results",
                    None,
                )

                st.session_state.pop(
                    "analysis_ready",
                    None,
                )

                st.session_state.pop(
                    "pipeline_stats",
                    None,
                )

                st.rerun()

        return

    # ---------------------------------------------------------
    # Upload
    # ---------------------------------------------------------

    uploaded_file = st.file_uploader(
        "Selecione o arquivo CSV",
        type=["csv"],
    )

    if uploaded_file is None:

        st.info("Aguardando upload...")
        return

    # ---------------------------------------------------------
    # Validação
    # ---------------------------------------------------------

    if not _validate_schema(uploaded_file):

        st.stop()

    st.markdown(
        """
        <h4 style="margin-bottom:0;">
            ✓ Dataset validado
        </h4>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # Execução
    # ---------------------------------------------------------

    if st.button("Iniciar Análise 🚀"):

        uploaded_file.seek(0)

        with st.spinner("Verificando histórico de análises..."):

            file_hash, _ = hash_file_stream(uploaded_file)

        # -----------------------------------------------------
        # CACHE
        # -----------------------------------------------------

        if has_cached_analysis(file_hash):

            with st.spinner("Carregando resultados do cache..."):

                results = tuple(load_results(file_hash))

            st.session_state["analysis_results"] = results

            st.session_state["pipeline_stats"] = {
                "loaded": len(results),
                "cleaned": len(results),
                "normalized": len(results),
                "classified": len(results),
            }

            st.session_state["analysis_ready"] = True
            st.rerun()

        # -----------------------------------------------------
        # PIPELINE
        # -----------------------------------------------------

        with st.spinner("Processando pipeline funcional e LLMs..."):

            uploaded_file.seek(0)

            source_stream = stream_csv(uploaded_file)

            config = PipelineConfig(
                enable_normalization=True,
                enable_classification=True,
            )

            # A recusa de schema é falha alta e deliberada: não vira sentinela
            # `unknown` (ADR-0004). Aqui ela só troca de forma — vira mensagem
            # legível nomeando o repositório, em vez de traceback cru.
            try:

                resultados_lazy = run_pipeline(
                    source_stream,
                    config,
                )

                resultados_finais = tuple(resultados_lazy)

            except SchemaRefusalError as refusal:

                st.error(
                    f"O modelo devolveu uma classificação fora do vocabulário "
                    f"controlado para o repositório **{refusal.repo}**, e a "
                    f"análise foi interrompida sem gravar resultados. "
                    f"Conteúdo recusado: `{refusal.content}`"
                )

                st.stop()
                return

        save_results(
            file_hash,
            resultados_finais,
        )

        st.session_state["analysis_results"] = resultados_finais

        st.session_state["pipeline_stats"] = {
            "loaded": len(resultados_finais),
            "cleaned": len(resultados_finais),
            "normalized": len(resultados_finais),
            "classified": len(resultados_finais),
        }

        st.session_state["analysis_ready"] = True

        status_banner(
            "Análise concluída com sucesso!",
            "success",
        )

        st.rerun()
