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
"""

from collections.abc import Callable, Iterable
from functools import reduce

from core.models.analysis_result import AnalysisResult

Predicate = Callable[[AnalysisResult], bool]


def by_language(languages: tuple[str, ...]) -> Predicate:
    allowed = frozenset(map(str.lower, languages))
    return lambda record: record.language.lower() in allowed


def is_language(language: str) -> Predicate:
    """Wrapper para by_language que aceita uma linguagem individual."""
    return by_language((language,))


def by_project_type(project_types: tuple[str, ...]) -> Predicate:
    allowed = frozenset(map(str.lower, project_types))
    return lambda record: record.project_type.lower() in allowed


def by_pr_nature(pr_natures: tuple[str, ...]) -> Predicate:
    """
    Cria um predicado para filtrar registros por natureza da contribuição.

    Os valores devem corresponder ao campo pr_nature definido em AnalysisResult,
    como "bug_fix", "feature", "refactoring", "documentation" e "other".


def by_pr_nature(pr_natures: tuple[str, ...]) -> Predicate:
    allowed = frozenset(map(str.lower, pr_natures))
    return lambda record: record.pr_nature.lower() in allowed


def has_pr_nature(pr_nature: str) -> Predicate:
    """Wrapper para by_pr_nature que aceita uma natureza individual."""
    return by_pr_nature((pr_nature,))


def by_clarity_level(clarity_levels: tuple[str, ...]) -> Predicate:
    allowed = frozenset(map(str.lower, clarity_levels))
    return lambda record: record.clarity_level.lower() in allowed


def is_in_date_range(
    start_date: str,
    end_date: str,
) -> Predicate:
    """
    Cria predicado para filtrar registros
    dentro de um intervalo de datas.

    Args:
        start_date:
            Data inicial no formato YYYY-MM-DD.

        end_date:
            Data final no formato YYYY-MM-DD.

    Returns:
        Predicate que valida se o registro
        está dentro do intervalo informado.
    """

    return lambda record: start_date <= record.created_at <= end_date


def compose_predicates(predicates: Iterable[Predicate]) -> Predicate:
    """
    Constrói uma nova função pura combinando múltiplos predicados via conjunção lógica (AND).


def is_in_date_range(
    start_date: str,
    end_date: str,
) -> Predicate:
    """
    Cria predicado para filtrar registros dentro de um intervalo de datas.

    Args:
        start_date: Data inicial no formato YYYY-MM-DD.
        end_date: Data final no formato YYYY-MM-DD.
    """
    return lambda record: start_date <= record.created_at <= end_date


def compose_predicates(predicates: Iterable[Predicate]) -> Predicate:
    predicate_tuple: tuple[Predicate, ...] = tuple(predicates)

    if not predicate_tuple:
        return lambda _: True

    return reduce(
        lambda accumulated, current: (
            lambda record: accumulated(record) and current(record)
        ),
        predicate_tuple,
    )


def build_filter(*predicates: Predicate) -> Predicate:
    """
    Compõe múltiplos predicados em um único predicado via conjunção lógica (AND).
    """
    return compose_predicates(predicates)


def apply_filters(
    predicates: Iterable[Predicate],
    records: Iterable[AnalysisResult],
) -> filter:
    return filter(compose_predicates(predicates), records)