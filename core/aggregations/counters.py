"""
core/aggregations/counters.py
==============================
Fornece funções puras de contagem e distribuição sobre coleções de
`AnalysisResult`, implementadas exclusivamente com `reduce()` e
expressões funcionais.

Responsabilidades:
    - Contar o total de PRs agrupados por linguagem de programação,
      tipo de projeto e natureza da contribuição, via `reduce()`.
    - Calcular a distribuição percentual de cada categoria em relação
      ao total do dataset filtrado.
    - Produzir estruturas de dados imutáveis (tuplas, frozensets ou
      dicionários read-only) prontas para consumo pelos componentes
      de visualização.
    - Suportar contagens estratificadas por combinações de critérios
      (ex: contagem de PRs do tipo "bug_fix" em projetos "framework"
      escritos em "Python").

Não deve:
    - Modificar os registros de entrada.
    - Realizar I/O ou chamar LLMs.
    - Conter lógica de plotagem.

Relacionado a:
    - Issue 05 (volume de PRs estratificado por linguagem, tipo e natureza)
    - HU 05 (visualização de número de PRs por categorias)
    - Regra Funcional 01 (uso de reduce() em vez de laços)
    - Regra Funcional 07 (map, filter, reduce)
    - Conceito-Chave 03 (reduce para agregação)
"""

from collections import Counter
from functools import reduce
from typing import Callable, Iterable, Any


def count_by(records: Iterable, key_fn: Callable) -> dict:
    """
    Conta registros por dimensão usando função pura.
    """

    return dict(
        reduce(
            lambda acc, record: (acc.update([key_fn(record)]) or acc),
            records,
            Counter(),
        )
    )


def count_by_language(records):
    return count_by(records, lambda r: r.language)


def count_by_project_type(records):
    return count_by(records, lambda r: r.project_type)


def count_by_pr_nature(records):
    return count_by(records, lambda r: r.pr_nature)
