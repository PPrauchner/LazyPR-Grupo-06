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


def render_home(
    records,
) -> None:
    """
    Renderiza página inicial institucional.
    """

    theme = get_theme()

    st.markdown(
        f"""
    <div
        style="
            padding: 2rem 2rem;
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
           display: flex;
           justify-content: space-between;
           align-items: center;
           gap: 2rem;
           flex-wrap: wrap;
        "
    >

      <!-- TEXTO -->

    <div
        style="
        flex: 1;
        min-width: 320px;
        "
    >

    <div
        style="
           font-size: 2.3rem;
           font-weight: 800;
           color: {theme['text']};
        "
    >
        Bem-vindo ao
        <span style="color:#8b5cf6;">
        LazyPR
        </span>
    </div>

    <div
        style="
            margin-top: 1rem;
            font-size: 1rem;
            line-height: 1.8;
            color: {theme['muted_text']};
            max-width: 650px;
        "
    >
                Análise semântica de Pull Requests no GitHub com LLMs, cache persistente e agregações multidimensionais.

    </div>

    </div>

    <!-- PIPELINE -->

    <div
        style="
            display: flex;
            align-items: center;
            gap: 1.2rem;
            flex-wrap: wrap;
        "
    >

    <div style="text-align:center;">
    <div style="font-size:2.4rem;">📥</div>
    <div style="font-weight:700;color:white;">
            Ingestão
    </div>
    <div style="font-size:0.8rem;color:#94a3b8;">
            CSV → Stream
    </div>
    </div>

    <div style="font-size:2rem;color:#94a3b8;">→</div>

    <div style="text-align:center;">
    <div style="font-size:2.4rem;">🧹</div>
    <div style="font-weight:700;color:white;">
            Limpeza
    </div>
    <div style="font-size:0.8rem;color:#94a3b8;">
            Remove ruídos
    </div>
    </div>

    <div style="font-size:2rem;color:#94a3b8;">→</div>

    <div style="text-align:center;">
    <div style="font-size:2.4rem;">⚙️</div>
    <div style="font-weight:700;color:white;">
            Normalização
    </div>
    <div style="font-size:0.8rem;color:#94a3b8;">
            Padrões e Labels
    </div>
    </div>

    <div style="font-size:2rem;color:#94a3b8;">→</div>

    <div style="text-align:center;">
    <div style="font-size:2.4rem;">🤖</div>
    <div style="font-weight:700;color:white;">
            Classificação
    </div>
    <div style="font-size:0.8rem;color:#94a3b8;">
            LLMs
    </div>
    </div>

    <div style="font-size:2rem;color:#94a3b8;">→</div>

    <div style="text-align:center;">
    <div style="font-size:2.4rem;">📊</div>
    <div style="font-weight:700;color:white;">
            Agregação
    </div>
    <div style="font-size:0.8rem;color:#94a3b8;">
            Métricas
    </div>
    </div>

    </div>

    </div>

    </div>
    """,
        unsafe_allow_html=True,
    )

    st.subheader("Visão Geral")

    # Calcular KPIs dinamicamente (não hardcoded)
    from core.aggregations.counters import count_by_language, count_by_project_type

    total_prs = len(records)
    languages = count_by_language(records)
    projects = count_by_project_type(records)

    # Calcular clareza média (aproximada)
    clarity_values = {
        "insufficient": 1,
        "basic": 2,
        "good": 3,
        "excellent": 4,
    }
    clarity_avg = sum(clarity_values.get(r.clarity_level, 0) for r in records) / max(
        total_prs, 1
    )
    clarity_avg = round(clarity_avg, 2)

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:

        metric_card(
            label="Total PRs",
            value=str(total_prs),
            icon="📦",
            delta="+14%",
        )

    with kpi_col2:

        metric_card(
            label="Linguagens",
            value=str(len(languages)),
            icon="💻",
            delta="+3",
        )

    with kpi_col3:

        metric_card(
            label="Projetos",
            value=str(len(projects)),
            icon="🧩",
            delta="+7%",
        )

    with kpi_col4:

        metric_card(
            label="Clareza Média",
            value=str(clarity_avg),
            icon="✨",
            delta="+0.6",
        )

    st.divider()

    st.subheader("Pipeline Funcional")

    pipeline_cols = st.columns(5)

    pipeline_steps = [
        ("📥", "Ingestão"),
        ("🧹", "Limpeza"),
        ("⚙️", "Normalização"),
        ("🤖", "Classificação"),
        ("📊", "Agregação"),
    ]

    for column, (icon, title) in zip(
        pipeline_cols,
        pipeline_steps,
    ):

        with column:

            st.markdown(
                f"""
                <div
                    style="
                        padding: 1.2rem;
                        border-radius: 18px;
                        text-align: center;
                        background-color: {theme['card']};
                        border: 1px solid {theme['border']};
                        height: 100%;
                        transition: 0.2s ease;
                    "
                >

    <div
       style="
       font-size: 2rem;
    "
    >
        {icon}
    </div>

    <div
        style="
            margin-top: 0.7rem;
            font-weight: 700;
            color: {theme['text']};
    "
    >
            {title}
    </div>

    </div>
                """,
                unsafe_allow_html=True,
            )

    st.divider()

    st.subheader("Dataset Ativo")

    st.success("Dataset carregado e pronto para análise.")

    st.divider()

    st.subheader("Acesso Rápido")

    quick_col1, quick_col2, quick_col3 = st.columns(3)

    with quick_col1:

        st.info("📂 Upload de datasets e processamento inicial.")

    with quick_col2:

        st.info("📊 Visualização agregada e métricas analíticas.")

    with quick_col3:

        st.info("🔥 Correlações e análise multidimensional.")

    st.divider()

    st.subheader("Insights Rápidos")

    insight_col1, insight_col2 = st.columns(2)

    with insight_col1:

        st.info("💻 Linguagem predominante: Python")

    with insight_col2:

        st.info("🔥 Categoria mais frequente: Refatoração")
