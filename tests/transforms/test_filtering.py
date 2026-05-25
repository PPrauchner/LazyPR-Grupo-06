import pytest
from typing import NamedTuple
from datetime import datetime
from core.transforms.filtering import (
    by_language,
    by_project_type,
    by_pr_nature,
    by_clarity_level,
    compose_predicates,
    apply_filters,
)


# Mock imutável simulando o PRRecord/AnalysisResult gerado pelo pipeline
class MockResult(NamedTuple):
    language: str = ""
    project_type: str = ""
    pr_nature: str = ""
    clarity_level: str = ""
    created_at: str = ""


def test_by_language_exact_match():
    """Testa correspondência exata de linguagem (case-insensitive)."""
    predicate = by_language(("Python",))

    assert predicate(MockResult(language="Python")) is True
    assert predicate(MockResult(language="python")) is True
    assert predicate(MockResult(language="PYTHON")) is True


def test_by_language_no_match():
    """Testa quando a linguagem não corresponde."""
    predicate = by_language(("Python",))

    assert predicate(MockResult(language="Java")) is False
    assert predicate(MockResult(language="")) is False


def test_by_language_multiple_options():
    """Testa que predicado aceita múltiplas linguagens."""
    predicate = by_language(("Python", "JavaScript", "Go"))

    assert predicate(MockResult(language="Python")) is True
    assert predicate(MockResult(language="javascript")) is True
    assert predicate(MockResult(language="GO")) is True
    assert predicate(MockResult(language="Java")) is False


def test_by_language_empty_tuple():
    """Testa comportamento com tupla vazia (nenhuma linguagem permitida)."""
    predicate = by_language(())

    assert predicate(MockResult(language="Python")) is False
    assert predicate(MockResult(language="Java")) is False


def test_by_project_type_single():
    """Testa filtragem por tipo único de projeto."""
    predicate = by_project_type(("library",))

    assert predicate(MockResult(project_type="library")) is True
    assert predicate(MockResult(project_type="Library")) is True
    assert predicate(MockResult(project_type="LIBRARY")) is True
    assert predicate(MockResult(project_type="framework")) is False


def test_by_project_type_multiple():
    """Testa filtragem com múltiplos tipos de projeto."""
    predicate = by_project_type(("library", "framework", "cli"))

    assert predicate(MockResult(project_type="library")) is True
    assert predicate(MockResult(project_type="framework")) is True
    assert predicate(MockResult(project_type="cli")) is True
    assert predicate(MockResult(project_type="web_app")) is False


def test_by_pr_nature_single():
    """Testa filtragem por natureza única de PR."""
    predicate = by_pr_nature(("bug_fix",))

    assert predicate(MockResult(pr_nature="bug_fix")) is True
    assert predicate(MockResult(pr_nature="BUG_FIX")) is True
    assert predicate(MockResult(pr_nature="feature")) is False


def test_by_pr_nature_multiple():
    """Testa filtragem com múltiplas naturezas."""
    predicate = by_pr_nature(("bug_fix", "feature", "refactoring"))

    assert predicate(MockResult(pr_nature="bug_fix")) is True
    assert predicate(MockResult(pr_nature="feature")) is True
    assert predicate(MockResult(pr_nature="refactoring")) is True
    assert predicate(MockResult(pr_nature="documentation")) is False


def test_by_clarity_level_single():
    """Testa filtragem por nível único de clareza."""
    predicate = by_clarity_level(("excellent",))

    assert predicate(MockResult(clarity_level="excellent")) is True
    assert predicate(MockResult(clarity_level="EXCELLENT")) is True
    assert predicate(MockResult(clarity_level="good")) is False


def test_by_clarity_level_multiple():
    """Testa filtragem com múltiplos níveis de clareza."""
    predicate = by_clarity_level(("excellent", "good"))

    assert predicate(MockResult(clarity_level="excellent")) is True
    assert predicate(MockResult(clarity_level="good")) is True
    assert predicate(MockResult(clarity_level="basic")) is False
    assert predicate(MockResult(clarity_level="insufficient")) is False


def test_compose_predicates_empty():
    """Se nenhum filtro for passado, deve aprovar tudo."""
    predicate = compose_predicates([])
    assert predicate(MockResult()) is True


def test_compose_predicates_single():
    """Testa composição com um único predicado."""
    predicates = [by_language(("Python",))]
    predicate = compose_predicates(predicates)

    assert predicate(MockResult(language="Python")) is True
    assert predicate(MockResult(language="Java")) is False


def test_compose_predicates_multiple_and_logic():
    """Valida a conjunção lógica (AND) de múltiplos filtros puros."""
    predicates = [
        by_language(("Python",)),
        by_pr_nature(("bug_fix",)),
    ]
    predicate = compose_predicates(predicates)

    # Passa em ambos
    assert predicate(MockResult(language="Python", pr_nature="bug_fix")) is True

    # Falha em natureza
    assert predicate(MockResult(language="Python", pr_nature="feature")) is False

    # Falha em linguagem
    assert predicate(MockResult(language="Java", pr_nature="bug_fix")) is False

    # Falha em ambos
    assert predicate(MockResult(language="Java", pr_nature="feature")) is False


def test_compose_predicates_three_predicates():
    """Testa composição com três predicados."""
    predicates = [
        by_language(("Python",)),
        by_project_type(("library",)),
        by_clarity_level(("good", "excellent")),
    ]
    predicate = compose_predicates(predicates)

    # Satisfaz todos
    result = MockResult(
        language="Python", project_type="library", clarity_level="good"
    )
    assert predicate(result) is True

    # Falha em um
    result_fail_language = MockResult(
        language="Java", project_type="library", clarity_level="good"
    )
    assert predicate(result_fail_language) is False


def test_compose_predicates_generator_input():
    """Testa que compose_predicates aceita geradores como entrada."""

    def predicate_generator():
        yield by_language(("Python",))
        yield by_pr_nature(("feature",))

    composed = compose_predicates(predicate_generator())

    assert (
        composed(MockResult(language="Python", pr_nature="feature")) is True
    )
    assert (
        composed(MockResult(language="Java", pr_nature="feature")) is False
    )


def test_apply_filters_lazy_evaluation():
    """Testa que apply_filters retorna um iterador (avaliação preguiçosa)."""
    predicates = [by_language(("Python",))]
    records = [
        MockResult(language="Python"),
        MockResult(language="Java"),
    ]

    result = apply_filters(predicates, records)

    # Deve retornar um filter object (iterador)
    assert isinstance(result, filter)


def test_apply_filters_filters_correctly():
    """Testa que apply_filters filtra registros corretamente."""
    predicates = [by_language(("Python",))]
    records = [
        MockResult(language="Python"),
        MockResult(language="Java"),
        MockResult(language="Python"),
    ]

    result = list(apply_filters(predicates, records))

    assert len(result) == 2
    assert all(r.language == "Python" for r in result)


def test_apply_filters_multiple_predicates():
    """Testa apply_filters com múltiplos predicados."""
    predicates = [
        by_language(("Python",)),
        by_pr_nature(("feature",)),
    ]
    records = [
        MockResult(language="Python", pr_nature="feature"),
        MockResult(language="Python", pr_nature="bug_fix"),
        MockResult(language="Java", pr_nature="feature"),
        MockResult(language="Python", pr_nature="feature"),
    ]

    result = list(apply_filters(predicates, records))

    assert len(result) == 2
    assert all(
        r.language == "Python" and r.pr_nature == "feature" for r in result
    )


def test_apply_filters_empty_results():
    """Testa apply_filters quando nenhum registro passa no filtro."""
    predicates = [by_language(("Rust",))]
    records = [
        MockResult(language="Python"),
        MockResult(language="Java"),
    ]

    result = list(apply_filters(predicates, records))

    assert len(result) == 0


def test_apply_filters_empty_predicates():
    """Testa apply_filters com predicados vazios (deve retornar todos)."""
    predicates = []
    records = [
        MockResult(language="Python"),
        MockResult(language="Java"),
    ]

    result = list(apply_filters(predicates, records))

    assert len(result) == 2