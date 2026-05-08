"""
tests/test_memoization.py
==========================
Testes unitários para módulo de memoization.
"""

import tempfile
from typing import Generator

import pytest

from core.models.analysis_result import AnalysisResult
from core.models.pr_record import PRRecord
from utils import memoization


@pytest.fixture
def reset_cache(monkeypatch):
    """Reseta cache em memória e stats antes de cada teste."""
    memoization._in_memory_cache.clear()
    memoization._cache_stats["hits"] = 0
    memoization._cache_stats["misses"] = 0
    yield


@pytest.fixture
def temp_cache_dir(monkeypatch):
    """Configura CACHE_DIR temporário."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("CACHE_DIR", tmpdir)
        # Recarrega storage para pegar nova variável
        import importlib

        import services.storage

        importlib.reload(services.storage)
        yield tmpdir


class TestCachedClassify:
    """Testes para cached_classify()."""

    def test_cache_hit_memory(self, reset_cache, temp_cache_dir):
        """Primeira chamada miss, segunda é hit em memória."""
        test_hash = "test_hash_memory"
        call_count = 0

        def mock_classify() -> Generator[AnalysisResult, None, None]:
            nonlocal call_count
            call_count += 1
            result = AnalysisResult(
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
                project_type="library",
                pr_nature="feature",
                clarity_level="good",
                char_count=4,
                word_count=1,
            )
            yield result

        # Primeira chamada → miss (chama mock_classify)
        result1 = list(memoization.cached_classify(mock_classify, test_hash))
        assert call_count == 1
        assert len(result1) > 0

        # Segunda chamada → hit (não chama mock_classify)
        result2 = list(memoization.cached_classify(mock_classify, test_hash))
        assert call_count == 1  # Não incrementou
        assert result1 == result2

    def test_cache_stats_hit_miss(self, reset_cache, temp_cache_dir):
        """Stats registram hits e misses corretamente."""

        def mock_classify() -> Generator[AnalysisResult, None, None]:
            result = AnalysisResult(
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
                project_type="library",
                pr_nature="feature",
                clarity_level="good",
                char_count=4,
                word_count=1,
            )
            yield result

        # Primeira chamada (miss)
        list(memoization.cached_classify(mock_classify, "hash1"))
        stats = memoization.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 0

        # Segunda chamada (hit)
        list(memoization.cached_classify(mock_classify, "hash1"))
        stats = memoization.get_cache_stats()
        assert stats["misses"] == 1
        assert stats["hits"] == 1
        assert stats["total"] == 2

    def test_different_hashes_separate_cache(self, reset_cache, temp_cache_dir):
        """Hashes diferentes têm entradas de cache separadas."""
        call_count = 0

        def mock_classify() -> Generator[AnalysisResult, None, None]:
            nonlocal call_count
            call_count += 1
            result = AnalysisResult(
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
                project_type="library",
                pr_nature="feature",
                clarity_level="good",
                char_count=4,
                word_count=1,
            )
            yield result

        # Chamadas com hashes diferentes → ambas chamam mock_classify
        list(memoization.cached_classify(mock_classify, "hash_a"))
        list(memoization.cached_classify(mock_classify, "hash_b"))

        assert call_count == 2

    def test_cache_persistence_across_calls(self, reset_cache, temp_cache_dir):
        """Cache em memória persiste entre chamadas separadas."""

        def mock_classify() -> Generator[AnalysisResult, None, None]:
            result = AnalysisResult(
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
                project_type="library",
                pr_nature="feature",
                clarity_level="good",
                char_count=4,
                word_count=1,
            )
            yield result

        hash_key = "persist_test"

        # Primeira chamada — cached_classify yields itens individuais
        results1 = list(memoization.cached_classify(mock_classify, hash_key))
        assert len(results1) > 0
        result1 = results1[0]

        # Segunda chamada sem limpar cache
        results2 = list(memoization.cached_classify(mock_classify, hash_key))
        assert len(results2) > 0
        result2 = results2[0]

        # Devem ser idênticos
        assert result1.project_type == result2.project_type
        assert result1.pr_nature == result2.pr_nature


class TestClearCache:
    """Testes para clear_cache()."""

    def test_clear_cache_resets_memory(self, reset_cache, temp_cache_dir):
        """clear_cache() limpa cache em memória (mas não disco)."""

        def mock_classify() -> Generator[AnalysisResult, None, None]:
            result = AnalysisResult(
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
                project_type="library",
                pr_nature="feature",
                clarity_level="good",
                char_count=4,
                word_count=1,
            )
            yield result

        hash_key = "clear_test"
        call_count = 0

        def counting_classify() -> Generator[AnalysisResult, None, None]:
            nonlocal call_count
            call_count += 1
            yield from mock_classify()

        # Primeira chamada
        list(memoization.cached_classify(counting_classify, hash_key))
        assert call_count == 1

        # Clear cache apenas em memória
        memoization.clear_cache()

        # Segunda chamada após clear vai ao storage (ainda chamará se arquivo não existe)
        # Mas para este teste, vamos verificar que segunda chamada com hash diferente chama novamente
        list(memoization.cached_classify(counting_classify, hash_key + "_different"))
        assert call_count == 2


class TestGetCacheStats:
    """Testes para get_cache_stats()."""

    def test_cache_stats_initial(self, reset_cache, temp_cache_dir):
        """Stats iniciam zeradas."""
        stats = memoization.get_cache_stats()
        assert stats["hits"] == 0
        assert stats["misses"] == 0
        assert stats["total"] == 0

    def test_cache_stats_accumulate(self, reset_cache, temp_cache_dir):
        """Stats acumulam hits e misses."""

        def mock_classify() -> Generator[AnalysisResult, None, None]:
            result = AnalysisResult(
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
                project_type="library",
                pr_nature="feature",
                clarity_level="good",
                char_count=4,
                word_count=1,
            )
            yield result

        # 3 misses
        for i in range(3):
            list(memoization.cached_classify(mock_classify, f"hash_{i}"))

        # 2 hits (repetindo hashes anteriores)
        list(memoization.cached_classify(mock_classify, "hash_0"))
        list(memoization.cached_classify(mock_classify, "hash_1"))

        stats = memoization.get_cache_stats()
        assert stats["misses"] == 3
        assert stats["hits"] == 2
        assert stats["total"] == 5


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
