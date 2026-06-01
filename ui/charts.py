"""
Funções puras de visualização para gráficos interativos
utilizados no dashboard do projeto.

Responsabilidades:
    - Renderizar gráficos categóricos a partir de contagens.
    - Renderizar distribuições estatísticas.
    - Renderizar heatmaps de correlação multidimensional.
    - Aplicar tema visual global aos gráficos.
    - Manter separação entre visualização e agregação.

Não deve:
    - Realizar agregações.
    - Mutar datasets.
    - Acessar session_state diretamente.
"""

from typing import Any, Mapping

import plotly.graph_objects as go

from ui.theme import (
    get_theme,
)

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
    Aplica layout padrão baseado no tema ativo.
    """

    theme = get_theme()

    figure.update_layout(
        title=title,
        xaxis_title=x_title,
        yaxis_title=y_title,
        hovermode="x unified",
        showlegend=False,
        template=theme["plotly_template"],
        paper_bgcolor=theme["background"],
        plot_bgcolor=theme["card"],
        font={
            "color": theme["text"],
        },
        margin=dict(
            l=0,
            r=0,
            t=40,
            b=0,
        ),
        hoverlabel=dict(
            bgcolor=theme["card"],
            bordercolor=theme["border"],
            font_size=13,
        ),
    )

    figure.update_xaxes(
        showgrid=True,
        gridcolor="rgba(128,128,128,0.10)",
        zeroline=False,
    )

    figure.update_yaxes(
        showgrid=True,
        gridcolor="rgba(128,128,128,0.10)",
        zeroline=False,
    )

    return figure


def validate_dimension(
    dimension: str,
    valid_dimensions: tuple[str, ...],
) -> None:
    """
    Valida dimensões suportadas.
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
    Adiciona linhas de média e mediana.
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
    Cria histograma estatístico.
    """

    validate_dimension(
        dimension,
        ("char", "word"),
    )

    config = DISTRIBUTION_CONFIG[dimension]

    dimension_stats = stats[dimension]

    values = dimension_stats.get(
        "values",
        (),
    )

    mean = dimension_stats.get(
        "mean",
        0,
    )

    median = dimension_stats.get(
        "median",
        0,
    )

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

    figure = apply_default_layout(
        figure,
        title or config["title"],
        config["x_title"],
    )

    return figure


def distribution_chart_from_bins(
    data: Mapping[str, int],
    dimension: str,
    title: str = "",
) -> go.Figure:
    """
    Cria gráfico de barras baseado em bins.
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

    figure = apply_default_layout(
        figure,
        title or config["title"],
        config["x_title"],
    )

    return figure


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

    figure = apply_default_layout(
        figure,
        title or "Distribuição por Categoria",
        x_title or "Categoria",
        y_title,
    )

    return figure


def correlation_heatmap(
    matrix: Mapping[str, Mapping[str, int]],
    title: str = "",
) -> go.Figure:
    """
    Cria heatmap multidimensional.
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

    figure = apply_default_layout(
        figure,
        title or "Correlação Multidimensional",
        "Categoria",
        "Nível de Clareza",
    )

    return figure
