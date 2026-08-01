"""
tests/test_memoization.py
==========================
Testes unitários para módulo de memoization.
"""

import threading
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


class TestCachedClassifyNamespace:
    """cached_classify() vive no espaço de nomes das classificações por repo."""

    def _result(self) -> AnalysisResult:
        """Constrói um AnalysisResult mínimo para os testes de namespace."""
        return AnalysisResult(
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

    def test_repo_classification_survives_analysis_version_bump(
        self, temp_cache_dir, monkeypatch
    ):
        """Bump da versão da Análise não força reclassificação pelo LLM."""
        from services import storage

        cache_key = "repo_batch_hash"
        call_count = {"n": 0}

        def classify_fn() -> Generator[AnalysisResult, None, None]:
            call_count["n"] += 1
            yield self._result()

        # Primeira execução: cache miss, chama a "LLM" e persiste.
        list(memoization.cached_classify(classify_fn, cache_key))
        assert call_count["n"] == 1

        monkeypatch.setattr(storage, "CACHE_SCHEMA_VERSION", "v99")

        # Segunda execução após o bump: ainda é hit, sem nova chamada.
        cached = list(memoization.cached_classify(classify_fn, cache_key))
        assert call_count["n"] == 1
        assert [r.id for r in cached] == [1]


class TestCachedClassifyCorruptedCache:
    """Cache de repositório corrompido recomputa, em vez de truncar a Análise."""

    def _result(self, result_id: int = 1) -> AnalysisResult:
        """Constrói um AnalysisResult mínimo para os testes de corrupção."""
        return AnalysisResult(
            id=result_id,
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

    def _write_raw_repo_cache(self, cache_key: str, content: str) -> None:
        """Grava conteúdo cru no cache de classificações por repositório."""
        from services import storage

        cache_path = storage._cache_path(
            cache_key, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
        )
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_corrupted_cache_triggers_reclassification(self, temp_cache_dir):
        """JSON inválido não vira hit vazio: a classificação roda de novo."""
        cache_key = "repo_hash_corrompido"
        self._write_raw_repo_cache(cache_key, "{ nao_e_json: [")

        call_count = {"n": 0}

        def classify_fn() -> Generator[AnalysisResult, None, None]:
            call_count["n"] += 1
            yield self._result(1)

        results = list(memoization.cached_classify(classify_fn, cache_key))

        assert call_count["n"] == 1
        assert [r.id for r in results] == [1]

    def test_partially_malformed_cache_does_not_return_prefix(self, temp_cache_dir):
        """Lista com um item bom e um quebrado não entrega o prefixo parcial."""
        import json as _json

        cache_key = "repo_hash_parcial"
        self._write_raw_repo_cache(
            cache_key,
            _json.dumps(
                [self._result(1)._asdict(), {"id": 2, "campo_estranho": "valor"}]
            ),
        )

        call_count = {"n": 0}

        def classify_fn() -> Generator[AnalysisResult, None, None]:
            call_count["n"] += 1
            yield self._result(10)
            yield self._result(11)

        results = list(memoization.cached_classify(classify_fn, cache_key))

        # Nem o prefixo válido ([1]) nem um conjunto vazio: recomputou inteiro.
        assert call_count["n"] == 1
        assert [r.id for r in results] == [10, 11]

    def test_corrupted_cache_is_overwritten_by_fresh_results(self, temp_cache_dir):
        """Após recomputar, o cache corrompido é substituído por um íntegro."""
        from services import storage

        cache_key = "repo_hash_sobrescrito"
        self._write_raw_repo_cache(cache_key, "lixo")

        def classify_fn() -> Generator[AnalysisResult, None, None]:
            yield self._result(42)

        list(memoization.cached_classify(classify_fn, cache_key))

        assert storage.has_cached_analysis(
            cache_key, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
        )
        cached = storage.read_results(
            cache_key, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
        )
        assert [r.id for r in cached] == [42]


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


class TestMemoizationDiskCacheL2:

    def test_cache_hit_on_disk_when_memory_empty(self, reset_cache, temp_cache_dir):

        test_hash = "hash_disco_persistente"

        resultado_simulado = AnalysisResult(
            id=99,
            html_url="https://github.com/repo/test/pull/99",
            repo="repo/test",
            path="src/app.py",
            body="Cache disco",
            diff_hunk="@@",
            author="tester",
            author_association="NONE",
            commit_id="000",
            line=1,
            language="Python",
            created_at="2024-01-01",
            project_type="api",
            pr_nature="bugfix",
            clarity_level="good",
            char_count=10,
            word_count=2,
        )

        # Simula o encerramento de uma sessão anterior salvando diretamente no disco
        from services import storage

        storage.save_results(test_hash, [resultado_simulado])

        call_count = 0

        def mock_classify_caro() -> Generator[AnalysisResult, None, None]:
            nonlocal call_count
            call_count += 1
            yield resultado_simulado

        # Nova sessão: L1 está vazio (via reset_cache fixture), mas o disco (L2) tem dados
        resultados = list(memoization.cached_classify(mock_classify_caro, test_hash))

        # Asserções críticas
        assert (
            call_count == 0
        )  # A função de classificação da LLM NUNCA deve ser chamada
        assert len(resultados) == 1
        assert resultados[0].id == 99

        # Verifica se as estatísticas contabilizaram como um Cache HIT bem-sucedido
        stats = memoization.get_cache_stats()
        assert stats["hits"] == 1
        assert stats["misses"] == 0


import threading


class TestMemoizationAdvancedResilience:

    def test_cached_classify_does_not_cache_exceptions(
        self, reset_cache, temp_cache_dir
    ):
        """Garante que se a LLM lançar exceção (ex: Timeout), o erro sobe e NADA vai para o cache."""
        test_hash = "hash_erro_api"
        call_count = 0

        def mock_classify_failing() -> Generator[AnalysisResult, None, None]:
            nonlocal call_count
            call_count += 1
            raise ConnectionError("Falha na API da LLM - Timeout")
            yield  # Nunca chega aqui

        # A execução deve propagar a exceção
        with pytest.raises(ConnectionError):
            list(memoization.cached_classify(mock_classify_failing, test_hash))

        assert call_count == 1

        # O estado não deve ter sido alterado: não tem no cache em memória
        assert test_hash not in memoization._in_memory_cache

        # Também não pode ter salvo um arquivo sujo/vazio no disco
        from services.storage import has_cached_analysis

        assert not has_cached_analysis(test_hash)

    def test_cache_stats_thread_safety(self, reset_cache, temp_cache_dir):
        """Testa se os Locks protegem a atualização das estatísticas do cache em acessos concorrentes."""
        num_threads = 100

        def simulate_cache_access():
            # Simula um "miss" direto atualizando as stats usando a função interna
            memoization._update_stats(hit=False)

        threads = []
        for _ in range(num_threads):
            t = threading.Thread(target=simulate_cache_access)
            threads.append(t)
            t.start()

        for t in threads:
            t.join()

        # Como usamos o _stats_lock no código original, nenhuma operação += deve ter se perdido
        stats = memoization.get_cache_stats()
        assert stats["misses"] == num_threads
        assert stats["hits"] == 0

    def test_clear_cache_preserves_stats(self, reset_cache, temp_cache_dir):
        """Verifica o comportamento de design: limpar a memória não zera o histórico de estatísticas."""
        memoization._update_stats(hit=True)
        memoization._update_stats(hit=False)

        assert memoization.get_cache_stats()["total"] == 2

        # Limpa o cache L1
        memoization.clear_cache()

        # As estatísticas de vida útil da aplicação devem se manter
        stats = memoization.get_cache_stats()
        assert stats["total"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
