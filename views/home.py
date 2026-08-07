"""
Página inicial institucional da plataforma LazyPR.
"""

import streamlit as st

from ui.components import (
    metric_card,
)

from ui.theme import (
    get_theme,
)


def render_home(records) -> None:
    """
    Renderiza página inicial institucional.
    """

    theme = get_theme()

    st.markdown(
        f"""
        <div
            style="
                padding: 2rem;
                border-radius: 24px;
                background:
                radial-gradient(
                    circle at top left,
                    rgba(124,58,237,0.18),
                    transparent 30%
                ),
                linear-gradient(
                    135deg,
                    #020817,
                    #0f172a
                );
                border: 1px solid {theme['border']};
                box-shadow: 0 0 30px rgba(124,58,237,0.08);
                margin-bottom: 1.5rem;
            "
        >
         <div
             style="
                display:flex;
                 justify-content:space-between;
                 align-items:center;
                 gap:2rem;
                 flex-wrap:wrap;
             "
         >

        <div
             style="
                 flex:1;
                 min-width:320px;
             "
         >

         <div
            style="
                font-size:2.3rem;
                font-weight:800;
                color:{theme['text']};
            "
        >
            Bem-vindo ao
            <span style="color:#8b5cf6;">
                LazyPR 🐱
            </span>
        </div>

         <div
             style="
                margin-top:1rem;
                font-size:1rem;
                 line-height:1.8;
                color:{theme['muted_text']};
                max-width:650px;
         "
         >
                Plataforma de análise semântica de Pull Requests
                  utiizando LLMs, cache persistente e agregações multidimensionais.
        </div>

         </div>

         </div>
        </div>
        """,
        unsafe_allow_html=True,
    )

    # ---------------------------------------------------------
    # KPIs
    # ---------------------------------------------------------

    st.subheader("Visão Geral")

    from core.aggregations.counters import (
        count_by_language,
        count_by_project_type,
    )

    total_prs = len(records)

    languages = count_by_language(records)

    projects = count_by_project_type(records)

    clarity_values = {
        "insufficient": 1,
        "basic": 2,
        "good": 3,
        "excellent": 4,
    }

    clarity_avg = sum(
        clarity_values.get(
            getattr(
                record,
                "clarity_level",
                None,
            ),
            0,
        )
        for record in records
    ) / max(
        total_prs,
        1,
    )

    clarity_avg = round(
        clarity_avg,
        2,
    )

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:

        metric_card(
            label="Total PRs",
            value=str(total_prs),
            icon="📦",
        )

    with kpi_col2:

        metric_card(
            label="Linguagens",
            value=str(len(languages)),
            icon="💻",
        )

    with kpi_col3:

        metric_card(
            label="Projetos",
            value=str(len(projects)),
            icon="🧩",
        )

    with kpi_col4:

        metric_card(
            label="Clareza Média",
            value=str(clarity_avg),
            icon="✨",
        )

    st.divider()

    # ---------------------------------------------------------
    # PIPELINE
    # ---------------------------------------------------------

    st.subheader("Pipeline Funcional")
    col1, arrow1, col2, arrow2, col3, arrow3, col4, arrow4, col5 = st.columns(
        [2, 0.4, 2, 0.4, 2, 0.4, 2, 0.4, 2]
    )

    with col1:

        if st.button(
            "📥",
            key="pipeline_ingestao",
            width="stretch",
        ):

            st.session_state["page_override"] = "upload"
            st.rerun()

        st.markdown(
            """
            <div style="text-align:center;">
                <h4>Ingestão</h4>
                <p style="color:#94a3b8;">CSV → Stream</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with arrow1:

        st.markdown(
            "<h1 style='text-align:center;padding-top:30px;'>→</h1>",
            unsafe_allow_html=True,
        )

    with col2:

        if st.button(
            "🧹",
            key="pipeline_limpeza",
            width="stretch",
        ):

            st.session_state["page_override"] = "cleaning"
            st.rerun()

        st.markdown(
            """
            <div style="text-align:center;">
                <h4>Limpeza</h4>
                <p style="color:#94a3b8;">Remove ruídos</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with arrow2:

        st.markdown(
            "<h1 style='text-align:center;padding-top:30px;'>→</h1>",
            unsafe_allow_html=True,
        )

    with col3:

        if st.button(
            "⚙️",
            key="pipeline_normalizacao",
            width="stretch",
        ):

            st.session_state["page_override"] = "normalization"
            st.rerun()

        st.markdown(
            """
            <div style="text-align:center;">
                <h4>Normalização</h4>
                <p style="color:#94a3b8;">Padrões e Labels</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with arrow3:

        st.markdown(
            "<h1 style='text-align:center;padding-top:30px;'>→</h1>",
            unsafe_allow_html=True,
        )

    with col4:

        if st.button(
            "🧠",
            key="pipeline_classificacao",
            width="stretch",
        ):

            st.session_state["page_override"] = "overview"
            st.rerun()

        st.markdown(
            """
            <div style="text-align:center;">
                <h4>Classificação</h4>
                <p style="color:#94a3b8;">LLMs</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    with arrow4:

        st.markdown(
            "<h1 style='text-align:center;padding-top:30px;'>→</h1>",
            unsafe_allow_html=True,
        )

    with col5:

        if st.button(
            "📊",
            key="pipeline_agregacao",
            width="stretch",
        ):

            st.session_state["page_override"] = "correlations"
            st.rerun()

        st.markdown(
            """
            <div style="text-align:center;">
                <h4>Agregação</h4>
                <p style="color:#94a3b8;">Métricas</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

    st.divider()

    st.subheader("Acesso Rápido")

    quick_col1, quick_col2, quick_col3 = st.columns(3)

    with quick_col1:

        if st.button(
            "📂 Upload",
            width="stretch",
            key="quick_upload",
        ):

            st.session_state["page_override"] = "upload"
            st.rerun()

    with quick_col2:

        if st.button(
            "📊 Overview",
            width="stretch",
            key="quick_overview",
        ):

            st.session_state["page_override"] = "overview"
            st.rerun()

    with quick_col3:

        if st.button(
            "🔥 Correlação",
            width="stretch",
            key="quick_correlation",
        ):

            st.session_state["page_override"] = "correlations"
            st.rerun()

    st.divider()

    st.subheader("Insights Rápidos")

    if records:

        st.info(f"📦 Total de registros analisados: {len(records)}")

    else:

        st.info("Realize uma análise para visualizar insights automáticos.")
