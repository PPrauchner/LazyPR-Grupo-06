import streamlit as st


def render_normalization_dashboard(records):

    st.title("⚙️ Normalização")

    st.metric(
        "Registros normalizados",
        len(records),
    )

    st.info("Mostra métricas da etapa de normalização.")
