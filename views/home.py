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
                padding: 3rem 2rem;
                border-radius: 24px;
                background: linear-gradient(
                    135deg,
                    {theme['card']},
                    rgba(124,58,237,0.12)
                );
                border: 1px solid {theme['border']};
                margin-bottom: 2rem;
                box-shadow: 0 0 30px rgba(124,58,237,0.10);
            "
        >

            <div
                style="
                    font-size: 3rem;
                    font-weight: 800;
                    color: {theme['text']};
                "
            >
                🚀 LazyPR
            </div>

            <div
                style="
                    margin-top: 1rem;
                    font-size: 1.1rem;
                    line-height: 1.8;
                    color: {theme['muted_text']};
                    max-width: 850px;
                "
            >
                Plataforma analítica para análise semântica
                de Pull Requests utilizando Programação Funcional,
                visualização interativa de dados e modelos de linguagem.
            </div>

        </div>
        """,
        unsafe_allow_html=True,
    )

    st.subheader("Visão Geral")

    kpi_col1, kpi_col2, kpi_col3, kpi_col4 = st.columns(4)

    with kpi_col1:

        metric_card(
            title="Total PRs",
            value=str(len(records)),
            icon="📦",
            trend="+14%",
        )

    with kpi_col2:

        metric_card(
            title="Linguagens",
            value="18",
            icon="💻",
            trend="+3",
        )

    with kpi_col3:

        metric_card(
            title="Projetos",
            value="42",
            icon="🧩",
            trend="+7%",
        )

    with kpi_col4:

        metric_card(
            title="Clareza Média",
            value="8.7",
            icon="✨",
            trend="+0.6",
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
