"""
Dashboard principal para visualização do volume de contribuições.

Esta página apresenta gráficos interativos construídos com
Streamlit e Plotly para análise agregada dos pull requests.
As visualizações são alimentadas exclusivamente por funções
puras do módulo core/aggregations.

Responsabilidades:
- Exibir volume de PRs por linguagem
- Exibir volume por tipo de projeto
- Exibir volume por natureza da contribuição
- Renderizar distribuições gerais do dataset
- Consumir apenas dados previamente agregados
"""

import streamlit as st

from core.aggregations.counters import (
    count_by_language,
    count_by_project_type,
    count_by_pr_nature,
)

from ui.charts import bar_chart_by_category


def render_overview(records):

    st.title("Overview de Pull Requests")

    # =========================
    # AGREGAÇÕES FUNCIONAIS
    # =========================

    language_data = count_by_language(records)

    project_type_data = count_by_project_type(records)

    pr_nature_data = count_by_pr_nature(records)

    # =========================
    # GRÁFICOS
    # =========================

    st.plotly_chart(
        bar_chart_by_category(language_data, "PRs por Linguagem"),
        use_container_width=True,
    )

    st.plotly_chart(
        bar_chart_by_category(project_type_data, "PRs por Tipo de Projeto"),
        use_container_width=True,
    )

    st.plotly_chart(
        bar_chart_by_category(pr_nature_data, "PRs por Natureza"),
        use_container_width=True,
    )
