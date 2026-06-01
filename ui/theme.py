"""
Gerenciamento global de tema visual do LazyPR.
"""

import streamlit as st

THEMES = {
    "dark": {
        "background": "#020817",
        "card": "#111827",
        "border": "#334155",
        "text": "#f8fafc",
        "muted_text": "#cbd5e1",
        "success": "#22c55e",
        "error": "#ef4444",
        "plotly_template": "plotly_dark",
    },
    "light": {
        "background": "#f8fafc",
        "card": "#ffffff",
        "border": "#dbe4ee",
        "text": "#0f172a",
        "muted_text": "#475569",
        "success": "#16a34a",
        "error": "#dc2626",
        "plotly_template": "plotly_white",
    },
}


def initialize_theme() -> None:
    """
    Inicializa tema global da aplicação.
    """

    if "theme_mode" not in st.session_state:

        st.session_state["theme_mode"] = "dark"


def set_theme(
    mode: str,
) -> None:
    """
    Atualiza tema ativo.
    """

    if mode not in THEMES:

        return

    st.session_state["theme_mode"] = mode


def get_theme_mode() -> str:
    """
    Retorna tema ativo.
    """

    return st.session_state.get(
        "theme_mode",
        "dark",
    )


def get_theme() -> dict:
    """
    Retorna tokens do tema ativo.
    """

    return THEMES[get_theme_mode()]


def apply_theme() -> None:
    """
    Aplica CSS do tema ativo.
    """

    theme_mode = get_theme_mode()

    css_path = "ui/styles/dark.css" if theme_mode == "dark" else "ui/styles/light.css"

    with open(
        css_path,
        encoding="utf-8",
    ) as css_file:

        st.markdown(
            f"""
            <style>
            {css_file.read()}
            </style>
            """,
            unsafe_allow_html=True,
        )
