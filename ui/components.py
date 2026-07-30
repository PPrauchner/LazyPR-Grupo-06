"""
Fornece widgets e elementos visuais reutilizáveis do Streamlit.
"""

from typing import Any, Iterable

import streamlit as st

from core.models.analysis_result import (
    AnalysisResult,
)

from services.exporters import (
    to_download_bytes,
)

from ui.theme import (
    get_theme,
)


def metric_card(
    label: str,
    value: Any,
    delta: str = "",
    icon: str = "📊",
    trend_direction: str = "up",
) -> None:
    """
    Renderiza KPI card moderno reutilizável.
    """

    theme = get_theme()

    trend_color = theme["success"] if trend_direction == "up" else theme["error"]

    trend_icon = "↑" if trend_direction == "up" else "↓"

    st.markdown(
        f"""
        <div
            style="
                background: linear-gradient(
                    135deg,
                    {theme['card']},
                    rgba(124,58,237,0.06)
                );
                border: 1px solid {theme['border']};
                border-radius: 18px;
                padding: 1rem;
                margin-bottom: 1rem;
                box-shadow: 0 0 18px rgba(124,58,237,0.08);
                min-height: 140px;
            "
        >

<div
    style="
        display: flex;
        align-items: center;
        justify-content: space-between;
    "
>

<div
    style="
       color: {theme['muted_text']};
       font-size: 0.92rem;
       font-weight: 600;
   "
>
     {icon} {label}
</div>

</div>

<div
    style="
       margin-top: 0.8rem;
       font-size: 2rem;
       font-weight: 800;
       color: {theme['text']};
    "
>
     {value}
</div>

<div
   style="
        margin-top: 0.35rem;
        color: {trend_color};
        font-size: 0.85rem;
        font-weight: 700;
    "
>
     {trend_icon} {delta}
</div>

</div>
""",
        unsafe_allow_html=True,
    )


def chart_container_start() -> None:
    """
    Inicia container reutilizável para gráficos.
    """

    theme = get_theme()

    st.markdown(
        f"""
        <div
            style="
                padding: 1rem;
                border-radius: 20px;
                background: linear-gradient(
                    135deg,
                    {theme['card']},
                    rgba(124,58,237,0.04)
                );
                border: 1px solid {theme['border']};
                box-shadow: 0 0 16px rgba(124,58,237,0.05);
                margin-bottom: 1rem;
                overflow: hidden;
            "
        >
        """,
        unsafe_allow_html=True,
    )


def chart_container_end() -> None:
    """
    Finaliza container visual reutilizável.
    """

    st.markdown(
        """
        </div>
        """,
        unsafe_allow_html=True,
    )


def data_table(
    records: Iterable[AnalysisResult],
) -> None:
    """
    Renderiza tabela interativa de resultados.
    """

    data = tuple(
        map(
            lambda r: r._asdict(),
            records,
        )
    )

    if not data:

        st.info("Nenhum registro encontrado para os filtros atuais.")

        return

    chart_container_start()

    st.dataframe(
        data,
        width="stretch",
    )

    chart_container_end()


def status_banner(
    message: str,
    status_type: str = "info",
) -> None:
    """
    Exibe banner visual de status.
    """

    banners = {
        "success": st.success,
        "error": st.error,
        "warning": st.warning,
        "info": st.info,
    }

    banner_func = banners.get(
        status_type,
        st.info,
    )

    banner_func(message)


def download_buttons(
    results: Iterable[AnalysisResult],
) -> None:
    """
    Renderiza botões de exportação.
    """

    results_tuple = tuple(results)

    chart_container_start()

    col1, col2 = st.columns(2)

    with col1:

        st.download_button(
            label="📥 Baixar CSV",
            data=to_download_bytes(
                results_tuple,
                fmt="csv",
            ),
            file_name="analise_pr.csv",
            mime="text/csv",
            width="stretch",
        )

    with col2:

        st.download_button(
            label="📥 Baixar JSON",
            data=to_download_bytes(
                results_tuple,
                fmt="json",
            ),
            file_name="analise_pr.jsonl",
            mime="application/json",
            width="stretch",
        )

    chart_container_end()
