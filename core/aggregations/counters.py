"""
Fornece funções puras de contagem e distribuição sobre coleções de
AnalysisResult, implementadas com reduce() e composição funcional.

Responsabilidades:
    - Contar PRs agrupados por:
        * linguagem
        * tipo de projeto
        * natureza da contribuição
    - Produzir estruturas prontas para visualização.
    - Evitar mutação direta dos registros originais.
    - Centralizar agregações reutilizáveis.

Não deve:
    - Realizar I/O
    - Chamar LLMs
    - Renderizar gráficos
"""

from collections import Counter
from functools import reduce
from types import MappingProxyType
from typing import Any, Callable, Iterable, Mapping


def _increment_counter(
    accumulator: Counter,
    key: str,
) -> Counter:
    """
    Retorna um novo Counter incrementado sem mutar
    o acumulador original.
    """

    return accumulator + Counter([key])


def _count_reducer(
    key_fn: Callable[[Any], str],
) -> Callable[[Counter, Any], Counter]:
    """
    Cria reducer funcional parametrizado.

    Args:
        key_fn:
            Função que extrai a chave do registro.

    Returns:
        Função reducer compatível com reduce().
    """

    def reducer(
        accumulator: Counter,
        record: Any,
    ) -> Counter:

        key = key_fn(record)

        return _increment_counter(
            accumulator,
            key,
        )

    return reducer


def count_by(
    records: Iterable[Any],
    key_fn: Callable[[Any], str],
) -> Mapping[str, int]:
    """
    Conta registros por dimensão usando reduce()
    e composição funcional.

    Args:
        records:
            Coleção iterável de registros.

        key_fn:
            Função responsável por extrair
            a chave de agrupamento.

    Returns:
        Estrutura read-only contendo:
            {
                categoria: frequência
            }
    """

    counts = reduce(
        _count_reducer(key_fn),
        records,
        Counter(),
    )

    return MappingProxyType(dict(counts))


def count_by_language(
    records: Iterable[Any],
) -> Mapping[str, int]:
    """
    Conta PRs agrupados por linguagem.
    """

    return count_by(
        records,
        lambda record: record.language,
    )


def count_by_project_type(
    records: Iterable[Any],
) -> Mapping[str, int]:
    """
    Conta PRs agrupados por tipo de projeto.
    """

    return count_by(
        records,
        lambda record: record.project_type,
    )


def count_by_pr_nature(
    records: Iterable[Any],
) -> Mapping[str, int]:
    """
    Conta PRs agrupados por natureza da contribuição.
    """

    return count_by(
        records,
        lambda record: record.pr_nature,
    )
