"""
Página responsável pela exportação dos resultados enriquecidos.

Permite que o usuário realize download dos dados processados
após execução do pipeline funcional e classificação LLM.

Responsabilidades:
- Exportação em CSV
- Exportação em JSON
- Geração de bytes para download
- Disponibilização dos resultados enriquecidos
- Integração com services/exporters.py
"""

import streamlit as st

from ui.components import (
    download_buttons,
    status_banner,
)


def render_export_page(
    results,
) -> None:
    """
    Renderiza página de exportação.
    """

    st.title("Exportação de Resultados")

    st.markdown("""
        Exporte os resultados processados
        para formatos reutilizáveis.
        """)

    st.divider()

    if not results:

        status_banner(
            "Nenhum resultado disponível.",
            "warning",
        )

        return

    with st.container(border=True):

        st.subheader("Downloads Disponíveis")

        st.write("")

        download_buttons(results)

    st.divider()

    st.caption("Exportação visual • Streamlit UI")
