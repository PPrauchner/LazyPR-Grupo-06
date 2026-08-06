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
from core.pipeline.runner import run_pipeline
from core.pipeline.stages import (
    Stage,
    clean_records,
    enrich_without_classification,
    normalize_records,
)
from services.classifiers import classify_project_type
from services.storage import has_cached_analysis, load_results, save_results
from utils.hashing import hash_file_stream
from ui.components import status_banner

# Etapas oferecidas ao usuário, na ordem em que compõem o pipeline.
# Cada entrada: (rótulo, ajuda, Etapa).
_SELECTABLE_STAGES: tuple[tuple[str, str, Stage], ...] = (
    (
        "Limpeza textual",
        "Remove HTML, espaços sobrando e trunca campos longos.",
        clean_records,
    ),
    (
        "Normalização",
        "Converte a linguagem inferida para a forma canônica.",
        normalize_records,
    ),
    (
        "Classificação semântica (LLM)",
        "Classifica tipo de projeto, natureza e clareza. Sem ela, as três "
        "classificações ficam como 'unknown'.",
        classify_project_type,
    ),
)


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


def _select_stages() -> tuple[Stage, ...]:
    """Oferece as Etapas ao usuário e monta a tupla que será executada.

    Uma Etapa desmarcada simplesmente não entra na tupla (Regra Geral 05).
    Quando a Classificação Semântica fica de fora, o enriquecimento neutro
    entra no lugar dela para que o resultado continue sendo `AnalysisResult`
    e possa ser persistido e agregado como qualquer outra Análise.

    Returns:
        Etapas escolhidas, na ordem de aplicação.
    """
    st.markdown("**Etapas do pipeline**")

    chosen = tuple(
        stage
        for label, help_text, stage in _SELECTABLE_STAGES
        if st.checkbox(label, value=True, help=help_text, key=f"stage::{label}")
    )

    return (
        chosen
        if classify_project_type in chosen
        else chosen + (enrich_without_classification,)
    )


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

    steps = _select_stages()

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

            st.session_state["analysis_ready"] = True
            st.rerun()

        # -----------------------------------------------------
        # PIPELINE
        # -----------------------------------------------------

        with st.spinner("Processando pipeline funcional e LLMs..."):

            uploaded_file.seek(0)

            source_stream = stream_csv(uploaded_file)

            # A recusa de schema não interrompe a Análise: o llm_client degrada
            # o registro recusado para o sentinela `unknown` e registra a
            # recusa em log, para que os demais registros cheguem ao fim e
            # sejam persistidos (ADR-0004).
            resultados_lazy = run_pipeline(
                steps,
                source_stream,
            )

            resultados_finais = tuple(resultados_lazy)

        save_results(
            file_hash,
            resultados_finais,
        )

        st.session_state["analysis_results"] = resultados_finais

        st.session_state["analysis_ready"] = True

        status_banner(
            "Análise concluída com sucesso!",
            "success",
        )

        st.rerun()
