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
    dataset_name: str,
    total_records: int,
) -> None:
    """
    Renderiza card compacto do dataset carregado.
    """

    card_html = f"""
    <div
        style="
            padding: 1rem;
            border-radius: 16px;
            border: 1px solid rgba(34,197,94,0.20);
            background: linear-gradient(
                135deg,
                rgba(34,197,94,0.08),
                rgba(15,23,42,0.45)
            );
            margin-top: 0.8rem;
            box-shadow: 0 0 16px rgba(34,197,94,0.08);
        "
    >

    <div
      style="
                display: flex;
                align-items: center;
                gap: 0.45rem;
                color: #4ade80;
                font-size: 0.82rem;
                font-weight: 700;
                margin-bottom: 0.6rem;
        "
        >
            ● Dataset carregado
    </div>

    <div
     style="
                font-size: 0.85rem;
                font-weight: 600;
                color: #f8fafc;
                overflow: hidden;
                text-overflow: ellipsis;
                white-space: nowrap;
    "
        >
            {dataset_name}
    </div>

    <div
     style="
                margin-top: 0.45rem;
                font-size: 0.76rem;
                color: #cbd5e1;
        "
        >
            {total_records:,} registros
    </div>
    """

    st.markdown(
        card_html,
        unsafe_allow_html=True,
    )
