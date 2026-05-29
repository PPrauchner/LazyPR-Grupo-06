"""
Dashboard principal para visualização do volume de contribuições.

Responsabilidades:
    - Exibir volume de PRs por linguagem
    - Exibir volume por tipo de projeto
    - Exibir volume por natureza da contribuição
    - Organizar o dashboard em containers e colunas
    - Consumir exclusivamente dados previamente agregados
"""

from functools import reduce
from typing import Iterable, Any

import streamlit as st

from core.aggregations.metrics import (
    char_distribution,
    description_stats,
    word_distribution,
)

from core.aggregations.grouping import (
    aggregate_by_language,
    aggregate_by_project_type,
    aggregate_by_pr_nature,
)

from core.transforms.filtering import (
    apply_filters,
)

from ui.sidebar_filters import (
    get_active_filters,
)

from ui.charts import (
    bar_chart_by_category,
    distribution_chart_from_bins,
)

from ui.components import (
    metric_card,
    chart_container_start,
    chart_container_end,
)


def _count_total_records(
    records: Iterable[Any],
) -> int:
    """
    Conta total de registros.
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

    st.title("📊 Overview Pull Requests")

    st.markdown("""
        Visualização agregada das contribuições
        processadas pela pipeline funcional do LazyPR.
        """)


def render_kpis(
    total_records: int,
    language_data: Iterable[Any],
    project_type_data: Iterable[Any],
) -> None:
    """
    Renderiza KPI cards.
    """

    kpi_col1, kpi_col2, kpi_col3 = st.columns(3)

    with kpi_col1:

        metric_card(
            label="Total de PRs",
            value=f"{total_records:,}",
            delta="",
            icon="📦",
            trend_direction="up",
        )

    with kpi_col2:

        metric_card(
            label="Linguagens",
            value=len(language_data),
            delta="",
            icon="💻",
            trend_direction="up",
        )

    with kpi_col3:

        metric_card(
            label="Tipos de Projeto",
            value=len(project_type_data),
            delta="",
            icon="🧩",
            trend_direction="up",
        )


def render_main_charts(
    language_data: Iterable[Any],
    project_type_data: Iterable[Any],
    pr_nature_data: Iterable[Any],
) -> None:
    """
    Renderiza gráficos principais.
    """

    col1, col2 = st.columns(2)

    with col1:

        chart_container_start()

        st.plotly_chart(
            bar_chart_by_category(
                language_data,
                title="PRs por Linguagem",
                x_title="Linguagem",
            ),
            use_container_width=True,
        )

        chart_container_end()

    with col2:

        chart_container_start()

        st.plotly_chart(
            bar_chart_by_category(
                project_type_data,
                title="PRs por Tipo de Projeto",
                x_title="Tipo de Projeto",
            ),
            use_container_width=True,
        )

        chart_container_end()

    chart_container_start()

    st.plotly_chart(
        bar_chart_by_category(
            pr_nature_data,
            title="PRs por Natureza da Contribuição",
            x_title="Natureza",
        ),
        use_container_width=True,
    )

    chart_container_end()


def render_description_distributions(
    records: Iterable[Any],
) -> None:
    """
    Renderiza métricas descritivas.
    """

    stats = description_stats(
        records,
    )

    char_data = char_distribution(
        records,
    )

    word_data = word_distribution(
        records,
    )

    st.subheader("Distribuição de Descrições")

    metric_col1, metric_col2 = st.columns(2)

    with metric_col1:

        metric_card(
            label="Média de Caracteres",
            value=round(stats["char"]["mean"]),
            delta="",
            icon="✏️",
            trend_direction="up",
        )

    with metric_col2:

        metric_card(
            label="Média de Palavras",
            value=round(stats["word"]["mean"]),
            delta="",
            icon="📝",
            trend_direction="up",
        )

    chart_col1, chart_col2 = st.columns(2)

    with chart_col1:

        chart_container_start()

        st.plotly_chart(
            distribution_chart_from_bins(
                char_data,
                dimension="char_count",
            ),
            use_container_width=True,
        )

        chart_container_end()

    with chart_col2:

        chart_container_start()

        st.plotly_chart(
            distribution_chart_from_bins(
                word_data,
                dimension="word_count",
            ),
            use_container_width=True,
        )

        chart_container_end()


def render_footer() -> None:
    """
    Renderiza rodapé.
    """

    st.caption("LazyPR Analytics Platform")


def render_overview(
    records: Iterable[Any],
) -> None:
    """
    Renderiza dashboard overview.
    """

    active_filter = get_active_filters()

    filtered_records = tuple(
    apply_filters(
        active_filter,
        records,
    )
    )
 
    language_data = aggregate_by_language(
        filtered_records,
    )

    project_type_data = aggregate_by_project_type(
        filtered_records,
    )

    pr_nature_data = aggregate_by_pr_nature(
        filtered_records,
    )

    total_records = _count_total_records(
        filtered_records,
    )

    render_header()

    total_records = len(
    filtered_records,
    )

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