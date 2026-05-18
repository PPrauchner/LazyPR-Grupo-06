"""
ui/sidebar_filters.py
======================
Implementa os controles interativos de filtragem global do dashboard,
traduzindo seleções do usuário em predicados funcionais compostos.

Responsabilidades:
    - Renderizar widgets de filtragem no sidebar do Streamlit para cada
      dimensão analisável: linguagem, tipo de projeto, natureza da
      contribuição e nível de clareza.
    - Implementar `get_active_filters()` que lê o estado atual dos
      widgets e retorna uma função de filtro composta (via
      `core/transforms/filtering.py`) pronta para ser aplicada ao
      stream de dados.
    - Garantir que a mudança de qualquer filtro reaplique o pipeline
      sobre os dados já carregados em cache, sem reler o arquivo.
    - Manter os filtros sincronizados com `st.session_state` para
      preservar as seleções do analista durante a navegação entre páginas.

Não deve:
    - Conter lógica de agregação, plotagem ou acesso a LLMs.
    - Modificar diretamente os dados do dataset.

Relacionado a:
    - Issue 08 (motor de filtros dinâmicos globais)
    - HU 08 (filtrar todas as visualizações simultaneamente)
    - Conceito-Chave 07 (lambda para filtros inline)
"""
import streamlit as st
from datetime import datetime
from core.transforms.filtering import (
    is_language,
    has_project_type,
    has_pr_nature,
    has_clarity_level,
    is_in_date_range,
    build_filter,
    Predicate
)

def get_active_filters() -> Predicate:
    """
    Lê o estado atual dos widgets no sidebar e retorna uma função 
    de filtro composta (Predicate) pronta para ser aplicada ao stream de dados.
    """
    st.sidebar.header("Filtros Globais")

    # Utilizando tuplas (imutáveis) ao invés de listas
    LANGUAGES = ("Todas", "Python", "JavaScript", "Java", "C++", "Go", "TypeScript", "Ruby")
    PROJECT_TYPES = ("Todos", "biblioteca", "framework", "aplicação web", "ferramenta CLI", "outro")
    PR_NATURES = ("Todas", "bug_fix", "feature", "refatoração", "documentação", "outro")
    CLARITY_LEVELS = ("Todos", "insuficiente", "básica", "boa", "excelente")

    # Captura das escolhas do usuário
    selected_lang = st.sidebar.selectbox("Linguagem", LANGUAGES)
    selected_type = st.sidebar.selectbox("Tipo de Projeto", PROJECT_TYPES)
    selected_nature = st.sidebar.selectbox("Natureza da Contribuição", PR_NATURES)
    selected_clarity = st.sidebar.selectbox("Clareza da Descrição", CLARITY_LEVELS)
    
    # Filtro de Data
    use_date_filter = st.sidebar.checkbox("Filtrar por data?")
    start_date, end_date = None, None
    if use_date_filter:
        dates = st.sidebar.date_input("Intervalo de criação", [])
        if len(dates) == 2:
            start_date = dates[0].strftime("%Y-%m-%d")
            end_date = dates[1].strftime("%Y-%m-%d")

    # Mapeamento do estado da UI para os predicados puros
    active_predicates = []
    
    if selected_lang != "Todas":
        active_predicates.append(is_language(selected_lang))
        
    if selected_type != "Todos":
        active_predicates.append(has_project_type(selected_type))
        
    if selected_nature != "Todas":
        active_predicates.append(has_pr_nature(selected_nature))
        
    if selected_clarity != "Todos":
        active_predicates.append(has_clarity_level(selected_clarity))
        
    if use_date_filter and start_date and end_date:
        active_predicates.append(is_in_date_range(start_date, end_date))

    # Retorna o lambda puro resultante da combinação de todos os ativos
    return build_filter(*active_predicates)