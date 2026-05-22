"""
Testes unitários dos predicados funcionais utilizados
no sistema de filtragem global do dashboard.

Responsabilidades:
    - Validar filtros por:
        * linguagem
        * tipo de projeto
        * natureza da contribuição
        * nível de clareza
        * intervalo de datas
    - Validar composição funcional de predicados
    - Garantir aplicação lazy dos filtros
    - Preservar comportamento determinístico

Não deve:
    - Realizar I/O
    - Inicializar Streamlit
    - Modificar registros
"""

from typing import NamedTuple

from core.transforms.filtering import (
    apply_filters,
    by_clarity_level,
    by_language,
    by_pr_nature,
    by_project_type,
    compose_predicates,
    is_in_date_range,
)


class MockResult(NamedTuple):
    """
    Mock imutável simulando AnalysisResult.
    """

    language: str = ""
    project_type: str = ""
    pr_nature: str = ""
    clarity_level: str = ""
    created_at: str = ""


def test_by_language():
    """
    Valida filtro funcional por linguagem.
    """

    predicate = by_language(
        ("python",),
    )

    assert predicate(
        MockResult(language="Python")
    ) is True

    assert predicate(
        MockResult(language="python")
    ) is True

    assert predicate(
        MockResult(language="Java")
    ) is False


def test_by_project_type():
    """
    Valida filtro funcional por tipo de projeto.
    """

    predicate = by_project_type(
        ("framework",),
    )

    assert predicate(
        MockResult(project_type="framework")
    ) is True

    assert predicate(
        MockResult(project_type="library")
    ) is False


def test_by_pr_nature():
    """
    Valida filtro funcional por natureza do PR.
    """

    predicate = by_pr_nature(
        ("bug_fix",),
    )

    assert predicate(
        MockResult(pr_nature="bug_fix")
    ) is True

    assert predicate(
        MockResult(pr_nature="feature")
    ) is False


def test_by_clarity_level():
    """
    Valida filtro funcional por nível de clareza.
    """

    predicate = by_clarity_level(
        ("good",),
    )

    assert predicate(
        MockResult(clarity_level="good")
    ) is True

    assert predicate(
        MockResult(clarity_level="poor")
    ) is False


def test_is_in_date_range():
    """
    Valida filtro funcional por intervalo de datas.
    """

    predicate = is_in_date_range(
        "2025-01-01",
        "2025-12-31",
    )

    assert predicate(
        MockResult(
            created_at="2025-06-15",
        )
    ) is True

    assert predicate(
        MockResult(
            created_at="2024-01-01",
        )
    ) is False


def test_compose_predicates():
    """
    Valida composição funcional de predicados.
    """

    predicate = compose_predicates(
        (
            by_language(("python",)),
            by_pr_nature(("bug_fix",)),
        )
    )

    assert predicate(
        MockResult(
            language="python",
            pr_nature="bug_fix",
        )
    ) is True

    assert predicate(
        MockResult(
            language="java",
            pr_nature="bug_fix",
        )
    ) is False


def test_apply_filters():
    """
    Valida aplicação lazy de filtros.
    """

    records = (
        MockResult(language="Python"),
        MockResult(language="Java"),
    )

    filtered = apply_filters(
        (
            by_language(("python",)),
        ),
        records,
    )

    filtered_records = tuple(filtered)

    assert len(filtered_records) == 1

    assert (
        filtered_records[0].language
        == "Python"
    )