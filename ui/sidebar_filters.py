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
from collections.abc import Callable, Mapping
from datetime import date
from types import MappingProxyType

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

# `language` não é vocabulário de LLM: é derivada da extensão do arquivo em `path`.
# A lista da sidebar é derivada da mesma fonte para não divergir do que o sistema
# realmente produz (ver CLAUDE.md §7).
from services.ingestion import _EXTENSION_TO_LANGUAGE

LANGUAGES: tuple[str, ...] = tuple(sorted(frozenset(_EXTENSION_TO_LANGUAGE.values())))

LANGUAGE_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "c": "C",
        "cpp": "C++",
        "csharp": "C#",
        "dart": "Dart",
        "go": "Go",
        "java": "Java",
        "javascript": "JavaScript",
        "kotlin": "Kotlin",
        "php": "PHP",
        "python": "Python",
        "ruby": "Ruby",
        "rust": "Rust",
        "scala": "Scala",
        "swift": "Swift",
        "typescript": "TypeScript",
    }
)

# Os vocabulários abaixo são os valores canônicos da §8 do CLAUDE.md — o que o
# pipeline grava em AnalysisResult e o que os predicados de core/transforms/
# filtering.py comparam. Os rótulos legíveis vivem apenas nos mapas *_LABELS,
# consumidos via `format_func`; o valor que trafega é sempre o canônico.
PROJECT_TYPES: tuple[str, ...] = (
    "library",
    "web_app",
    "framework",
    "cli",
    "other",
    "unknown",
)

PROJECT_TYPE_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "library": "Biblioteca",
        "web_app": "Aplicação Web",
        "framework": "Framework",
        "cli": "CLI",
        "other": "Outro",
        "unknown": "Desconhecido",
    }
)

PR_NATURES: tuple[str, ...] = (
    "bug_fix",
    "feature",
    "refactoring",
    "documentation",
    "other",
    "unknown",
)

PR_NATURE_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "bug_fix": "Correção de Bug",
        "feature": "Nova Funcionalidade",
        "refactoring": "Refatoração",
        "documentation": "Documentação",
        "other": "Outra",
        "unknown": "Desconhecida",
    }
)

CLARITY_LEVELS: tuple[str, ...] = (
    "excellent",
    "good",
    "basic",
    "insufficient",
    "unknown",
)

CLARITY_LEVEL_LABELS: Mapping[str, str] = MappingProxyType(
    {
        "excellent": "Excelente",
        "good": "Boa",
        "basic": "Básica",
        "insufficient": "Insuficiente",
        "unknown": "Desconhecida",
    }
)

PAGES = (
    "🏠 Home",
    "📂 Upload",
    "📊 Overview",
    "🔥 Correlação",
    "💾 Exportação",
)


def label_formatter(labels: Mapping[str, str]) -> Callable[[str], str]:
    """Cria a `format_func` que exibe o rótulo legível de um valor canônico.

    O widget continua trafegando o valor canônico (o que os predicados de
    `core/transforms/filtering.py` comparam); só a exibição é traduzida.

    Args:
        labels: Mapa de valor canônico para rótulo legível.

    Returns:
        Função que traduz um valor canônico em rótulo, devolvendo o próprio
        valor quando não houver rótulo cadastrado.
    """
    return lambda value: labels.get(value, value)


def get_active_filters() -> Predicate:
    """Retorna predicado funcional composto baseado nos filtros ativos.

    Lógica: (language1 OR language2 OR ...) AND (type1 OR type2 OR ...) AND ...

    Cada dimensão tem OR interno (múltiplas seleções na mesma dimensão = OR).
    Entre dimensões: AND (todos os filtros ativos devem ser satisfeitos).

    Returns:
        Predicate (Callable[[AnalysisResult], bool]) que retorna True se o registro
        satisfaz todos os critérios ativos.
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

    # UM predicado por dimensão (OR dentro de cada uma)
    if selected_languages:
        active_predicates.append(by_language(selected_languages))

    if selected_project_types:
        active_predicates.append(by_project_type(selected_project_types))

    if selected_natures:
        active_predicates.append(by_pr_nature(selected_natures))

    if selected_clarity:
        active_predicates.append(by_clarity_level(selected_clarity))

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
            Plataforma para análise semântica de Pull Requests com LLMs.
            """)

        st.divider()

        render_section_title("NAVEGAÇÃO")

        if "page" not in st.session_state:
            st.session_state["page_override"] = "🏠 Home"

        selected_page = st.radio(
            "Navegação",
            PAGES,
            key="page",
            label_visibility="collapsed",
        )

        st.divider()

        render_section_title("FILTROS GLOBAIS")

        st.multiselect(
            "Linguagens",
            LANGUAGES,
            key="selected_languages",
            format_func=label_formatter(LANGUAGE_LABELS),
        )

        st.multiselect(
            "Tipos de Projeto",
            PROJECT_TYPES,
            key="selected_project_types",
            format_func=label_formatter(PROJECT_TYPE_LABELS),
        )

        st.multiselect(
            "Natureza da Contribuição",
            PR_NATURES,
            key="selected_natures",
            format_func=label_formatter(PR_NATURE_LABELS),
        )

        st.multiselect(
            "Nível de Clareza",
            CLARITY_LEVELS,
            key="selected_clarity",
            format_func=label_formatter(CLARITY_LEVEL_LABELS),
        )

        use_date_filter = st.checkbox(
            "Filtrar por data",
            key="use_date_filter",
        )

        if use_date_filter:

            st.markdown("##### Período")

            start_date = st.date_input(
                "Data inicial",
                value=date(2020, 1, 1),
                key="start_date_input",
            )

            end_date = st.date_input(
                "Data final",
                value=date.today(),
                key="end_date_input",
            )

            st.session_state["start_date"] = start_date.strftime("%Y-%m-%d")

            st.session_state["end_date"] = end_date.strftime("%Y-%m-%d")

        st.divider()

        if st.button(
            "↻ Limpar filtros",
            width="stretch",
        ):

            keys_to_clear = (
                "selected_languages",
                "selected_project_types",
                "selected_natures",
                "selected_clarity",
                "use_date_filter",
                "start_date",
                "end_date",
                "start_date_input",
                "end_date_input",
            )

            for key in keys_to_clear:

                if key in st.session_state:

                    del st.session_state[key]

            st.rerun()

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

        st.caption("LazyPR • 2026")

    return {
        "page": st.session_state["page"],
    }
