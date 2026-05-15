"""
Página responsável pelo upload e ingestão de datasets CSV/JSON.

Esta interface permite que o usuário carregue arquivos contendo
pull requests públicos do GitHub. Após o upload, o pipeline
funcional inicia o processamento lazy dos registros utilizando
geradores Python, evitando carregamento completo em memória.

Responsabilidades:
- Upload de arquivos CSV/JSON
- Validação inicial do dataset
- Inicialização do pipeline funcional
- Disparo do processo de classificação e enriquecimento
- Persistência do hash da análise para cache posterior
"""

import streamlit as st

from ui.components import (
    status_banner,
)


def render_upload_page() -> None:
    """
    Renderiza página de upload.
    """

    st.title("Upload de Dataset")

    st.markdown("""
        Faça upload do dataset contendo
        Pull Requests para análise.
        """)

    st.divider()

    with st.container(border=True):

        uploaded_file = st.file_uploader(
            "Selecione um arquivo CSV",
            type=("csv", "json"),
        )

        if uploaded_file:

            status_banner(
                "Dataset carregado com sucesso.",
                "success",
            )

            st.session_state["uploaded_dataset"] = uploaded_file

            st.write("")

            st.caption(f"Arquivo selecionado: " f"{uploaded_file.name}")

        else:

            status_banner(
                "Nenhum dataset carregado.",
                "warning",
            )

    st.divider()

    st.caption("Upload visual • Streamlit UI")
