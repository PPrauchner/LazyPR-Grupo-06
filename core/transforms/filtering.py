"""
core/transforms/filtering.py
=============================
Fornece predicados e funções de filtragem puras que selecionam subconjuntos
de registros a partir de critérios configuráveis pelo analista.

Responsabilidades:
    - Implementar predicados individuais e combináveis para cada critério
      de filtragem: linguagem de programação, tipo de projeto, natureza
      da contribuição, nível de clareza e intervalo de datas.
    - Expor `build_filter(*predicates)` que compõe múltiplos predicados
      em uma única função de filtro via conjunção lógica (AND), integrando-se
      ao sistema de filtros dinâmicos globais do dashboard.
    - Garantir que nenhum filtro mute o registro original; cada predicado
      apenas avalia e retorna True/False.
    - Suportar a combinação dinâmica de filtros selecionados pelo usuário
      na sidebar do Streamlit, sem recarregar o dataset base.

Não deve:
    - Modificar campos dos registros (responsabilidade de cleaning.py
      ou normalizing.py).
    - Conter lógica de agregação.

Relacionado a:
    - Issue 08 (motor de filtros dinâmicos globais)
    - HU 08 (filtrar todas as visualizações por critérios)
    - Regra Funcional 02 (funções puras)
    - Regra Funcional 07 (filter(), lambda)
    - Conceito-Chave 07 (lambda para filtros inline)
"""

from collections.abc import Callable

from core.models.analysis_result import AnalysisResult

Predicate = Callable[[AnalysisResult], bool]


def by_language(languages: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por linguagem.

    A comparação é case-insensitive para evitar descartes causados por
    diferenças de capitalização, como "Python" e "python".

    Args:
        languages: Linguagens selecionadas pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando a linguagem
        do registro estiver entre as linguagens permitidas.
    """
    allowed = frozenset(map(str.lower, languages))
    return lambda record: record.language.lower() in allowed


def by_project_type(project_types: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por tipo de projeto.

    Os valores esperados devem seguir o vocabulário controlado do projeto,
    como "library", "web_app", "framework", "cli" e "other".

    Args:
        project_types: Tipos de projeto selecionados pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando o tipo de
        projeto do registro estiver entre os valores permitidos.
    """
    allowed = frozenset(map(str.lower, project_types))
    return lambda record: record.project_type.lower() in allowed


def by_pr_nature(pr_natures: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por natureza da contribuição.

    Os valores devem corresponder ao campo pr_nature definido em AnalysisResult,
    como "bug_fix", "feature", "refactoring", "documentation" e "other".

    Args:
        pr_natures: Naturezas de contribuição selecionadas pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando a natureza
        da contribuição estiver entre os valores permitidos.
    """
    allowed = frozenset(map(str.lower, pr_natures))
    return lambda record: record.pr_nature.lower() in allowed


def by_clarity_level(clarity_levels: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por nível de clareza.

    O projeto define clarity_level como categoria textual, não como número.
    Por isso, o filtro recebe um conjunto de labels válidas em vez de um
    intervalo numérico.

    Args:
        clarity_levels: Níveis de clareza selecionados pelo usuário.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando o nível de
        clareza estiver entre os valores permitidos.
    """
    allowed = frozenset(map(str.lower, clarity_levels))
    return lambda record: record.clarity_level.lower() in allowed


def build_filter(*predicates: Predicate) -> Predicate:
    """
    Compõe múltiplos predicados em uma única função de filtro.

    A composição usa conjunção lógica: um registro só passa se todos os
    predicados ativos retornarem True. Quando nenhum predicado é informado,
    all() retorna True, permitindo que todos os registros passem.

    Args:
        *predicates: Predicados individuais criados a partir dos filtros
            selecionados na interface.

    Returns:
        Função que recebe um AnalysisResult e retorna True quando o registro
        satisfizer todos os critérios ativos.
    """
    return lambda record: all(predicate(record) for predicate in predicates)
