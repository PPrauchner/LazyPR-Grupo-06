"""
Helpers visuais reutilizáveis de layout.
"""

import streamlit as st

from ui.theme import (
    get_theme,
)


def render_section_title(
    title: str,
) -> None:
    """
    Renderiza título de seção da sidebar.
    """

    st.markdown(
        f"""
        <div
            style="
                margin-top: 1rem;
                margin-bottom: 0.5rem;
                font-size: 0.85rem;
                font-weight: 700;
                opacity: 0.8;
                letter-spacing: 0.05rem;
            "
        >
            {title}
        </div>
        """,
        unsafe_allow_html=True,
    )


def render_dataset_card(
    filename: str,
    total_records: int,
) -> None:
    """
    Renderiza card visual do dataset carregado.
    """

    theme = get_theme()

    st.markdown(
        f"""
<div
    style="
        width: 100%;
        box-sizing: border-box;
        padding: 0.8rem;
        border-radius: 16px;
        border: 1px solid {theme['border']};
        background-color: {theme['card']};
        margin-top: 1rem;
        margin-bottom: 1rem;
    "
>
    <div
        style="
            font-size: 0.85rem;
            opacity: 0.7;
            color: {theme['muted_text']};
        "
    >
        DATASET CARREGADO
    </div>

    <div
        style="
            margin-top: 0.5rem;
            font-weight: 600;
            font-size: 1rem;
            theme['sidebar_text'];
        "
    >
        📂 {filename}
    </div>

    <div
        style="
            margin-top: 0.5rem;
            opacity: 0.8;
            font-size: 0.9rem;
            color: {theme['muted_text']};
        "
    >
        📊 {total_records} registros analisados
    </div>
</div>
        """,
        unsafe_allow_html=True,
    )
