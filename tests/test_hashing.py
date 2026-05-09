"""
tests/test_hashing.py
=====================
Testes unitários para módulo de hashing.
"""

import pytest

from core.models.pr_record import PRRecord
from utils.hashing import hash_content, hash_record


class TestHashContent:
    """Testes para hash_content()."""

    def test_hash_content_deterministic(self):
        """Mesmo conteúdo produz mesmo hash."""
        content = "exemplo de conteúdo para hash"
        hash1 = hash_content(content)
        hash2 = hash_content(content)
        assert hash1 == hash2

    def test_hash_content_different_input(self):
        """Conteúdos diferentes produzem hashes diferentes."""
        hash1 = hash_content("conteúdo 1")
        hash2 = hash_content("conteúdo 2")
        assert hash1 != hash2

    def test_hash_content_length(self):
        """Hash SHA-256 tem 64 caracteres (hex)."""
        hash_result = hash_content("teste")
        assert len(hash_result) == 64


class TestHashRecord:
    """Testes para hash_record()."""

    def test_hash_record_same_repo(self):
        """Dois PRs do mesmo repositório geram mesmo hash."""
        pr1 = PRRecord(
            id=1,
            html_url="https://github.com/repo/example/pull/10#comment-1",
            repo="repo/example",
            path="src/main.py",
            body="Descrição 1",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author1",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        pr2 = PRRecord(
            id=2,
            html_url="https://github.com/repo/example/pull/11#comment-2",
            repo="repo/example",
            path="src/other.py",
            body="Descrição 2",
            diff_hunk="@@ -20,5 +20,5 @@",
            author="author2",
            author_association="MEMBER",
            commit_id="def456",
            line=20,
            language="Python",
            created_at="2024-01-02",
        )
        assert hash_record(pr1) == hash_record(pr2)

    def test_hash_record_different_repo(self):
        """PRs de repositórios diferentes geram hashes diferentes."""
        pr1 = PRRecord(
            id=1,
            html_url="https://github.com/repo/example1/pull/10#comment-1",
            repo="repo/example1",
            path="src/main.py",
            body="Descrição",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        pr2 = PRRecord(
            id=2,
            html_url="https://github.com/repo/example2/pull/10#comment-2",
            repo="repo/example2",
            path="src/main.py",
            body="Descrição",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        assert hash_record(pr1) != hash_record(pr2)

    def test_hash_record_length(self):
        """Hash do PR é SHA-256 válido (64 caracteres)."""
        pr = PRRecord(
            id=1,
            html_url="https://github.com/repo/test/pull/10#comment-1",
            repo="repo/test",
            path="src/main.py",
            body="Body",
            diff_hunk="@@ -10,5 +10,5 @@",
            author="author",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2024-01-01",
        )
        hash_result = hash_record(pr)
        assert len(hash_result) == 64


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
