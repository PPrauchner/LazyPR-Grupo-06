"""
Ponto de entrada da aplicação Streamlit, responsável por orquestrar
a inicialização do sistema e o roteamento entre páginas.

Responsabilidades:
    - Configurar layout global da aplicação
    - Integrar sidebar global
    - Centralizar navegação entre páginas
    - Orquestrar dashboards e páginas visuais
    - Manter separação entre UI e lógica funcional

Não deve:
    - Realizar agregações
    - Processar datasets
    - Renderizar gráficos diretamente
    - Executar lógica de negócio
"""

import streamlit as st

from views.home import (
    render_home,
)

from views.overview import (
    render_overview,
)

from views.correlations_dashboard import (
    render_correlation_dashboard,
)

from views.upload import (
    render_upload_page,
)

from views.export import (
    render_export_page,
)

from ui.sidebar_filters import (
    render_sidebar,
)

st.set_page_config(
    page_title="LazyPR Analytics",
    page_icon="📊",
    layout="wide",
)

from ui.theme import (
    apply_theme,
    initialize_theme,
)

from views.cleaning_dashboard import (
    render_cleaning_dashboard,
)

from views.normalization_dashboard import (
    render_normalization_dashboard,
)

initialize_theme()

apply_theme()

records = st.session_state.get(
    "analysis_results",
    (),
)

filters = render_sidebar()

if "page_override" in st.session_state:

 page = st.session_state.pop(
        "page_override"
    )
else:   
   page = filters["page"]
   
if page == "🏠 Home":

    render_home(records)

elif page == "📂 Upload":

    render_upload_page()

elif page == "📊 Overview":

    render_overview(records)

elif page == "🔥 Correlação":

    render_correlation_dashboard(records)

elif page == "💾 Exportação":

    render_export_page(records)
elif page == "🧹 Limpeza":

    render_cleaning_dashboard(records)

elif page == "⚙️ Normalização":

    render_normalization_dashboard(records)
