"""
pages/export.py
==================
Camada de apresentação final para exportação dos resultados enriquecidos.

Responsabilidades:
    - Exibir KPIs de resumo da análise (total de PRs, clareza alta).
    - Renderizar prévia dos dados via `ui/components.data_table()`.
    - Disponibilizar botões de download CSV e JSON via `ui/components.download_buttons()`.
    - Ler exclusivamente de `st.session_state["results"]` — nunca acessar o dataset bruto.

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
from ui.components import data_table, download_buttons, metric_card

st.set_page_config(page_title="LazyPR - Exportar", page_icon="💾")


def render() -> None:
    """Orquestra a renderização da página de exportação.

    Lê os resultados de `st.session_state["results"]`, materializa em tupla
    imutável para permitir múltiplos consumos (KPIs, tabela e download), e
    delega cada seção ao componente correspondente de `ui/components.py`.

    Interrompe a execução com `st.stop()` quando nenhum dado processado
    estiver disponível na sessão, orientando o usuário ao fluxo correto.

    Returns:
        None: Função de efeito colateral — renderiza no Streamlit.
    """
    st.title("💾 Exportar Resultados")

    if "results" not in st.session_state or not st.session_state["results"]:
        st.warning(
            "Nenhum dado processado disponível. "
            "Por favor, retorne à página de Upload e inicie uma análise."
        )
        st.stop()

    results = tuple(st.session_state["results"])

    st.subheader("Resumo do Arquivo")
    col1, col2, _ = st.columns(3)

    with col1:
        metric_card("Total de PRs", len(results))

    with col2:
        clarity_counts = count_by(results, lambda r: r.clarity_level)
        metric_card("Clareza Alta", clarity_counts.get("excellent", 0))

    st.divider()

    st.subheader("Prévia dos Dados")
    data_table(results)

    st.divider()

    st.subheader("Opções de Download")
    download_buttons(results)


render()