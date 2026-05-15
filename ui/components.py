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
    """
    Exibe banner de status (progresso, sucesso, erro).
    Utiliza Dispatch Table (Dicionário) para evitar if/else longos (Clean Code).
    """
    banners = {
        "success": st.success,
        "error": st.error,
        "warning": st.warning,
        "info": st.info
    }
    
    # Busca a função correspondente, se não existir cai no fallback (st.info)
    banner_func = banners.get(status_type, st.info)
    banner_func(message)


def download_buttons(results: Iterable[AnalysisResult]) -> None:
    """Renderiza botões de download para CSV e JSON no dashboard."""
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
            file_name="analise_prs.jsonl",
            mime="application/json",
        )
