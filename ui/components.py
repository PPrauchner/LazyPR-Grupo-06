"""
ui/components.py
=================
Fornece widgets e elementos visuais reutilizáveis do Streamlit que
encapsulam padrões de exibição comuns ao longo do dashboard.

Responsabilidades:
    - Implementar `metric_card(label, value, delta)` para exibição de
      KPIs de alto nível (total de PRs, distribuição de clareza, etc.).
    - Implementar `data_table(records)` para renderização interativa de
      subconjuntos do dataset filtrado.
    - Implementar `status_banner(message, status_type)` para feedback visual
      de progresso do pipeline (ingestão, classificação, exportação).
    - Implementar `download_buttons(results)` que integra com `exporters.py`
      para oferecer botões de download CSV e JSON diretamente na interface.
    - Todos os componentes devem receber dados já processados como argumento —
      nenhuma lógica de transformação ou acesso a estado global dentro deste módulo.

Não deve:
    - Chamar o pipeline, LLMs ou funções de agregação diretamente.
    - Compartilhar estado mutável entre componentes.

Relacionado a:
    - Issue 05, 06, 07 (visualizações do dashboard)
    - Issue 09 (botões de download)
    - HU 09 (exportação acessível pela interface)
    - Regra Geral 08 (interface gráfica obrigatória)
"""
import streamlit as st
from typing import Any, Iterable

from core.models.analysis_result import AnalysisResult
from services.exporters import to_download_bytes


def metric_card(label: str, value: Any, delta: Any = None) -> None:
    """Renderiza um cartão de métrica (KPI) de alto nível na interface.

    Args:
        label (str): Título ou descrição da métrica exibida.
        value (Any): Valor numérico ou textual exibido em destaque.
        delta (Any, opcional): Indicador de variação positivo ou negativo.
            Quando positivo, exibido em verde; quando negativo, em vermelho.

    Returns:
        None: Função de efeito colateral — renderiza no Streamlit.
    """
    st.metric(label=label, value=value, delta=delta)


def data_table(records: Iterable[AnalysisResult]) -> None:
    """Renderiza uma tabela interativa para visualização dos registros filtrados.

    Converte o iterável de NamedTuples em dicionários via `map()` e materializa
    em tupla imutável, necessário pois `st.dataframe` exige uma estrutura
    completamente indexável para renderização.

    Args:
        records (Iterable[AnalysisResult]): Registros enriquecidos a exibir.

    Returns:
        None: Função de efeito colateral — renderiza no Streamlit.
    """
    data = tuple(map(lambda r: r._asdict(), records))

    if not data:
        st.info("Nenhum registro encontrado para os filtros atuais.")
        return

    st.dataframe(data, use_container_width=True)


def status_banner(message: str, status_type: str = "info") -> None:
    """Exibe um banner de status colorido na interface do Streamlit.

    Utiliza dispatch table (dicionário de funções) para mapear o tipo de
    status à função de alerta correspondente, evitando estruturas condicionais
    longas e mantendo o código declarativo.

    Args:
        message (str): Mensagem descritiva a ser exibida no banner.
        status_type (str): Nível visual do alerta. Valores aceitos:
            "success", "error", "warning" ou "info". Padrão: "info".
            Valores não reconhecidos fazem fallback para "info".

    Returns:
        None: Função de efeito colateral — renderiza no Streamlit.

    Exemplo:
        >>> status_banner("Dataset carregado com sucesso!", status_type="success")
        >>> status_banner("Colunas obrigatórias ausentes.", status_type="error")
    """
    banners = {
        "success": st.success,
        "error": st.error,
        "warning": st.warning,
        "info": st.info,
    }

    banner_func = banners.get(status_type, st.info)
    banner_func(message)


def download_buttons(results: Iterable[AnalysisResult]) -> None:
    """Renderiza botões de download para CSV e JSON dos resultados da análise.

    Materializa o iterável em tupla imutável antes das chamadas de serialização,
    pois `results` pode ser um gerador e seria exaurido após a primeira chamada
    a `to_download_bytes`, resultando em um segundo arquivo vazio.

    A serialização é delegada a `to_download_bytes()` de `services/exporters.py`,
    mantendo a camada de UI livre de lógica de I/O.

    Args:
        results (Iterable[AnalysisResult]): Registros enriquecidos a exportar.
            Pode ser qualquer iterável, incluindo geradores de uso único.

    Returns:
        None: Função de efeito colateral — renderiza no Streamlit.

    Exemplo:
        >>> download_buttons(tuple(st.session_state["results"]))
    """
    results_tuple = tuple(results)

    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="📥 Baixar CSV",
            data=to_download_bytes(results_tuple, fmt="csv"),
            file_name="analise_pr.csv",
            mime="text/csv",
            use_container_width=True,
        )

    with col2:
        st.download_button(
            label="📥 Baixar JSON",
            data=to_download_bytes(results_tuple, fmt="json"),
            file_name="analise_pr.jsonl",
            mime="application/json",
            use_container_width=True,
        )