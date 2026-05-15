"""
Funções puras de visualização para gráficos interativos
utilizados no dashboard do projeto.

Responsabilidades:
    - Renderizar gráficos categóricos
    - Renderizar distribuições estatísticas
    - Renderizar heatmaps de correlação
    - Manter separação entre dados e apresentação

Não deve:
    - Realizar agregações
    - Modificar datasets
    - Acessar Streamlit diretamente
"""

from typing import Any, Mapping

import plotly.graph_objects as go

CHART_COLORS = {
    "primary": "#636EFA",
    "secondary": "#EF553B",
    "success": "#00CC96",
    "mean": "#BA7517",
    "median": "#3B6D11",
}


DISTRIBUTION_CONFIG = {
    "char": {
        "title": "Distribuição de Caracteres por Comentário",
        "x_title": "Número de Caracteres",
        "color": CHART_COLORS["primary"],
    },
    "word": {
        "title": "Distribuição de Palavras por Comentário",
        "x_title": "Número de Palavras",
        "color": CHART_COLORS["secondary"],
    },
}

BIN_CONFIG = {
    "char_count": {
        "title": "Distribuição de Caracteres (bins)",
        "x_title": "Faixa de Caracteres",
        "color": CHART_COLORS["primary"],
    },
    "word_count": {
        "title": "Distribuição de Palavras (bins)",
        "x_title": "Faixa de Palavras",
        "color": CHART_COLORS["secondary"],
    },
    "clarity": {
        "title": "Distribuição de Clareza",
        "x_title": "Nível de Clareza",
        "color": CHART_COLORS["success"],
    },
}


def apply_default_layout(
    figure: go.Figure,
    title: str,
    x_title: str,
    y_title: str = "Frequência",
) -> go.Figure:
    """
    Aplica layout padrão compartilhado entre gráficos.
    """

    figure.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode="x unified",
        showlegend=False,
        template="plotly_white",
    )

    return figure


def validate_dimension(
    dimension: str,
    valid_dimensions: tuple[str, ...],
) -> None:
    """
    Valida dimensão utilizada nos gráficos.
    """

    if dimension not in valid_dimensions:

        raise ValueError(
            f"Dimensão inválida: '{dimension}'. " f"Use uma de: {valid_dimensions}"
        )


def add_statistical_lines(
    figure: go.Figure,
    mean: float,
    median: float,
) -> go.Figure:
    """
    Adiciona linhas estatísticas ao histograma.
    """

    figure.add_vline(
        x=mean,
        line_dash="dash",
        line_color=CHART_COLORS["mean"],
        annotation_text=f"Média: {mean:.1f}",
        annotation_position="top right",
    )

    figure.add_vline(
        x=median,
        line_dash="dot",
        line_color=CHART_COLORS["median"],
        annotation_text=f"Mediana: {median:.1f}",
        annotation_position="top left",
    )

    return figure


def distribution_chart(
    stats: Mapping[str, Any],
    dimension: str = "char",
    title: str = "",
) -> go.Figure:
    """
    Cria histograma estatístico de distribuição.
    """

    validate_dimension(
        dimension,
        ("char", "word"),
    )

    config = DISTRIBUTION_CONFIG[dimension]

    dimension_stats = stats[dimension]

    values = dimension_stats.get("values", ())
    mean = dimension_stats.get("mean", 0)
    median = dimension_stats.get("median", 0)

    figure = go.Figure(
        data=[
            go.Histogram(
                x=values,
                nbinsx=40,
                marker={
                    "color": config["color"],
                    "opacity": 0.85,
                },
                hovertemplate=("Faixa: %{x}" "<br>Frequência: %{y}" "<extra></extra>"),
            )
        ]
    )

    figure = add_statistical_lines(
        figure,
        mean,
        median,
    )

    return apply_default_layout(
        figure,
        title or config["title"],
        config["x_title"],
    )


def distribution_chart_from_bins(
    data: Mapping[str, int],
    dimension: str,
    title: str = "",
) -> go.Figure:
    """
    Cria gráfico de barras para distribuições
    previamente agrupadas em bins.
    """

    validate_dimension(
        dimension,
        ("char_count", "word_count", "clarity"),
    )

    config = BIN_CONFIG[dimension]

    bins = tuple(data.keys())
    frequencies = tuple(data.values())

    figure = go.Figure(
        data=[
            go.Bar(
                x=bins,
                y=frequencies,
                marker={
                    "color": config["color"],
                },
                text=frequencies,
                textposition="auto",
                hovertemplate=("<b>%{x}</b>" "<br>Frequência: %{y}" "<extra></extra>"),
            )
        ]
    )

    return apply_default_layout(
        figure,
        title or config["title"],
        config["x_title"],
    )


def bar_chart_by_category(
    counts: Mapping[str, int],
    title: str = "",
    x_title: str = "",
    y_title: str = "Frequência",
) -> go.Figure:
    """
    Cria gráfico de barras categórico.
    """

    categories = tuple(counts.keys())
    values = tuple(counts.values())

    figure = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker={
                    "color": CHART_COLORS["primary"],
                },
                text=values,
                textposition="auto",
                hovertemplate=("<b>%{x}</b>" "<br>Total: %{y}" "<extra></extra>"),
            )
        ]
    )

    return apply_default_layout(
        figure,
        title or "Distribuição por Categoria",
        x_title or "Categoria",
        y_title,
    )


def correlation_heatmap(
    matrix: Mapping[str, Mapping[str, int]],
    title: str = "",
) -> go.Figure:
    """
    Cria heatmap multidimensional para análise
    de correlação entre categorias.
    """

    y_labels = tuple(matrix.keys())

    x_labels = tuple({column for row in matrix.values() for column in row.keys()})

    z_values = tuple(
        tuple(matrix[row].get(column, 0) for column in x_labels) for row in y_labels
    )

    figure = go.Figure(
        data=go.Heatmap(
            z=z_values,
            x=x_labels,
            y=y_labels,
            colorscale="Blues",
            hoverongaps=False,
        )
    )

    figure.update_layout(
        title=title or "Correlação Multidimensional",
        xaxis_title="Categoria",
        yaxis_title="Nível de Clareza",
        template="plotly_white",
    )

    return figure

