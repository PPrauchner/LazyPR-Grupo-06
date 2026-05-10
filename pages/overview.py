"""
Dashboard principal para visualização do volume de contribuições.

Esta página apresenta gráficos interativos construídos com
Streamlit e Plotly para análise agregada dos pull requests.

Responsabilidades:
    - Exibir volume de PRs por linguagem
    - Exibir volume por tipo de projeto
    - Exibir volume por natureza da contribuição
    - Organizar o dashboard em containers e colunas
    - Consumir exclusivamente dados previamente agregados
    - Manter separação entre UI e lógica funcional

Não deve:
    - Realizar agregações diretamente
    - Modificar o dataset
    - Implementar regras de negócio
"""

from functools import reduce
from typing import Iterable, Any

import streamlit as st

from core.aggregations.counters import (
    count_by_language,
    count_by_project_type,
    count_by_pr_nature,
)

from ui.charts import (
    bar_chart_by_category,
)


def _count_total_records(
    records: Iterable[Any],
) -> int:
    """
    Conta total de registros utilizando reduce()
    para manter aderência funcional ao projeto.
    """

    return reduce(
        lambda total, _: total + 1,
        records,
        0,
    )


def render_overview(
    records: Iterable[Any],
) -> None:
    """
    Renderiza dashboard principal de overview.

    Args:
        records:
            Coleção de AnalysisResult já processados.
    """

    # =====================================
    # Evita consumo múltiplo de generators
    # durante agregações independentes.

    cached_records = tuple(records)

    # =====================================
    # AGREGAÇÕES FUNCIONAIS
    # =====================================

    language_data = count_by_language(cached_records)

    project_type_data = count_by_project_type(cached_records)

    pr_nature_data = count_by_pr_nature(cached_records)

    total_records = _count_total_records(cached_records)

    st.title("Overview de Pull Requests")

    st.markdown("""
        Visualização agregada do volume de contribuições
        classificadas pelo pipeline funcional do projeto.
        """)

    st.divider()

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    with kpi_col1:

        st.metric(
            label="Total de PRs",
            value=total_records,
        )

    with kpi_col2:

        st.metric(
            label="Linguagens",
            value=len(language_data),
        )

    with kpi_col3:

        st.metric(
            label="Tipos de Projeto",
            value=len(project_type_data),
        )

    st.divider()

    col1, col2 = st.columns(2)

    with col1:

        st.plotly_chart(
            bar_chart_by_category(
                language_data,
                title="PRs por Linguagem",
                x_title="Linguagem",
            ),
            use_container_width=True,
        )

    with col2:

        st.plotly_chart(
            bar_chart_by_category(
                project_type_data,
                title="PRs por Tipo de Projeto",
                x_title="Tipo de Projeto",
            ),
            use_container_width=True,
        )

    st.plotly_chart(
        bar_chart_by_category(
            pr_nature_data,
            title="PRs por Natureza da Contribuição",
            x_title="Natureza",
        ),
        use_container_width=True,
    )
