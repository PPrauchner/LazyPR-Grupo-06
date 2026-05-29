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

from core.transforms.filtering import (
    apply_filters,
)

from ui.charts import (
    correlation_heatmap,
)

from ui.components import (
    chart_container_start,
    chart_container_end,
)

from ui.sidebar_filters import (
    get_active_filters,
)


def render_correlation_dashboard(
    records,
) -> None:
    """
    Renderiza dashboard de correlação multidimensional.
    """

    active_filter = get_active_filters()

    filtered_records = tuple(
        apply_filters(
            (active_filter,),
            records,
        )
    )

    language_matrix = clarity_by_language(
        filtered_records,
    )

    project_matrix = clarity_by_project_type(
        filtered_records,
    )

    nature_matrix = clarity_by_pr_nature(
        filtered_records,
    )

    st.title("Correlação Multidimensional")

    st.markdown("""
        Relação entre:

        - Clareza
        - Linguagem
        - Tipo de Projeto
        - Natureza da Contribuição
        """)

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        chart_container_start()

        st.plotly_chart(
            correlation_heatmap(
                language_matrix,
                "Clareza x Linguagem",
            ),
            use_container_width=True,
        )

        chart_container_end()

    with col2:

        chart_container_start()

        st.plotly_chart(
            correlation_heatmap(
                project_matrix,
                "Clareza x Tipo de Projeto",
            ),
            use_container_width=True,
        )

        chart_container_end()

    st.write("")

    chart_container_start()

    st.plotly_chart(
        correlation_heatmap(
            nature_matrix,
            "Clareza x Natureza da Contribuição",
        ),
        use_container_width=True,
    )

    chart_container_end()
