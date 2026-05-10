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
import plotly.graph_objects as go
import plotly.express as px


def distribution_chart(
    stats: dict, dimension: str = "char", title: str = ""
) -> go.Figure:
    """Renderiza um histograma a partir da saída de `metrics.description_stats()`.

    Exibe a distribuição bruta de valores para `char_count` ou `word_count`
    com linhas verticais de referência para a média e a mediana.

    Args:
        stats (dict): Dicionário retornado por `metrics.description_stats()`,
            com a estrutura::

                {
                    "char": {"min", "max", "mean", "median", "values": tuple},
                    "word": {"min", "max", "mean", "median", "values": tuple},
                    "total_records": int
                }

        dimension (str): Métrica a plotar — "char" para contagem de caracteres,
            "word" para contagem de palavras. Padrão: "char".
        title (str): Título customizado opcional. Quando vazio, um título
            padrão baseado na dimensão é utilizado.

    Returns:
        go.Figure: Figura Plotly com histograma e duas linhas verticais
        marcando a média (tracejada) e a mediana (pontilhada).

    Raises:
        ValueError: Se `dimension` não for "char" ou "word".
        KeyError: Se `stats` não contiver a estrutura esperada.

    Exemplo:
        >>> stats = description_stats(results)
        >>> fig = distribution_chart(stats, dimension="char")
        >>> st.plotly_chart(fig)
    """
    if dimension not in ("char", "word"):
        raise ValueError(
            f"Dimensão inválida: '{dimension}'. Use 'char' ou 'word'."
        )

    dimension_config = {
        "char": {
            "title": title or "Distribuição de Caracteres por Comentário",
            "x_title": "Número de Caracteres",
            "color": "#636EFA",
        },
        "word": {
            "title": title or "Distribuição de Palavras por Comentário",
            "x_title": "Número de Palavras",
            "color": "#EF553B",
        },
    }

    config = dimension_config[dimension]
    dim_stats = stats[dimension]

    values = dim_stats.get("values", ())
    mean   = dim_stats.get("mean", 0)
    median = dim_stats.get("median", 0)

    fig = go.Figure(
        data=[
            go.Histogram(
                x=values,
                nbinsx=40,
                marker={"color": config["color"], "opacity": 0.85},
                hovertemplate="Faixa: %{x}<br>Frequência: %{y}<extra></extra>",
            )
        ]
    )

    fig.add_vline(
        x=mean,
        line_dash="dash",
        line_color="#BA7517",
        annotation_text=f"Média: {mean:.1f}",
        annotation_position="top right",
    )

    fig.add_vline(
        x=median,
        line_dash="dot",
        line_color="#3B6D11",
        annotation_text=f"Mediana: {median:.1f}",
        annotation_position="top left",
    )

    fig.update_layout(
        title=config["title"],
        xaxis_title=config["x_title"],
        yaxis_title="Frequência",
        hovermode="x unified",
        showlegend=False,
        template="plotly_white",
    )

    return fig


def distribution_chart_from_bins(
    data: dict, dimension: str, title: str = ""
) -> go.Figure:
    """Renderiza um gráfico de barras a partir de dados de frequência já agrupados em bins.

    Alternativa a `distribution_chart()` para quando os dados já foram
    agrupados por `metrics.char_distribution()` ou `metrics.word_distribution()`.

    Args:
        data (dict): Dicionário mapeando rótulos de bin a contagens de frequência —
            saída de `char_distribution()` ou `word_distribution()`.
            Exemplo: {"0-100": 15, "100-200": 42, "200-500": 31, "500+": 8}
        dimension (str): Determina rótulos de eixo e título padrão. Deve ser um
            de: "char_count", "word_count" ou "clarity".
        title (str): Título customizado opcional.

    Returns:
        go.Figure: Figura Plotly com gráfico de barras, uma barra por bin.

    Raises:
        ValueError: Se `dimension` não for um dos valores aceitos.

    Exemplo:
        >>> bins = char_distribution(results)
        >>> fig = distribution_chart_from_bins(bins, dimension="char_count")
        >>> st.plotly_chart(fig)
    """
    valid_dimensions = ("char_count", "word_count", "clarity")
    if dimension not in valid_dimensions:
        raise ValueError(
            f"Dimensão inválida: '{dimension}'. Use um de: {valid_dimensions}"
        )

    dimension_config = {
        "char_count": {
            "title": title or "Distribuição de Caracteres (bins)",
            "x_title": "Faixa de Caracteres",
            "color": "#636EFA",
        },
        "word_count": {
            "title": title or "Distribuição de Palavras (bins)",
            "x_title": "Faixa de Palavras",
            "color": "#EF553B",
        },
        "clarity": {
            "title": title or "Distribuição de Clareza",
            "x_title": "Nível de Clareza",
            "color": "#00CC96",
        },
    }

    config = dimension_config[dimension]
    bins = tuple(data.keys())
    frequencies = tuple(data.values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=bins,
                y=frequencies,
                marker={"color": config["color"]},
                text=frequencies,
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Frequência: %{y}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=config["title"],
        xaxis_title=config["x_title"],
        yaxis_title="Frequência",
        hovermode="x unified",
        showlegend=False,
        template="plotly_white",
    )

    return fig


def bar_chart_by_category(
    counts: dict,
    title: str = "",
    x_title: str = "",
    y_title: str = "Frequência",
) -> go.Figure:
    """Renderiza um gráfico de barras para contagens de frequência por categoria.

    Aceita dados pré-agregados de qualquer função de contagem em
    `core/aggregations/counters.py` e produz um gráfico de barras com
    uma barra por categoria.

    Args:
        counts (dict): Dicionário mapeando rótulos de categoria a contagens.
            Exemplo: {"Python": 120, "JavaScript": 85, "Go": 45}
        title (str): Título do gráfico. Padrão: "Distribuição por Categoria".
        x_title (str): Rótulo do eixo X. Padrão: "Categoria".
        y_title (str): Rótulo do eixo Y. Padrão: "Frequência".

    Returns:
        go.Figure: Figura Plotly com gráfico de barras verticais.

    Exemplo:
        >>> counts = count_by_language(results)
        >>> fig = bar_chart_by_category(counts, title="PRs por Linguagem")
        >>> st.plotly_chart(fig)
    """
    categories = tuple(counts.keys())
    values = tuple(counts.values())

    fig = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker={"color": "#636EFA"},
                text=values,
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>",
            )
        ]
    )

    fig.update_layout(
        title=title or "Distribuição por Categoria",
        xaxis_title=x_title or "Categoria",
        yaxis_title=y_title,
        hovermode="x unified",
        showlegend=False,
        template="plotly_white",
    )

    return fig


def correlation_heatmap(matrix: dict, title: str = "") -> go.Figure:
    """Renderiza um heatmap para dados de correlação multidimensional.

    Destinado a visualizar a relação entre nível de clareza, tipo de projeto
    e linguagem de programação, conforme produzido por `metrics.correlation_summary()`.

    Nota:
        Implementação completa pendente da Issue #07. A função retorna
        atualmente uma figura placeholder para que as páginas de UI dependentes
        possam ser desenvolvidas sem bloqueio.

    Args:
        matrix (dict): Dados de correlação entre dimensões, conforme retornado
            por `metrics.correlation_summary()`.
        title (str): Título customizado opcional.

    Returns:
        go.Figure: Figura Plotly (placeholder até a Issue #07).
    """
    fig = go.Figure()
    fig.add_annotation(
        text="Heatmap de correlação — a ser implementado na Issue #07",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font={"size": 14, "color": "#888"},
    )
    fig.update_layout(
        title=title or "Correlação Multidimensional",
        template="plotly_white",
    )

    return fig
