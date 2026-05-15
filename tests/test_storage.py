"""
tests/test_storage.py
=====================
Testes unitários para módulo de storage.
"""

import json
import os
import tempfile
from pathlib import Path

import pytest

from core.models.analysis_result import AnalysisResult
from core.models.pr_record import PRRecord
from services import storage


@pytest.fixture
def temp_cache_dir(monkeypatch):
    """Cria diretório temporário e configura CACHE_DIR."""
    with tempfile.TemporaryDirectory() as tmpdir:
        monkeypatch.setenv("CACHE_DIR", tmpdir)
        # Recarrega módulo para pegar nova variável de ambiente
        import importlib

        importlib.reload(storage)
        yield tmpdir


class TestGetCacheDir:
    """Testes para _get_cache_dir()."""

    def test_cache_dir_from_env(self, monkeypatch):
        """Lê CACHE_DIR do ambiente."""
        custom_cache = "/custom/cache/path"
        monkeypatch.setenv("CACHE_DIR", custom_cache)
        import importlib

        importlib.reload(storage)
        cache_dir = storage._get_cache_dir()
        # Compara como Path para ser agnóstico de plataforma
        assert cache_dir == Path(custom_cache)

    def test_cache_dir_default(self, monkeypatch):
        """Usa '.cache' como padrão se CACHE_DIR não está set."""
        monkeypatch.delenv("CACHE_DIR", raising=False)
        import importlib

        importlib.reload(storage)
        cache_dir = storage._get_cache_dir()
        assert str(cache_dir) == ".cache"


class TestHasCachedAnalysis:
    """Testes para has_cached_analysis()."""

    def test_cache_not_exists(self, temp_cache_dir):
        """Retorna False para hash não analisado."""
        assert not storage.has_cached_analysis("nonexistent_hash_123")

    def test_cache_exists_after_save(self, temp_cache_dir):
        """Retorna True após save_results()."""
        repo_hash = "test_repo_hash_abc"
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
        storage.save_results(repo_hash, [result])
        assert storage.has_cached_analysis(repo_hash)


class TestSaveAndLoadResults:
    """Testes para save_results() e load_results()."""

    def test_save_and_load_roundtrip(self, temp_cache_dir):
        """Dados salvos podem ser carregados identicamente."""
        repo_hash = "test_roundtrip"
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
        # Salva
        storage.save_results(repo_hash, [result])

        # Carrega
        loaded = list(storage.load_results(repo_hash))
        assert len(loaded) == 1
        assert loaded[0] == result

    def test_load_nonexistent_returns_empty(self, temp_cache_dir):
        """load_results() retorna gerador vazio se arquivo não existe."""
        loaded = list(storage.load_results("nonexistent"))
        assert loaded == []

    def test_save_creates_cache_dir(self, monkeypatch):
        """save_results() cria diretório de cache se não existe."""
        with tempfile.TemporaryDirectory() as tmpdir:
            custom_cache = os.path.join(tmpdir, "nonexistent", "cache")
            monkeypatch.setenv("CACHE_DIR", custom_cache)
            import importlib

            importlib.reload(storage)

            repo_hash = "test_mkdir"
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
            storage.save_results(repo_hash, [result])
            assert Path(custom_cache).exists()

    def test_save_json_format(self, temp_cache_dir):
        """Arquivo salvo é JSON válido."""
        repo_hash = "test_json_format"
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
        storage.save_results(repo_hash, [result])

        # Lê arquivo diretamente
        cache_path = storage._get_cache_dir() / f"{repo_hash}.json"
        with open(cache_path, "r") as f:
            data = json.load(f)
        assert isinstance(data, list)
        assert len(data) == 1
        assert data[0]["id"] == 1

    def test_atomic_write_pattern(self, temp_cache_dir):
        """Arquivo temporário é renomeado atomicamente."""
        repo_hash = "test_atomic"
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
        storage.save_results(repo_hash, [result])

        cache_dir = storage._get_cache_dir()
        # Verifica que arquivo final existe mas temporário não
        assert (cache_dir / f"{repo_hash}.json").exists()
        assert not (cache_dir / f"{repo_hash}.tmp.json").exists()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
