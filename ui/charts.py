"""
ui/charts.py
=============
Funções puras de visualização para gráficos interativos
utilizados no dashboard do projeto.

Responsabilidades:
    - Renderizar gráficos categóricos a partir de contagens.
    - Renderizar distribuições estatísticas (histogramas e barras).
    - Renderizar heatmaps de correlação multidimensional.
    - Manter a separação estrita entre a lógica de manipulação de dados e a de apresentação.

Não deve:
    - Realizar agregações, cálculos estatísticos ou mutações nos datasets originais.
    - Acessar o `st.session_state` ou gerenciar estado da aplicação no Streamlit.
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
    Aplica um layout padronizado compartilhado a todas as figuras do Plotly.

    Args:
        figure (go.Figure): O objeto da figura do Plotly a ser formatado.
        title (str): O título principal do gráfico.
        x_title (str): O rótulo a ser exibido no eixo X.
        y_title (str, opcional): O rótulo a ser exibido no eixo Y. Padrão é "Frequência".

    Returns:
        go.Figure: A mesma figura Plotly atualizada com o layout padrão (fundo branco, hover unificado, etc).
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
    Valida se a dimensão solicitada para a plotagem é suportada pela configuração.

    Args:
        dimension (str): A dimensão informada na chamada da função (ex: 'char', 'word').
        valid_dimensions (tuple[str, ...]): Uma tupla contendo as strings das dimensões válidas aceitas.

    Raises:
        ValueError: Se a dimensão fornecida não estiver presente na tupla de dimensões válidas.
    """
    if dimension not in valid_dimensions:
        raise ValueError(
            f"Dimensão inválida: '{dimension}'. Use uma de: {valid_dimensions}"
        )


def add_statistical_lines(
    figure: go.Figure,
    mean: float,
    median: float,
) -> go.Figure:
    """
    Adiciona linhas verticais de referência para a média e a mediana em um histograma.

    Args:
        figure (go.Figure): O objeto da figura do Plotly base.
        mean (float): O valor numérico correspondente à média estatística.
        median (float): O valor numérico correspondente à mediana estatística.

    Returns:
        go.Figure: A figura Plotly enriquecida com as anotações visuais da média (tracejada) e mediana (pontilhada).
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
    Cria um histograma estatístico mostrando a distribuição bruta de métricas textuais.

    Esta função extrai a lista de valores brutos e as medidas de tendência central
    para renderizar um histograma detalhado.

    Args:
        stats (Mapping[str, Any]): Dicionário estruturado com as estatísticas descritivas (saída do agregador).
        dimension (str, opcional): Dimensão alvo da plotagem ("char" ou "word"). Padrão é "char".
        title (str, opcional): Título customizado. Se vazio, utiliza o título padrão definido na configuração.

    Returns:
        go.Figure: Gráfico Plotly renderizado com os bins e as marcações estatísticas.
    """
    validate_dimension(dimension, ("char", "word"))

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
                hovertemplate="Faixa: %{x}<br>Frequência: %{y}<extra></extra>",
            )
        ]
    )

    figure = add_statistical_lines(figure, mean, median)
    return apply_default_layout(figure, title or config["title"], config["x_title"])


def distribution_chart_from_bins(
    data: Mapping[str, int],
    dimension: str,
    title: str = "",
) -> go.Figure:
    """
    Cria um gráfico de barras a partir de dados de distribuição previamente segmentados em faixas (bins).

    Args:
        data (Mapping[str, int]): Dicionário onde a chave é o rótulo da faixa (ex: "0-100") e o valor é a frequência.
        dimension (str): A métrica de origem ("char_count", "word_count", "clarity").
        title (str, opcional): Título customizado para sobrepor o padrão.

    Returns:
        go.Figure: Gráfico de barras verticais simples Plotly com as frequências segmentadas.
    """
    validate_dimension(dimension, ("char_count", "word_count", "clarity"))

    config = BIN_CONFIG[dimension]
    bins = tuple(data.keys())
    frequencies = tuple(data.values())

    figure = go.Figure(
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

    return apply_default_layout(figure, title or config["title"], config["x_title"])


def bar_chart_by_category(
    counts: Mapping[str, int],
    title: str = "",
    x_title: str = "",
    y_title: str = "Frequência",
) -> go.Figure:
    """
    Cria um gráfico de barras categórico simples baseado em dados de contagem.

    Destinado a exibir agregações diretas, como quantidade de PRs por linguagem ou por natureza.

    Args:
        counts (Mapping[str, int]): Dicionário mapeando os nomes das categorias para os totais contabilizados.
        title (str, opcional): O título principal do gráfico. Padrão: "Distribuição por Categoria".
        x_title (str, opcional): O rótulo explicativo do eixo X. Padrão: "Categoria".
        y_title (str, opcional): O rótulo explicativo do eixo Y. Padrão: "Frequência".

    Returns:
        go.Figure: Gráfico de barras categóricas do Plotly formatado para o dashboard.
    """
    categories = tuple(counts.keys())
    values = tuple(counts.values())

    figure = go.Figure(
        data=[
            go.Bar(
                x=categories,
                y=values,
                marker={"color": CHART_COLORS["primary"]},
                text=values,
                textposition="auto",
                hovertemplate="<b>%{x}</b><br>Total: %{y}<extra></extra>",
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
    Renderiza um mapa de calor (heatmap) para explorar visualmente correlações bidimensionais.

    Útil para cruzar categorias como "Linguagem x Nível de Clareza", recebendo uma matriz
    aninhada resultante de contagens combinadas.

    Args:
        matrix (Mapping[str, Mapping[str, int]]): Matriz de dados agregados no formato `{eixo_y: {eixo_x: valor}}`.
        title (str, opcional): Título principal customizável do mapa de calor.

    Returns:
        go.Figure: Gráfico de calor do Plotly preenchido com a intensidade das intersecções de categoria.
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