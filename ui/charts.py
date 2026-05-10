"""
ui/charts.py
=============
Fornece funções de plotagem que transformam estruturas de dados agregadas
em figuras interativas, mantendo a separação entre lógica de dados e
lógica de apresentação.

Responsabilidades:
    - Implementar `bar_chart_by_category(counts, x, y, color)` para
      visualizar a distribuição de PRs por linguagem, tipo e natureza
      (Issue 05), usando Plotly ou Altair.
    - Implementar `distribution_chart(stats, dimension)` para exibir
      histogramas e boxplots de `char_count` e `word_count` estratificados
      por categoria (Issue 06).
    - Implementar `correlation_heatmap(matrix)` para visualizar a relação
      entre clareza, tipo de projeto e linguagem (Issue 07).
    - Cada função recebe exclusivamente dados já agregados (saídas de
      `core/aggregations/`) e retorna um objeto de figura — nunca acessa
      o dataset bruto ou chama funções de transformação.
    - Suportar o tema do Streamlit (light/dark) de forma consistente.

Não deve:
    - Realizar agregações, contagens ou cálculos estatísticos.
    - Acessar `st.session_state` ou gerenciar estado da aplicação.

Relacionado a:
    - Issue 05 (gráficos de volume estratificado)
    - Issue 06 (visualização de distribuição de tamanho)
    - Issue 07 (gráfico de correlação multidimensional)
    - HU 05, 06, 07 (visualizações interativas)
"""

import pandas as pd
import plotly.express as px


def bar_chart_by_category(data: dict, title: str):
    """
    Cria gráfico de barras a partir de dados agregados.
    """

    df = pd.DataFrame(
        {"Categoria": list(data.keys()), "Quantidade": list(data.values())}
    )

    fig = px.bar(df, x="Categoria", y="Quantidade", title=title)

    return fig
