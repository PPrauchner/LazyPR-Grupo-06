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
    by_language,
    by_project_type,
    by_pr_nature,
    by_clarity_level,
    compose_predicates,
    apply_filters,
    is_in_date_range,
    is_language,
    has_project_type,
    has_pr_nature,
    has_clarity_level,
    build_filter,
)


class MockResult(NamedTuple):
    """Mock imutável simulando AnalysisResult."""

    language: str = ""
    project_type: str = ""
    pr_nature: str = ""
    clarity_level: str = ""
    created_at: str = ""


def test_is_language():
    predicate = is_language("Python")

    # Deve ser case insensitive
    assert predicate(MockResult(language="Python")) is True
    assert predicate(MockResult(language="python")) is True
    assert predicate(MockResult(language="Java")) is False


def test_has_project_type():
    predicate = has_project_type("library")

    assert predicate(MockResult(project_type="library")) is True
    assert predicate(MockResult(project_type="framework")) is False
    assert predicate(MockResult(project_type="unknown")) is False


def test_has_project_type_with_none_project_type():
    """Registro sem classificação de tipo de projeto nunca satisfaz o predicado."""
    predicate = has_project_type("library")

    assert predicate(MockResult(project_type=None)) is False


def test_has_pr_nature():
    predicate = has_pr_nature("bug_fix")

    assert predicate(MockResult(pr_nature="bug_fix")) is True
    assert predicate(MockResult(pr_nature="feature")) is False


def test_has_clarity_level():
    predicate = has_clarity_level("excellent")

    assert predicate(MockResult(clarity_level="excellent")) is True
    assert predicate(MockResult(clarity_level="insufficient")) is False


def test_is_in_date_range():
    # A comparação é lexicográfica sobre a string ISO-8601, então o limite
    # superior precisa incluir a hora para abranger o último dia inteiro.
    predicate = is_in_date_range("2025-01-01", "2025-12-31T23:59:59Z")

    # Dentro do intervalo
    assert predicate(MockResult(created_at="2025-06-15T10:00:00Z")) is True
    assert predicate(MockResult(created_at="2025-01-01T00:00:00Z")) is True
    assert predicate(MockResult(created_at="2025-12-31T23:59:59Z")) is True

    # Fora do intervalo
    assert predicate(MockResult(created_at="2024-12-31T23:59:59Z")) is False
    assert predicate(MockResult(created_at="2026-01-01T00:00:00Z")) is False


# --- Testes das funções Base do PR ---


def test_by_language_exact_match():
    predicate = by_language(("Python",))
    assert predicate(MockResult(language="Python")) is True
    assert predicate(MockResult(language="python")) is True


def test_by_language_no_match():
    predicate = by_language(("Python",))
    assert predicate(MockResult(language="Java")) is False


def test_by_language_multiple_options():
    predicate = by_language(("Python", "JavaScript", "Go"))
    assert predicate(MockResult(language="javascript")) is True
    assert predicate(MockResult(language="Java")) is False


def test_by_project_type_multiple():
    predicate = by_project_type(("library", "framework", "cli"))
    assert predicate(MockResult(project_type="library")) is True
    assert predicate(MockResult(project_type="web_app")) is False


def test_by_pr_nature_multiple():
    predicate = by_pr_nature(("bug_fix", "feature", "refactoring"))
    assert predicate(MockResult(pr_nature="bug_fix")) is True
    assert predicate(MockResult(pr_nature="documentation")) is False


def test_by_clarity_level_multiple():
    predicate = by_clarity_level(("excellent", "good"))
    assert predicate(MockResult(clarity_level="good")) is True
    assert predicate(MockResult(clarity_level="basic")) is False


# --- Testes de Composição Funcional (compose_predicates / build_filter) ---


def test_compose_predicates_empty():
    predicate = compose_predicates([])
    assert predicate(MockResult()) is True


def test_build_filter_empty():
    predicate = build_filter()
    assert predicate(MockResult()) is True


def test_build_filter_composition():
    predicate = build_filter(is_language("Python"), has_pr_nature("bug_fix"))

    assert predicate(MockResult(language="python", pr_nature="bug_fix")) is True
    assert predicate(MockResult(language="Python", pr_nature="feature")) is False
    assert predicate(MockResult(language="Java", pr_nature="bug_fix")) is False


def test_compose_predicates_generator_input():
    def predicate_generator():
        yield by_language(("Python",))
        yield by_pr_nature(("feature",))

    composed = compose_predicates(predicate_generator())
    assert composed(MockResult(language="Python", pr_nature="feature")) is True
    assert composed(MockResult(language="Java", pr_nature="feature")) is False


# --- Testes de Pipeline (apply_filters) ---


def test_apply_filters_lazy_evaluation():
    predicates = [by_language(("Python",))]
    records = [MockResult(language="Python"), MockResult(language="Java")]

    result = apply_filters(predicates, records)
    assert isinstance(result, filter)


def test_apply_filters_filters_correctly():
    predicates = [by_language(("Python",))]
    records = [
        MockResult(language="Python"),
        MockResult(language="Java"),
        MockResult(language="Python"),
    ]

    result = list(apply_filters(predicates, records))
    assert len(result) == 2
    assert all(r.language == "Python" for r in result)


def test_apply_filters_empty_predicates():
    predicates = []
    records = [MockResult(language="Python"), MockResult(language="Java")]
    result = list(apply_filters(predicates, records))
    assert len(result) == 2
