"""
Funções puras para agregações multidimensionais
relacionadas à clareza, linguagem e tipo de projeto.

Responsabilidades:
    - Construir matrizes de correlação entre:
        * clareza x linguagem
        * clareza x tipo de projeto
        * clareza x natureza do PR
    - Produzir estruturas prontas para visualização
      em heatmaps e gráficos multidimensionais.
    - Utilizar reduce() e composição funcional.

Não deve:
    - Fazer plotagem
    - Realizar I/O
    - Chamar Streamlit
"""

from functools import reduce
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping


def _nested_increment(
    accumulator: dict,
    row_key: str,
    column_key: str,
) -> dict:
    """
    Retorna nova estrutura incrementada
    sem mutação do accumulator original.
    """

    current_row = accumulator.get(
        row_key,
        {},
    )

    updated_row = {
        **current_row,
        column_key: current_row.get(column_key, 0) + 1,
    }

    return {
        **accumulator,
        row_key: updated_row,
    }


def _create_matrix_reducer(
    row_getter: Callable[[Any], str],
    column_getter: Callable[[Any], str],
) -> Callable[[dict, Any], dict]:
    """
    Cria reducer reutilizável para matrizes
    multidimensionais.
    """

    def reducer(
        accumulator: dict,
        record: Any,
    ) -> dict:

        return _nested_increment(
            accumulator,
            row_getter(record),
            column_getter(record),
        )

    return reducer


def build_correlation_matrix(
    records: Iterable[Any],
    row_getter: Callable[[Any], str],
    column_getter: Callable[[Any], str],
) -> Mapping[str, Mapping[str, int]]:
    """
    Constrói matriz multidimensional reutilizável.
    """

    matrix = reduce(
        _create_matrix_reducer(
            row_getter,
            column_getter,
        ),
        records,
        {},
    )

    return MappingProxyType(matrix)


def _clarity_level(
    record: Any,
) -> str:
    """
    Extrai nível de clareza.
    """

    return record.clarity_level


def _language(
    record: Any,
) -> str:
    """
    Extrai linguagem do projeto.
    """

    return record.language


def _project_type(
    record: Any,
) -> str:
    """
    Extrai tipo de projeto.
    """

    return record.project_type


def _pr_nature(
    record: Any,
) -> str:
    """
    Extrai natureza da contribuição.
    """

    return record.pr_nature


def clarity_by_language(
    records: Iterable[Any],
) -> Mapping[str, Mapping[str, int]]:
    """
    Gera matriz:
        clareza -> linguagem -> contagem
    """

    return build_correlation_matrix(
        records,
        _clarity_level,
        _language,
    )


def clarity_by_project_type(
    records: Iterable[Any],
) -> Mapping[str, Mapping[str, int]]:
    """
    Gera matriz:
        clareza -> tipo de projeto -> contagem
    """

    return build_correlation_matrix(
        records,
        _clarity_level,
        _project_type,
    )


def clarity_by_pr_nature(
    records: Iterable[Any],
) -> Mapping[str, Mapping[str, int]]:
    """
    Gera matriz:
        clareza -> natureza do PR -> contagem
    """

    return build_correlation_matrix(
        records,
        _clarity_level,
        _pr_nature,
    )
