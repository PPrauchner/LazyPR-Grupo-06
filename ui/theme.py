"""
Sistema global de temas do LazyPR.

Responsabilidades:
    - Centralizar paletas visuais
    - Aplicar CSS global
    - Gerenciar dark/light mode
    - Fornecer configurações visuais reutilizáveis
"""

from pathlib import Path

import streamlit as st

DARK_THEME = {
    "mode": "dark",
    "background": "#0B1120",
    "card": "#121A2B",
    "text": "#F3F4F6",
    "sidebar_text": "#F3F4F6",
    "muted_text": "#9CA3AF",
    "primary": "#7C3AED",
    "secondary": "#06B6D4",
    "border": "#1F2937",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "plotly_template": "plotly_dark",
}


LIGHT_THEME = {
    "mode": "light",
    "background": "#F8FAFC",
    "card": "#FFFFFF",
    "text": "#111827",
    "sidebar_text": "#111827",
    "muted_text": "#6B7280",
    "primary": "#7C3AED",
    "secondary": "#0891B2",
    "border": "#E5E7EB",
    "success": "#10B981",
    "warning": "#F59E0B",
    "error": "#EF4444",
    "plotly_template": "plotly_white",
}


def get_theme() -> dict:
    """
    Retorna tema atualmente ativo.
    """

    theme_mode = st.session_state.get(
        "theme_mode",
        "dark",
    )

    return DARK_THEME if theme_mode == "dark" else LIGHT_THEME


def apply_theme() -> None:
    """
    Aplica CSS global do tema ativo.
    """

    theme = get_theme()

    css_file = "dark.css" if theme["mode"] == "dark" else "light.css"

    css_path = Path(__file__).parent / "styles" / css_file

    with open(css_path, encoding="utf-8") as file:

        st.markdown(
            f"<style>{file.read()}</style>",
            unsafe_allow_html=True,
        )
