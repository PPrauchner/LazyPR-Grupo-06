import pytest
from typing import NamedTuple
from core.transforms.filtering import (
    is_language,
    has_project_type,
    has_pr_nature,
    has_clarity_level,
    is_in_date_range,
    build_filter
)

# Mock imutável simulando o PRRecord/AnalysisResult gerado pelo pipeline
class MockResult(NamedTuple):
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
    assert predicate(MockResult()) is False  # Comportamento seguro com atributo vazio

def test_has_project_type():
    predicate = has_project_type("biblioteca")
    
    assert predicate(MockResult(project_type="biblioteca")) is True
    assert predicate(MockResult(project_type="framework")) is False

def test_has_pr_nature():
    predicate = has_pr_nature("bug_fix")
    
    assert predicate(MockResult(pr_nature="bug_fix")) is True
    assert predicate(MockResult(pr_nature="feature")) is False

def test_has_clarity_level():
    predicate = has_clarity_level("excelente")
    
    assert predicate(MockResult(clarity_level="excelente")) is True
    assert predicate(MockResult(clarity_level="insuficiente")) is False

def test_is_in_date_range():
    predicate = is_in_date_range("2025-01-01", "2025-12-31")
    
    # Dentro do intervalo
    assert predicate(MockResult(created_at="2025-06-15T10:00:00Z")) is True
    assert predicate(MockResult(created_at="2025-01-01T00:00:00Z")) is True
    assert predicate(MockResult(created_at="2025-12-31T23:59:59Z")) is True
    
    # Fora do intervalo
    assert predicate(MockResult(created_at="2024-12-31T23:59:59Z")) is False
    assert predicate(MockResult(created_at="2026-01-01T00:00:00Z")) is False

def test_build_filter_empty():
    """Se nenhum filtro for passado, deve aprovar tudo."""
    predicate = build_filter()
    assert predicate(MockResult()) is True

def test_build_filter_composition():
    """Valida a conjunção lógica (AND) de múltiplos filtros puros."""
    predicate = build_filter(
        is_language("Python"),
        has_pr_nature("bug_fix")
    )
    
    # Passa em ambos
    assert predicate(MockResult(language="python", pr_nature="bug_fix")) is True
    
    # Falha em um (Natureza diferente)
    assert predicate(MockResult(language="Python", pr_nature="feature")) is False
    
    # Falha no outro (Linguagem diferente)
    assert predicate(MockResult(language="Java", pr_nature="bug_fix")) is False