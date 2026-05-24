"""
tests/test_classifiers.py
Testes unitários para services/classifiers.py

Testes das funções públicas de classificação semântica.
"""

import pytest
from core.models.pr_record import PRRecord
from services.classifiers import (
    classify_clarity,
    classify_pr_nature,
    classify_project_type,
)


def test_classify_pr_nature_returns_valid_value():
    """Testa que classify_pr_nature retorna uma string válida."""
    pr = PRRecord(
        id=1,
        html_url="https://github.com/test/repo/pull/1#discussion_r1",
        repo="test/repo",
        path="src/main.py",
        body="This fixes a critical bug in the login button.",
        diff_hunk="@@ -10,6 +10,10 @@",
        author="test_user",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=15,
        language="python",
        created_at="2024-01-01T00:00:00Z",
    )
    result = classify_pr_nature(pr)
    assert isinstance(result, str)
    assert result in [
        "bug_fix",
        "feature",
        "refactoring",
        "documentation",
        "other",
        "unknown",
    ]


def test_classify_clarity_returns_valid_value():
    """Testa que classify_clarity retorna uma string válida."""
    pr = PRRecord(
        id=1,
        html_url="https://github.com/test/repo/pull/1#discussion_r1",
        repo="test/repo",
        path="src/main.py",
        body="This fixes a critical bug in the login button.",
        diff_hunk="@@ -10,6 +10,10 @@",
        author="test_user",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=15,
        language="python",
        created_at="2024-01-01T00:00:00Z",
    )
    result = classify_clarity(pr)
    assert isinstance(result, str)
    assert result in [
        "insufficient",
        "basic",
        "good",
        "excellent",
        "other",
        "unknown",
    ]


def test_classify_project_type_returns_iterable():
    """Testa que classify_project_type retorna um iterable."""
    pr = PRRecord(
        id=1,
        html_url="https://github.com/test/repo/pull/1#discussion_r1",
        repo="test/repo",
        path="src/main.py",
        body="This fixes a critical bug in the login button.",
        diff_hunk="@@ -10,6 +10,10 @@",
        author="test_user",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=15,
        language="python",
        created_at="2024-01-01T00:00:00Z",
    )
    result = classify_project_type([pr])
    # Verifica se é iterable
    assert hasattr(result, "__iter__")
