"""
Testes dos filtros globais aplicados
aos dashboards do sistema.

Valida:
    - composição funcional de predicados
    - integração entre filtros globais
    - aplicação lazy via apply_filters()
    - comportamento AND entre filtros
"""

from typing import NamedTuple

from core.transforms.filtering import (
    apply_filters,
    by_clarity_level,
    by_language,
    by_pr_nature,
    by_project_type,
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


def test_global_language_filter():
    """
    Deve filtrar registros apenas
    da linguagem selecionada.
    """

    records = (
        MockResult(language="Python"),
        MockResult(language="Java"),
    )

    filtered = tuple(
        apply_filters(
            (by_language(("Python",)),),
            records,
        )
    )

    assert len(filtered) == 1

    assert filtered[0].language == "Python"


def test_global_clarity_filter():
    """
    Deve filtrar registros apenas
    do nível de clareza selecionado.
    """

    records = (
        MockResult(clarity_level="excellent"),
        MockResult(clarity_level="poor"),
    )

    filtered = tuple(
        apply_filters(
            (by_clarity_level(("excellent",)),),
            records,
        )
    )

    assert len(filtered) == 1

    assert filtered[0].clarity_level == "excellent"


def test_global_filter_composition():
    """
    Deve aplicar composição AND
    entre múltiplos filtros globais.
    """

    records = (
        MockResult(
            language="Python",
            pr_nature="bug_fix",
        ),
        MockResult(
            language="Python",
            pr_nature="feature",
        ),
        MockResult(
            language="Java",
            pr_nature="bug_fix",
        ),
    )

    filtered = tuple(
        apply_filters(
            (
                by_language(("Python",)),
                by_pr_nature(("bug_fix",)),
            ),
            records,
        )
    )

    assert len(filtered) == 1

    assert filtered[0].language == "Python"

    assert filtered[0].pr_nature == "bug_fix"


def test_global_project_type_filter():
    """
    Deve filtrar registros apenas
    do tipo de projeto selecionado.
    """

    records = (
        MockResult(project_type="Framework"),
        MockResult(project_type="CLI"),
    )

    filtered = tuple(
        apply_filters(
            (by_project_type(("Framework",)),),
            records,
        )
    )

    assert len(filtered) == 1

    assert filtered[0].project_type == "Framework"
