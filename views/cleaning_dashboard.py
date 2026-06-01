import streamlit as st


def render_cleaning_dashboard(records):

    st.title("🧹 Limpeza")

    total = len(records)

    st.metric(
        "Registros após limpeza",
        total,
    )

    st.info("Mostra métricas da etapa de limpeza do pipeline.")
