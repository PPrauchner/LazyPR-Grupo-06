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
    get_active_filters,
    render_sidebar,
)

from core.transforms.filtering import (
    apply_filters,
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

analysis = st.session_state.get(
    "analysis_results",
    (),
)

filters = render_sidebar()

# Filtro de Visualização (ADR 0003): recorta a Análise já carregada, depois de
# a sidebar ter renderizado os widgets. Aplicado aqui, no roteamento, para que
# toda página receba o mesmo recorte — e o conjunto completo quando os filtros
# são limpos, inclusive num dataset servido do cache.
records = tuple(
    apply_filters(
        (get_active_filters(),),
        analysis,
    )
)

if "page_override" in st.session_state:

    page = st.session_state.pop("page_override")
else:
    page = filters["page"]

# O roteamento casa por chave estável, nunca pelo rótulo visível: mudar o texto
# de um rótulo (ou traduzi-lo) muda o que a navegação escreve na tela, não para
# onde ela leva. Os rótulos vivem em `ui/sidebar_filters.PAGE_LABELS`.
if page == "home":

    render_home(records)

elif page == "upload":

    render_upload_page()

elif page == "overview":

    render_overview(records)

elif page == "correlations":

    render_correlation_dashboard(records)

elif page == "export":

    render_export_page(records)
elif page == "cleaning":

    render_cleaning_dashboard(records)

elif page == "normalization":

    render_normalization_dashboard(records)
