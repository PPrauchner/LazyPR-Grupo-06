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

from core.aggregations.metrics import (
    char_distribution,
    description_stats,
    word_distribution,
)

from core.aggregations.counters import (
    count_by_language,
    count_by_project_type,
    count_by_pr_nature,
)

from ui.charts import (
    bar_chart_by_category,
    distribution_chart_from_bins,
)

from core.transforms.filtering import (
    apply_filters,
)

from ui.sidebar_filters import (
    get_active_filters,
)


def _count_total_records(
    records: Iterable[Any],
) -> int:
    """
    Conta total de registros utilizando reduce().
    """

    return reduce(
        lambda total, _: total + 1,
        records,
        0,
    )


def render_header() -> None:
    """
    Renderiza cabeçalho principal.
    """

    st.title("Overview de Pull Requests")

    st.markdown("""
        Visualização agregada do volume de contribuições
        classificadas pelo pipeline funcional do projeto.
        """)

    st.divider()


def render_kpis(
    total_records: int,
    language_data: dict,
    project_type_data: dict,
) -> None:
    """
    Renderiza KPIs principais.
    """

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


def render_main_charts(
    language_data: dict,
    project_type_data: dict,
    pr_nature_data: dict,
) -> None:
    """
    Renderiza gráficos principais do dashboard.
    """

    col1, col2 = st.columns(2)

    with col1:

        with st.container(border=True):

            st.plotly_chart(
                bar_chart_by_category(
                    language_data,
                    title="PRs por Linguagem",
                    x_title="Linguagem",
                ),
                use_container_width=True,
            )

    with col2:

        with st.container(border=True):

            st.plotly_chart(
                bar_chart_by_category(
                    project_type_data,
                    title="PRs por Tipo de Projeto",
                    x_title="Tipo de Projeto",
                ),
                use_container_width=True,
            )

    st.write("")

    with st.container(border=True):

        st.plotly_chart(
            bar_chart_by_category(
                pr_nature_data,
                title="PRs por Natureza da Contribuição",
                x_title="Natureza",
            ),
            use_container_width=True,
        )


def render_description_distributions(
    records: Iterable[Any],
) -> None:
    """
    Renderiza distribuições estatísticas
    de tamanho de descrição.
    """

    stats = description_stats(records)

    char_data = char_distribution(records)

    word_data = word_distribution(records)

    st.divider()

    st.subheader("Distribuição de Tamanho de Descrição")

    metric_col1, metric_col2 = st.columns(2)

    with metric_col1:

        st.metric(
            "Média de Caracteres",
            stats["char"]["mean"],
        )

    with metric_col2:

        st.metric(
            "Média de Palavras",
            stats["word"]["mean"],
        )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        with st.container(border=True):

            st.plotly_chart(
                distribution_chart_from_bins(
                    char_data,
                    dimension="char_count",
                ),
                use_container_width=True,
            )

    with chart_col2:

        with st.container(border=True):

            st.plotly_chart(
                distribution_chart_from_bins(
                    word_data,
                    dimension="word_count",
                ),
                use_container_width=True,
            )


def render_footer() -> None:
    """
    Renderiza rodapé do dashboard.
    """

    st.divider()

    st.caption("RP3 • Functional Dashboard • Streamlit")


def render_overview(
    records: Iterable[Any],
) -> None:
    """
    Renderiza dashboard principal de overview.
    """

    active_filter = get_active_filters()

    filtered_records = tuple(
        apply_filters(
            (active_filter,),
            records,
        )
    )

    language_data = count_by_language(filtered_records)

    project_type_data = count_by_project_type(filtered_records)

    pr_nature_data = count_by_pr_nature(filtered_records)

    total_records = _count_total_records(filtered_records)

    render_header()

    render_kpis(
        total_records,
        language_data,
        project_type_data,
    )

    render_main_charts(
        language_data,
        project_type_data,
        pr_nature_data,
    )

    render_description_distributions(
        filtered_records,
    )

    render_footer()
