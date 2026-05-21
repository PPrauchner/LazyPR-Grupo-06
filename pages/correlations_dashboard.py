"""
Dashboard de correlação multidimensional.

Visualiza:
- Clareza x Linguagem
- Clareza x Tipo de Projeto
- Clareza x Natureza do PR
"""

import streamlit as st

from core.aggregations.correlations import (
    clarity_by_language,
    clarity_by_project_type,
    clarity_by_pr_nature,
)

from ui.charts import (
    correlation_heatmap,
)


def render_correlation_dashboard(
    records,
) -> None:
    """
    Renderiza dashboard de correlação.
    """

    cached_records = tuple(records)

    language_matrix = clarity_by_language(cached_records)

    project_matrix = clarity_by_project_type(cached_records)

    nature_matrix = clarity_by_pr_nature(cached_records)

    st.title("Correlação Multidimensional")

    st.markdown("""
        Relação entre:
        - clareza
        - linguagem
        - tipo de projeto
        - natureza da contribuição
        """)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        with st.container(border=True):

            st.plotly_chart(
                correlation_heatmap(
                    language_matrix,
                    "Clareza x Linguagem",
                ),
                use_container_width=True,
            )

    with col2:

        with st.container(border=True):

            st.plotly_chart(
                correlation_heatmap(
                    project_matrix,
                    "Clareza x Tipo de Projeto",
                ),
                use_container_width=True,
            )

    st.write("")

    with st.container(border=True):

        st.plotly_chart(
            correlation_heatmap(
                nature_matrix,
                "Clareza x Natureza da Contribuição",
            ),
            use_container_width=True,
        )
