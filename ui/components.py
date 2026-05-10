"""
ui/components.py
=================
Fornece widgets e elementos visuais reutilizáveis do Streamlit que
encapsulam padrões de exibição comuns ao longo do dashboard.

Responsabilidades:
    - Implementar `metric_card(label, value, delta)` para exibição de
      KPIs de alto nível (total de PRs, distribuição de clareza, etc.).
    - Implementar `data_table(records, columns)` para renderização
      interativa de subconjuntos do dataset filtrado com paginação.
    - Implementar `status_banner(message, type)` para feedback visual
      de progresso do pipeline (ingestão, classificação, exportação).
    - Implementar `download_buttons(results)` que integra com
      `exporters.py` para oferecer botões de download CSV e JSON
      diretamente na interface.
    - Todos os componentes devem receber dados já processados como
      argumento — nenhuma lógica de transformação ou acesso a estado
      global dentro deste módulo.

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
from typing import Iterable
from core.models.analysis_result import AnalysisResult
from services.exporters import to_download_bytes


def status_banner(message: str, status_type: str = "info") -> None:
    """Exibe um banner de status (progresso, sucesso, erro) na interface.

    Utiliza o padrão Dispatch Table (dicionário de funções) para evitar
    estruturas condicionais longas (if/else), mantendo o código limpo, 
    declarativo e alinhado a boas práticas.

    Args:
        message (str): A mensagem descritiva a ser exibida no banner.
        status_type (str): O nível/tipo do alerta. Valores suportados:
            "success", "error", "warning" ou "info". Padrão: "info".

    Returns:
        None: A função atua apenas causando efeito colateral na interface
        do Streamlit (renderização).

    Exemplo:
        >>> status_banner("Dataset carregado com sucesso!", status_type="success")
        >>> status_banner("Colunas obrigatórias ausentes.", status_type="error")
    """
    banners = {
        "success": st.success,
        "error": st.error,
        "warning": st.warning,
        "info": st.info
    }
    
    banner_func = banners.get(status_type, st.info)
    banner_func(message)


def download_buttons(results: Iterable[AnalysisResult]) -> None:
    """Renderiza botões de download interativos para os resultados da análise.

    Delega a lógica de serialização para `to_download_bytes()` do módulo
    `exporters`, mantendo em memória os dados transformados em CSV/JSON
    sem gravação intermediária em disco, preservando a pureza I/O onde possível.

    Args:
        results (Iterable[AnalysisResult]): Coleção imutável de resultados
            já classificados e enriquecidos pelo pipeline do sistema.

    Returns:
        None: Modifica apenas a renderização do Streamlit injetando colunas e botões.

    Exemplo:
        >>> registros_processados = (AnalysisResult(...), AnalysisResult(...))
        >>> download_buttons(registros_processados)
    """
    col1, col2 = st.columns(2)
    
    with col1:
        st.download_button(
            label="📥 Baixar CSV",
            data=to_download_bytes(results, fmt="csv"),
            file_name="analise_prs.csv",
            mime="text/csv",
        )

    with col2:
        st.download_button(
            label="📥 Baixar JSON",
            data=to_download_bytes(results, fmt="json"),
            file_name="analise_prs.json",
            mime="application/json",
        )