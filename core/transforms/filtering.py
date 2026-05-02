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
from datetime import date

from core.transforms.cleaning import CleanPRRecord

# Tipos

Predicate = Callable[[CleanPRRecord], bool]


def by_language(languages: list[str]) -> Predicate:
    """
    Mantém registros cuja linguagem de programação esteja na lista.

    Comparação case-insensitive para evitar descartes por capitalização.

    Exemplo:
        filtro = by_language(["python", "typescript"])
        filtro(record)  →  True se record.language in {"python", "typescript"}
    """
    allowed = {lang.lower() for lang in languages}

    def predicate(record: CleanPRRecord) -> bool:
        return record.language.lower() in allowed

    return predicate


def by_project_type(types: list[str]) -> Predicate:
    """
    Mantém registros cujo tipo de projeto esteja na lista.

    Exemplo:
        filtro = by_project_type(["library", "cli"])
        filtro(record)  →  True se record.project_type in {"library", "cli"}
    """
    allowed = {t.lower() for t in types}

    def predicate(record: CleanPRRecord) -> bool:
        return record.project_type.lower() in allowed

    return predicate


def by_contribution_nature(natures: list[str]) -> Predicate:
    """
    Mantém registros cuja natureza de contribuição esteja na lista.

    Naturezas típicas: "bugfix", "feature", "refactor", "docs", "chore".

    Exemplo:
        filtro = by_contribution_nature(["bugfix", "feature"])
        filtro(record)  →  True se record.contribution_nature in {"bugfix", "feature"}
    """
    allowed = {n.lower() for n in natures}

    def predicate(record: CleanPRRecord) -> bool:
        return record.contribution_nature.lower() in allowed

    return predicate


def by_clarity_level(min_clarity: int, max_clarity: int) -> Predicate:
    """
    Mantém registros cujo nível de clareza esteja dentro do intervalo [min, max].

    O nível de clareza é um inteiro (ex: 1–5), onde valores maiores
    indicam descrições mais claras e completas.

    Exemplo:
        filtro = by_clarity_level(min_clarity=3, max_clarity=5)
        filtro(record)  →  True se 3 ≤ record.clarity_level ≤ 5
    """

    def predicate(record: CleanPRRecord) -> bool:
        return min_clarity <= record.clarity_level <= max_clarity

    return predicate


def by_date_range(start: date, end: date) -> Predicate:
    """
    Mantém registros cuja data de criação esteja dentro do intervalo [start, end].

    Ambas as extremidades são inclusivas.

    Exemplo:
        filtro = by_date_range(date(2024, 1, 1), date(2024, 6, 30))
        filtro(record)  →  True se 2024-01-01 ≤ record.created_at ≤ 2024-06-30
    """

    def predicate(record: CleanPRRecord) -> bool:
        return start <= record.created_at <= end

    return predicate


def build_filter(*predicates: Predicate) -> Predicate:
    """
    Compõe múltiplos predicados em uma única função de filtro via AND.

    Um registro só passa se TODOS os predicados retornarem True.
    Se nenhum predicado for fornecido, todos os registros passam.

    Projetado para integração com a sidebar do Streamlit: o chamador
    monta a lista de predicados com base nas seleções do usuário e
    chama build_filter uma vez — sem recarregar o dataset base.

    Exemplo:
        filtro = build_filter(
            by_language(["python"]),
            by_contribution_nature(["bugfix"]),
            by_date_range(date(2024, 1, 1), date(2024, 12, 31)),
        )

        registros_filtrados = [r for r in registros if filtro(r)]
    """

    def combined(record: CleanPRRecord) -> bool:
        return all(predicate(record) for predicate in predicates)

    return combined
