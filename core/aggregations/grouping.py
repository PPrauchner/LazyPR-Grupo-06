"""
core/aggregations/grouping.py
==============================
Fornece funções puras de agrupamento que organizam coleções de
`AnalysisResult` em estruturas indexadas por chaves compostas,
habilitando análises multidimensionais.

Responsabilidades:
    - Implementar `group_by(key_fn, records)` como função de ordem superior
      que agrupa registros de acordo com qualquer função de chave fornecida
      pelo chamador, sem assumir critério fixo.
    - Produzir agrupamentos por combinações de dimensões: (linguagem, tipo),
      (tipo, natureza), (linguagem, natureza, clareza), cobrindo os cruzamentos
      exigidos pelas visualizações das Issues 05, 06 e 07.
    - Retornar estruturas imutáveis mapeando chave → tupla de registros,
      nunca listas mutáveis.
    - Compor com `counters.py` e `metrics.py` para produzir sumarizações
      por grupo sem duplicar lógica.

Não deve:
    - Realizar I/O, chamadas a LLMs ou lógica de plotagem.
    - Modificar os registros agrupados.

Relacionado a:
    - Issue 05 (estratificação multidimensional)
    - Issue 07 (cruzamento de clareza, tipo e linguagem)
    - HU 07 (relação entre clareza, tipo de projeto, natureza e linguagem)
    - Regra Funcional 06 (composição de funções menores)
    - Conceito-Chave 09 (composição como mecanismo de pipeline)
"""

from functools import reduce, lru_cache
from typing import Callable, Iterable, Any, Dict, Tuple
from collections import Counter


def group_by(
    key_fn: Callable[[Any], Any], records: Iterable[Any]
) -> Dict[Any, Tuple[Any, ...]]:
    """
    Higher-order function that groups records by a dynamically evaluated key.

    Uses functional reduction to avoid imperative loops. It returns a new dictionary
    mapping keys to immutable tuples of records, adhering to immutability rules.

    Args:
        key_fn: A pure function that extracts the grouping key from a record.
        records: An iterable of records.

    Returns:
        A dictionary where values are immutable tuples of grouped records.
    """

    def reducer(acc: dict, record: Any) -> dict:
        key = key_fn(record)
        # Uses dictionary merging (|) to maintain immutability of the accumulator
        return acc | {key: acc.get(key, ()) + (record,)}

    return reduce(reducer, records, {})

def aggregate_by_language(
    records,
):
    """
    Agrupa PRs por linguagem.
    """

    counter = Counter(
        record.language
        for record in records
        if record.language
    )

    return tuple(
        sorted(
            counter.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def aggregate_by_pr_nature(records):

    counter = Counter(record.pr_nature for record in records if record.pr_nature)

    return tuple(
        sorted(
            counter.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def aggregate_by_project_type(records):

    counter = Counter(record.project_type for record in records if record.project_type)

    return tuple(
        sorted(
            counter.items(),
            key=lambda item: item[1],
            reverse=True,
        )
    )


def group_by_language_and_clarity(
    records: Iterable[Any],
) -> Dict[Tuple[str, str], Tuple[Any, ...]]:
    """
    Groups records simultaneously by multiple dimensions: language and clarity level.
    """
    return group_by(
        lambda r: (
            getattr(r, "language", "unknown"),
            getattr(r, "clarity_level", "unknown"),
        ),
        records,
    )


@lru_cache(maxsize=1)
def cross_count_language_clarity(
    records: Tuple[Any, ...],
) -> Dict[Tuple[str, str], int]:
    """
    Produces cross-counts of PRs simultaneously by language and clarity level.
    Composes the purely functional group_by with a map transformation.

    Memoized to prevent re-computation on UI refreshes (requires immutable input).

    Args:
        records: An immutable tuple of records (must be a tuple for lru_cache hashing).

    Returns:
        A dictionary mapping a composite key (language, clarity) to its count.
        Example: {("Python", "boa"): 45}
    """
    grouped_data = group_by_language_and_clarity(records)

    # Purely functional mapping to count group sizes without 'for' loops
    return dict(map(lambda item: (item[0], len(item[1])), grouped_data.items()))
