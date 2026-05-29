"""
Página responsável pelo upload e ingestão de datasets CSV.

Responsabilidades:
- Upload de arquivos CSV
- Validação estrutural do dataset
- Inicialização do pipeline funcional
- Persistência do arquivo em sessão
"""

import streamlit as st

from streamlit.runtime.uploaded_file_manager import (
    UploadedFile,
)

from services.ingestion import (
    read_header_lazily,
)

from core.validators.dataset_schema import (
    validate_dataset_columns,
)

from services.ingestion import (
    ingest_dataset,
)


def _validate_schema(
    uploaded_file: UploadedFile,
) -> bool:
    """
    Valida estrutura do dataset.
    """

    header = read_header_lazily(
        uploaded_file,
    )

    if not header:

        st.error("O arquivo enviado está vazio ou é inválido.")

        return False

    validation = validate_dataset_columns(
        header,
    )

    if not validation["is_valid"]:

        st.error(
            "Faltam colunas obrigatórias: " + ", ".join(validation["missing_required"])
        )

        return False

    if validation["missing_optional"]:

        st.info(
            "Modo compatível ativado: "
            "Algumas métricas avançadas "
            "Foram desabilitadas."
        )

    return True


def render_upload_page() -> None:
    """
    Renderiza página de upload.
    """

    st.title("📂 Carregar Dataset")

    st.markdown("""
        Envie um dataset CSV contendo Pull Requests
        públicos do GitHub para iniciar a análise.
        """)

    uploaded_file = st.file_uploader(
        "Selecione o arquivo CSV",
        type=["csv"],
        key="upload_dataset_csv",
    )

    if uploaded_file is None:

        st.info("Aguardando upload do dataset...")

        return

    is_valid = _validate_schema(
        uploaded_file,
    )

    if not is_valid:

        st.stop()

if st.button(
    "Iniciar Análise 🚀",
    width="stretch",
    key="btn_iniciar_analise",
):

    with st.spinner(
        "Processando dataset..."
    ):

        try:

            records = ingest_dataset(
                uploaded_file,
            )

            st.session_state[
                "analysis_results"
            ] = records

            st.session_state[
                "dataset_name"
            ] = uploaded_file.name

            st.success(
                f"Dataset processado com sucesso. "
                f"{len(records)} registros carregados."
            )

        except Exception as exc:

            st.error(
                f"Erro durante o processamento: {exc}"
            )