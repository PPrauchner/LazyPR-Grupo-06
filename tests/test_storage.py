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
        cache_path = storage._cache_path(repo_hash)
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
        assert storage._cache_path(repo_hash).exists()
        assert not storage._cache_path(repo_hash, suffix="tmp.json").exists()


class TestStorageEdgeCases:

    def test_load_corrupted_json_returns_empty(self, temp_cache_dir):
        """load_results() ignora arquivos com JSON malformado e retorna gerador vazio."""
        repo_hash = "corrupted_json_test"
        cache_path = storage._cache_path(repo_hash)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # Cria um arquivo com JSON inválido intencionalmente
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write("{ json_invalido: [ ")

        # A função deve engolir o JSONDecodeError e retornar vazio
        loaded = list(storage.load_results(repo_hash))
        assert loaded == []

    def test_load_invalid_schema_returns_empty(self, temp_cache_dir):
        """load_results() trata TypeError ao instanciar AnalysisResult com dados incompletos."""
        repo_hash = "invalid_schema_test"
        cache_path = storage._cache_path(repo_hash)
        cache_path.parent.mkdir(parents=True, exist_ok=True)

        # JSON válido, mas não possui os atributos necessários para AnalysisResult
        with open(cache_path, "w", encoding="utf-8") as f:
            json.dump([{"id": 1, "campo_estranho": "valor"}], f)

        # A função deve engolir o TypeError do destructuring (**) e retornar vazio
        loaded = list(storage.load_results(repo_hash))
        assert loaded == []

    def test_has_cached_analysis_is_not_file(self, temp_cache_dir):
        """has_cached_analysis() retorna False se o path existir mas for um diretório."""
        repo_hash = "dir_hash_test"
        cache_dir = storage._get_cache_dir()

        # Cria um diretório com o mesmo nome que o arquivo de cache teria
        fake_file_dir = storage._cache_path(repo_hash)
        fake_file_dir.mkdir(parents=True, exist_ok=True)

        # Deve retornar False pois o método exige is_file()
        assert not storage.has_cached_analysis(repo_hash)


class TestCorruptedCacheIsMiss:
    """Cache ilegível degrada para miss — nunca vira hit truncado."""

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

    def _write_raw(self, repo_hash: str, content: str) -> None:
        """Grava conteúdo cru no arquivo de cache da Análise."""
        cache_path = storage._cache_path(repo_hash)
        cache_path.parent.mkdir(parents=True, exist_ok=True)
        with open(cache_path, "w", encoding="utf-8") as f:
            f.write(content)

    def test_corrupted_json_is_not_a_cache_hit(self, temp_cache_dir):
        """JSON inválido não pode passar por hit: o chamador deve recomputar."""
        repo_hash = "hash_json_corrompido"
        self._write_raw(repo_hash, "{ json_invalido: [ ")

        assert not storage.has_cached_analysis(repo_hash)
        assert storage.read_results(repo_hash) is None

    def test_partially_malformed_list_is_not_a_cache_hit(self, temp_cache_dir):
        """Um item bom e um quebrado invalidam o cache inteiro, não meio dele."""
        repo_hash = "hash_lista_parcial"
        self._write_raw(
            repo_hash,
            json.dumps(
                [self._result(1)._asdict(), {"id": 2, "campo_estranho": "valor"}]
            ),
        )

        assert not storage.has_cached_analysis(repo_hash)
        assert storage.read_results(repo_hash) is None

    def test_partially_malformed_list_yields_no_partial_prefix(self, temp_cache_dir):
        """load_results() não entrega o prefixo válido de um cache corrompido."""
        repo_hash = "hash_sem_prefixo"
        self._write_raw(
            repo_hash,
            json.dumps(
                [self._result(1)._asdict(), {"id": 2, "campo_estranho": "valor"}]
            ),
        )

        assert list(storage.load_results(repo_hash)) == []

    def test_non_list_payload_is_not_a_cache_hit(self, temp_cache_dir):
        """JSON válido que não é lista também é miss, não hit vazio."""
        repo_hash = "hash_objeto_no_lugar_de_lista"
        self._write_raw(repo_hash, json.dumps({"nao": "e uma lista"}))

        assert not storage.has_cached_analysis(repo_hash)

    def test_valid_cache_still_reads_as_hit(self, temp_cache_dir):
        """A validação não pode transformar cache íntegro em miss."""
        repo_hash = "hash_integro"
        storage.save_results(repo_hash, [self._result(7)])

        assert storage.has_cached_analysis(repo_hash)
        assert [r.id for r in storage.read_results(repo_hash)] == [7]


class TestSchemaVersionNamespaces:
    """_schema_version() não tem fallback mudo."""

    def test_known_namespaces_map_to_own_versions(self):
        """Cada namespace conhecido devolve a própria versão de esquema."""
        assert (
            storage._schema_version(storage.ANALYSIS_NAMESPACE)
            == storage.CACHE_SCHEMA_VERSION
        )
        assert (
            storage._schema_version(storage.REPO_CLASSIFICATION_NAMESPACE)
            == storage.REPO_CLASSIFICATION_SCHEMA_VERSION
        )

    def test_unknown_namespace_raises(self):
        """Namespace desconhecido falha alto em vez de herdar outra versão."""
        with pytest.raises(KeyError):
            storage._schema_version("namespace-inexistente")


class TestStorageEmptyStates:

    def test_save_and_load_empty_results_list(self, temp_cache_dir):
        """O storage deve conseguir salvar um array vazio [] validamente e recuperar sem falhas."""
        repo_hash = "empty_list_hash"

        # Persiste uma lista vazia
        storage.save_results(repo_hash, [])

        # Verifica se o arquivo foi de fato criado (o cache hit do runner depende de arquivo existir)
        assert storage.has_cached_analysis(repo_hash)

        # Recupera os dados
        loaded = list(storage.load_results(repo_hash))

        # Deve retornar uma lista vazia, não None ou erro
        assert loaded == []
        assert len(loaded) == 0

    def test_get_cache_dir_creates_path_if_missing(self, monkeypatch):
        """Valida que o diretório base de cache consegue ser montado a partir do FileSystem."""
        custom_dir = "pasta_de_cache_estranha/subpasta"
        monkeypatch.setenv("CACHE_DIR", custom_dir)
        import importlib

        importlib.reload(storage)

        cache_path = storage._get_cache_dir()
        assert cache_path.name == "subpasta"
        assert cache_path.parent.name == "pasta_de_cache_estranha"


class TestCacheNamespaces:
    """Isolamento entre a Análise do dataset e as classificações por repositório."""

    def _result(self, result_id: int = 1) -> AnalysisResult:
        """Constrói um AnalysisResult mínimo para os testes de namespace."""
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

    def test_analysis_version_bump_preserves_repo_classification_cache(
        self, temp_cache_dir, monkeypatch
    ):
        """Versionar só a Análise não invalida as classificações por repositório."""
        shared_hash = "hash_compartilhado"
        storage.save_results(shared_hash, [self._result()])
        storage.save_results(
            shared_hash,
            [self._result(2)],
            namespace=storage.REPO_CLASSIFICATION_NAMESPACE,
        )

        monkeypatch.setattr(storage, "CACHE_SCHEMA_VERSION", "v99")

        assert not storage.has_cached_analysis(shared_hash)
        assert storage.has_cached_analysis(
            shared_hash, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
        )
        loaded = list(
            storage.load_results(
                shared_hash, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
            )
        )
        assert [r.id for r in loaded] == [2]

    def test_same_hash_in_both_namespaces_does_not_collide(self, temp_cache_dir):
        """O mesmo hash grava conteúdos distintos em cada espaço de nomes."""
        shared_hash = "hash_compartilhado"
        storage.save_results(shared_hash, [self._result(1)])
        storage.save_results(
            shared_hash,
            [self._result(2)],
            namespace=storage.REPO_CLASSIFICATION_NAMESPACE,
        )

        analysis_ids = [r.id for r in storage.load_results(shared_hash)]
        repo_ids = [
            r.id
            for r in storage.load_results(
                shared_hash, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
            )
        ]
        assert analysis_ids == [1]
        assert repo_ids == [2]

    def test_atomic_write_leaves_no_temp_file_in_either_namespace(self, temp_cache_dir):
        """A escrita atômica não deixa `.tmp.json` residual em nenhum namespace."""
        shared_hash = "hash_atomico"
        storage.save_results(shared_hash, [self._result()])
        storage.save_results(
            shared_hash,
            [self._result()],
            namespace=storage.REPO_CLASSIFICATION_NAMESPACE,
        )

        for namespace in (
            storage.ANALYSIS_NAMESPACE,
            storage.REPO_CLASSIFICATION_NAMESPACE,
        ):
            assert storage._cache_path(shared_hash, namespace=namespace).exists()
            assert not storage._cache_path(
                shared_hash, suffix="tmp.json", namespace=namespace
            ).exists()


class TestPromptVersionInvalidatesBothNamespaces:
    """A versão de prompt é a segunda dimensão do nome de arquivo do cache.

    Versão de esquema (formato de armazenamento) e versão de prompt (rubrica)
    são independentes: bumpar uma não pode mexer no que a outra invalida.
    Mudar a rubrica contamina os dois espaços de nomes, porque o
    `clarity_level` produzido por ela mora nos dois (issue #85).
    """

    def _result(self, result_id: int = 1) -> AnalysisResult:
        """Constrói um AnalysisResult mínimo para os testes de versão."""
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

    def test_cache_file_name_carries_both_versions(self, temp_cache_dir):
        """O nome do arquivo traz versão de esquema e versão de prompt."""
        from services.prompt_version import PROMPT_VERSION

        for namespace in (
            storage.ANALYSIS_NAMESPACE,
            storage.REPO_CLASSIFICATION_NAMESPACE,
        ):
            name = storage._cache_path("abc", namespace=namespace).name
            assert name == (
                f"{storage._schema_version(namespace)}-{PROMPT_VERSION}-abc.json"
            )

    def test_prompt_version_bump_invalidates_both_namespaces(
        self, temp_cache_dir, monkeypatch
    ):
        """Trocar a versão de prompt derruba a Análise e as classificações."""
        shared_hash = "hash_compartilhado"
        storage.save_results(shared_hash, [self._result()])
        storage.save_results(
            shared_hash,
            [self._result(2)],
            namespace=storage.REPO_CLASSIFICATION_NAMESPACE,
        )

        monkeypatch.setattr(storage, "PROMPT_VERSION", "p99")

        assert not storage.has_cached_analysis(shared_hash)
        assert not storage.has_cached_analysis(
            shared_hash, namespace=storage.REPO_CLASSIFICATION_NAMESPACE
        )

    def test_schema_version_bump_does_not_move_the_prompt_dimension(
        self, temp_cache_dir, monkeypatch
    ):
        """As duas dimensões são independentes: uma não arrasta a outra."""
        monkeypatch.setattr(storage, "CACHE_SCHEMA_VERSION", "v99")
        monkeypatch.setattr(storage, "PROMPT_VERSION", "p7")

        assert (
            storage._cache_path("abc", namespace=storage.ANALYSIS_NAMESPACE).name
            == "v99-p7-abc.json"
        )
        assert (
            storage._cache_path(
                "abc", namespace=storage.REPO_CLASSIFICATION_NAMESPACE
            ).name
            == f"{storage.REPO_CLASSIFICATION_SCHEMA_VERSION}-p7-abc.json"
        )

    def test_prompt_version_module_imports_nothing(self):
        """`prompt_version` é neutro: não importa nada, logo não exige Agno.

        Se ele importasse `llm_client` — que levanta `ImportError` sem o Agno —
        todo teste de storage passaria a depender da biblioteca de LLM.
        """
        import ast
        import inspect

        from services import prompt_version

        tree = ast.parse(inspect.getsource(prompt_version))
        imports = [
            node
            for node in ast.walk(tree)
            if isinstance(node, (ast.Import, ast.ImportFrom))
        ]
        assert imports == []


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
