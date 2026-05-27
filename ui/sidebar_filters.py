"""
Implementa os controles interativos de filtragem global do dashboard,
traduzindo seleções do usuário em predicados funcionais compostos.

Responsabilidades:
    - Renderizar widgets de filtragem no sidebar do Streamlit
    - Centralizar navegação entre páginas
    - Construir predicados funcionais compostos
    - Preservar separação entre UI e lógica funcional

Não deve:
    - Conter lógica de agregação
    - Renderizar gráficos
    - Chamar LLMs
"""

import streamlit as st

from ui.layout import (
    render_section_title,
    render_dataset_card,
)

from core.transforms.filtering import (
    Predicate,
    by_clarity_level,
    by_language,
    by_pr_nature,
    by_project_type,
    compose_predicates,
    is_in_date_range,
)

LANGUAGES = (
    "Python",
    "JavaScript",
    "Java",
    "Go",
    "TypeScript",
    "Ruby",
)

PROJECT_TYPES = (
    "Framework",
    "Library",
    "CLI",
    "Tool",
)

PR_NATURES = (
    "bug_fix",
    "feature",
    "refactor",
    "documentation",
)

CLARITY_LEVELS = (
    "excellent",
    "good",
    "average",
    "poor",
)

PAGES = (
    "🏠 Home",
    "📂 Upload",
    "📊 Overview",
    "🔥 Correlação",
    "💾 Exportação",
)


def get_active_filters() -> Predicate:
    """
    Retorna predicado funcional composto
    baseado nos filtros ativos.
    """

    active_predicates = []

    selected_languages = st.session_state.get(
        "selected_languages",
        (),
    )

    selected_project_types = st.session_state.get(
        "selected_project_types",
        (),
    )

    selected_natures = st.session_state.get(
        "selected_natures",
        (),
    )

    selected_clarity = st.session_state.get(
        "selected_clarity",
        (),
    )

    use_date_filter = st.session_state.get(
        "use_date_filter",
        False,
    )

    start_date = st.session_state.get(
        "start_date",
    )

    end_date = st.session_state.get(
        "end_date",
    )

    active_predicates.extend(
        map(
            lambda language: by_language((language,)),
            selected_languages,
        )
    )

    active_predicates.extend(
        map(
            lambda project_type: by_project_type((project_type,)),
            selected_project_types,
        )
    )

    active_predicates.extend(
        map(
            lambda pr_nature: by_pr_nature((pr_nature,)),
            selected_natures,
        )
    )

    active_predicates.extend(
        map(
            lambda clarity: by_clarity_level((clarity,)),
            selected_clarity,
        )
    )

    if use_date_filter and start_date and end_date:

        active_predicates.append(
            is_in_date_range(
                start_date,
                end_date,
            )
        )

    return compose_predicates(
        active_predicates,
    )


def render_sidebar() -> dict:
    """
    Renderiza sidebar global da aplicação.
    """

    with st.sidebar:

        if "theme_mode" not in st.session_state:

            st.session_state["theme_mode"] = "dark"

        theme_is_dark = st.session_state["theme_mode"] == "dark"

        toggle_value = st.toggle(
            "🌙 Tema Escuro",
            value=theme_is_dark,
        )

        st.session_state["theme_mode"] = "dark" if toggle_value else "light"

        st.caption("Alternar aparência visual do dashboard.")

        st.title("🚀 LazyPR")

        st.markdown("""
            Plataforma analítica para análise
            semântica de Pull Requests
            utilizando LLMs e Programação Funcional.
            """)

        st.divider()

        render_section_title("NAVEGAÇÃO")

        selected_page = st.radio(
            "Navegação",
            PAGES,
            label_visibility="collapsed",
        )

        st.divider()

        render_section_title("FILTROS GLOBAIS")

        st.multiselect(
            "Linguagens",
            LANGUAGES,
            key="selected_languages",
        )

        st.multiselect(
            "Tipos de Projeto",
            PROJECT_TYPES,
            key="selected_project_types",
        )

        st.multiselect(
            "Natureza da Contribuição",
            PR_NATURES,
            key="selected_natures",
        )

        st.multiselect(
            "Nível de Clareza",
            CLARITY_LEVELS,
            key="selected_clarity",
        )

        use_date_filter = st.checkbox(
            "Filtrar por data",
            key="use_date_filter",
        )

        if use_date_filter:

            dates = st.date_input(
                "Intervalo de criação",
                key="date_range",
            )

            if len(dates) == 2:

                st.session_state["start_date"] = dates[0].strftime("%Y-%m-%d")

                st.session_state["end_date"] = dates[1].strftime("%Y-%m-%d")

        st.divider()

        dataset_name = st.session_state.get(
            "dataset_name",
            "Nenhum dataset carregado",
        )

        analysis_results = st.session_state.get(
            "analysis_results",
            (),
        )

        render_dataset_card(
            dataset_name,
            len(tuple(analysis_results)),
        )

        st.divider()

        st.caption("LazyPR • Programação Funcional • 2026")

    return {
        "page": selected_page,
    }
