"""
views/export.py
==================
Camada de apresentação final para exportação dos resultados enriquecidos.

Responsabilidades:
    - Exibir KPIs de resumo da análise (total de PRs, clareza alta).
    - Renderizar prévia dos dados via `ui/components.data_table()`.
    - Disponibilizar botões de download CSV e JSON via `ui/components.download_buttons()`.
    -Recebe os resultados processados via parâmetro, materializando em tupla imutável para múltiplos consumos.

Não deve:
    - Realizar contagens, agregações ou transformações de dados diretamente.
    - Chamar LLMs, pipeline ou I/O de arquivo.

Relacionado a:
    - Issue 09 (exportação de resultados em CSV e JSON)
    - HU 09 (exportar resultados para uso em outras ferramentas)
    - Regra Geral 08 (interface gráfica obrigatória)
"""

import streamlit as st

from core.aggregations.counters import count_by
from ui.components import data_table, download_buttons, metric_card, status_banner


def render_export_page(records=None) -> None:
    """
    Renderiza a página de exportação.

    Args:
        records: Análise já recortada pelo Filtro de Visualização em main.py
            (ADR-0003) — a página não reaplica o recorte.
    """

    st.title("💾 Exportar Resultados")

    # Recebe a Análise já recortada pelo Filtro de Visualização (ADR 0003);
    # ler st.session_state aqui exportaria o conjunto inteiro, ignorando a
    # sidebar.
    results = tuple(records or ())

    # A guarda verifica o que a página de fato exporta. Sem Análise carregada e
    # recorte vazio são situações distintas: só a segunda se resolve na sidebar.
    if not results:

        if st.session_state.get("analysis_results"):

            status_banner(
                "O Filtro de Visualização atual não casou com nenhum PR. "
                "Ajuste ou limpe os filtros na barra lateral para exportar.",
                status_type="info",
            )

        else:

            status_banner(
                "Nenhum dado processado disponível. "
                "Por favor, retorne à página de Upload e inicie uma análise.",
                status_type="warning",
            )

        st.stop()
        return

    st.subheader("Resumo do Arquivo")

    col1, col2, _ = st.columns(3)

    with col1:
        metric_card(
            "Total de PRs",
            len(results),
        )

    with col2:

        clarity_counts = count_by(
            results,
            lambda r: r.clarity_level,
        )

        metric_card(
            "Clareza Alta",
            clarity_counts.get(
                "excellent",
                0,
            ),
        )

    st.divider()

    st.subheader("Prévia dos Dados")

    data_table(results)

    st.divider()

    st.subheader("Opções de Download")

    download_buttons(results)
