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

from core.transforms.filtering import (
    Predicate,
    build_filter,
    has_clarity_level,
    has_pr_nature,
    has_project_type,
    is_in_date_range,
    is_language,
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
    "basic",
    "insufficient",
)

PAGES = (
    "Upload",
    "Overview",
    "Correlação",
    "Exportação",
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
            is_language,
            selected_languages,
        )
    )

    active_predicates.extend(
        map(
            has_project_type,
            selected_project_types,
        )
    )

    active_predicates.extend(
        map(
            has_pr_nature,
            selected_natures,
        )
    )

    active_predicates.extend(
        map(
            has_clarity_level,
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

    return build_filter(
        *active_predicates,
    )


def render_sidebar() -> dict:
    """
    Renderiza sidebar global da aplicação.
    """

    with st.sidebar:

        st.title("RP3 Analytics")

        st.markdown("""
            Dashboard funcional para análise
            de Pull Requests do GitHub.
            """)

        st.divider()

        selected_page = st.selectbox(
            "Página",
            PAGES,
        )

        st.subheader("Filtros")

        selected_languages = st.multiselect(
            "Linguagens",
            LANGUAGES,
            key="selected_languages",
        )

        selected_project_types = st.multiselect(
            "Tipos de Projeto",
            PROJECT_TYPES,
            key="selected_project_types",
        )

        selected_natures = st.multiselect(
            "Natureza da Contribuição",
            PR_NATURES,
            key="selected_natures",
        )

        selected_clarity = st.multiselect(
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

        st.caption("Projeto desenvolvido com " "Programação Funcional.")

    return {
        "page": selected_page,
    }
