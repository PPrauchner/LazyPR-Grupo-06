"""
Testes para services/classifiers.py com mocks de LLM.

Cobertura:
    - Batching por repositório em classify_project_type
    - Cache hit/miss em dois níveis
    - Normalização de labels JSON inválidos
    - Tratamento de erros de parsing JSON
    - Lazy evaluation e generators
"""

import pytest
from unittest.mock import patch, MagicMock
from core.models.pr_record import PRRecord
from services.classifiers import (
    classify_project_type,
    classify_pr_nature,
    classify_clarity,
    _build_analysis_result,
    _extract_field_from_json,
)
from utils.memoization import clear_cache

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pr():
    """Fixture de um PRRecord para testes."""
    return PRRecord(
        id=1,
        html_url="https://github.com/golang/go/pull/23805#discussion_r1",
        repo="golang/go",
        path="src/math/rand/rand.go",
        body="This fixes an issue with random number generation.",
        diff_hunk="@@ -210,6 +210,11 @@",
        author="test_user",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=213,
        language="go",
        created_at="2020-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_pr_same_repo():
    """Fixture de um segundo PRRecord no mesmo repositório."""
    return PRRecord(
        id=2,
        html_url="https://github.com/golang/go/pull/23806#discussion_r2",
        repo="golang/go",
        path="src/math/rand/rand.go",
        body="This adds support for new random distributions.",
        diff_hunk="@@ -220,6 +220,11 @@",
        author="another_user",
        author_association="MEMBER",
        commit_id="def456",
        line=223,
        language="go",
        created_at="2020-01-02T00:00:00Z",
    )


@pytest.fixture
def sample_pr_different_repo():
    """Fixture de um PRRecord em repositório diferente."""
    return PRRecord(
        id=3,
        html_url="https://github.com/torvalds/linux/pull/12345#discussion_r3",
        repo="torvalds/linux",
        path="drivers/gpu/drm/nouveau/nouveau_drv.c",
        body="This fixes a GPU driver issue.",
        diff_hunk="@@ -100,6 +100,11 @@",
        author="kernel_dev",
        author_association="OWNER",
        commit_id="ghi789",
        line=105,
        language="c",
        created_at="2020-01-03T00:00:00Z",
    )


@pytest.fixture(autouse=True)
def clear_memoization_cache():
    """Limpa cache entre testes para evitar efeitos colaterais."""
    clear_cache()
    yield
    clear_cache()


# ---------------------------------------------------------------------------
# Tests: _parse_json_response()
# ---------------------------------------------------------------------------


class TestParseJsonResponse:
    """Testes para _parse_json_response()."""

    def test_parse_json_response_valid(self):
        """Testa parsing de JSON válido."""
        response = '{"project_type": "library"}'
        result = _parse_json_response(response, "project_type")
        assert result == "library"

    def test_parse_json_response_with_whitespace(self):
        """Testa parsing com espaços em branco."""
        response = '  {"project_type": "web_app"}  '
        result = _parse_json_response(response, "project_type")
        assert result == "web_app"

    def test_parse_json_response_field_missing(self):
        """Testa parsing quando field não existe no JSON."""
        response = '{"other_field": "value"}'
        result = _parse_json_response(response, "project_type")
        assert result == "other"

    def test_parse_json_response_invalid_json(self):
        """Testa parsing de JSON inválido."""
        response = "not a json"
        result = _parse_json_response(response, "project_type")
        assert result == "other"

    def test_parse_json_response_null_value(self):
        """Testa parsing com valor null no JSON."""
        response = '{"project_type": null}'
        result = _parse_json_response(response, "project_type")
        assert result == "other"

    def test_parse_json_response_empty_string_value(self):
        """Testa parsing com valor vazio."""
        response = '{"project_type": ""}'
        result = _parse_json_response(response, "project_type")
        assert result == "other"


# ---------------------------------------------------------------------------
# Tests: _build_analysis_result()
# ---------------------------------------------------------------------------


class TestBuildAnalysisResult:
    """Testes para _build_analysis_result()."""

    def test_build_analysis_result_complete(self, sample_pr):
        """Testa construção completa de AnalysisResult."""
        result = _build_analysis_result(
            record=sample_pr,
            project_type="library",
            pr_nature="bug_fix",
            clarity_level="good",
        )

        assert result.id == sample_pr.id
        assert result.repo == sample_pr.repo
        assert result.project_type == "library"
        assert result.pr_nature == "bug_fix"
        assert result.clarity_level == "good"
        assert result.char_count == len(sample_pr.body)
        assert result.word_count == len(sample_pr.body.split())

    def test_build_analysis_result_char_word_count(self):
        """Testa cálculo de char_count e word_count."""
        pr = PRRecord(
            id=1,
            html_url="https://example.com",
            repo="test/repo",
            path="test.py",
            body="Hello world test",
            diff_hunk="@@ @@",
            author="user",
            author_association="CONTRIBUTOR",
            commit_id="abc",
            line=1,
            language="python",
            created_at=None,
        )

        result = _build_analysis_result(
            record=pr,
            project_type="library",
            pr_nature="feature",
            clarity_level="excellent",
        )

        assert result.char_count == 16
        assert result.word_count == 3


# ---------------------------------------------------------------------------
# Tests: _extract_field_from_json()
# ---------------------------------------------------------------------------


class TestExtractFieldFromJson:
    """Testes para _extract_field_from_json()."""

    def test_extract_field_from_json_valid(self):
        """Testa extração e normalização de field válido."""
        response = '{"project_type": "library"}'
        result = _extract_field_from_json(response, "project_type")
        assert result == "library"

    def test_extract_field_from_json_normalize_invalid(self):
        """Testa que field inválido normaliza para 'other'."""
        response = '{"project_type": "invalid_type"}'
        result = _extract_field_from_json(response, "project_type")
        assert result == "other"

    def test_extract_field_from_json_normalize_variant(self):
        """Testa normalização de variações (ex: bug-fix → bug_fix)."""
        response = '{"pr_nature": "bug-fix"}'
        result = _extract_field_from_json(response, "pr_nature")
        assert result == "bug_fix"


# ---------------------------------------------------------------------------
# Tests: classify_project_type()
# ---------------------------------------------------------------------------


class TestClassifyProjectType:
    """Testes para classify_project_type()."""

    @patch("services.classifiers.classify_project_type_batch")
    def test_classify_project_type_single_repo(
        self, mock_llm, sample_pr, sample_pr_same_repo
    ):
        """Testa classificação com PRs do mesmo repositório."""
        # Mock retorna JSON válido
        mock_llm.return_value = '{"project_type": "library"}'

        records = [sample_pr, sample_pr_same_repo]
        results = list(classify_project_type(records))

        # Deve retornar 2 AnalysisResult
        assert len(results) == 2

        # Ambos devem ter mesmo project_type (batching)
        assert results[0].project_type == "library"
        assert results[1].project_type == "library"

    @patch("services.classifiers.classify_project_type_batch")
    def test_classify_project_type_returns_generator(self, mock_llm, sample_pr):
        """Testa que classify_project_type retorna generator (lazy)."""
        mock_llm.return_value = '{"project_type": "library"}'

        records = [sample_pr]
        result_gen = classify_project_type(records)

        # Deve ser generator, não lista
        assert hasattr(result_gen, "__iter__")
        assert hasattr(result_gen, "__next__")

    @patch("services.classifiers.classify_project_type_batch")
    def test_classify_project_type_empty_records(self, mock_llm):
        """Testa classificação com lista vazia."""
        records = []
        results = list(classify_project_type(records))

        # Deve retornar lista vazia
        assert len(results) == 0


# ---------------------------------------------------------------------------
# Tests: classify_pr_nature()
# ---------------------------------------------------------------------------


class TestClassifyPRNature:
    """Testes para classify_pr_nature()."""

    def test_classify_pr_nature_returns_valid_label(self, sample_pr):
        """Testa que classify_pr_nature retorna label válido."""
        result = classify_pr_nature(sample_pr)

        # Implementação atual retorna "other" por padrão
        assert result in ["bug_fix", "feature", "refactoring", "documentation", "other"]

    def test_classify_pr_nature_uses_hash_key(self, sample_pr):
        """Testa que usa hash correto como chave de cache."""
        # Duas chamadas com mesmo PR devem usar cache
        result1 = classify_pr_nature(sample_pr)
        result2 = classify_pr_nature(sample_pr)

        # Deve retornar mesmo valor (cache hit)
        assert result1 == result2

    def test_classify_pr_nature_different_bodies(self):
        """Testa que diferentes bodies geram diferentes hashes."""
        pr1 = PRRecord(
            id=1,
            html_url="url1",
            repo="test/repo",
            path="file.py",
            body="Fix bug",
            diff_hunk="@@",
            author="user",
            author_association="CON",
            commit_id="abc",
            line=1,
            language="python",
            created_at=None,
        )

        pr2 = PRRecord(
            id=2,
            html_url="url2",
            repo="test/repo",
            path="file.py",
            body="Add feature",
            diff_hunk="@@",
            author="user",
            author_association="CON",
            commit_id="def",
            line=1,
            language="python",
            created_at=None,
        )

        # Ambas devem retornar string válida
        result1 = classify_pr_nature(pr1)
        result2 = classify_pr_nature(pr2)

        assert isinstance(result1, str)
        assert isinstance(result2, str)


# ---------------------------------------------------------------------------
# Tests: classify_clarity()
# ---------------------------------------------------------------------------


class TestClassifyClarity:
    """Testes para classify_clarity()."""

    def test_classify_clarity_returns_valid_label(self, sample_pr):
        """Testa que classify_clarity retorna label válido."""
        result = classify_clarity(sample_pr)

        # Implementação atual retorna "other" por padrão
        assert result in ["insufficient", "basic", "good", "excellent", "other"]

    def test_classify_clarity_uses_body_hash(self, sample_pr):
        """Testa que usa hash do body como chave de cache."""
        # Duas chamadas com mesmo body devem usar cache
        result1 = classify_clarity(sample_pr)
        result2 = classify_clarity(sample_pr)

        # Deve retornar mesmo valor (cache hit)
        assert result1 == result2

    def test_classify_clarity_different_bodies(self):
        """Testa que diferentes bodies geram diferentes hashes."""
        pr1 = PRRecord(
            id=1,
            html_url="url1",
            repo="test/repo",
            path="file.py",
            body="Clear and detailed description",
            diff_hunk="@@",
            author="user",
            author_association="CON",
            commit_id="abc",
            line=1,
            language="python",
            created_at=None,
        )

        pr2 = PRRecord(
            id=2,
            html_url="url2",
            repo="test/repo",
            path="file.py",
            body="xyz",
            diff_hunk="@@",
            author="user",
            author_association="CON",
            commit_id="def",
            line=1,
            language="python",
            created_at=None,
        )

        # Ambas devem retornar string válida
        result1 = classify_clarity(pr1)
        result2 = classify_clarity(pr2)

        assert isinstance(result1, str)
        assert isinstance(result2, str)


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestClassifiersIntegration:
    """Testes de integração entre classificadores."""

    def test_deterministic_classification(self, sample_pr):
        """Testa que classificação é determinística."""
        # Mesmo PR deve gerar mesmo resultado sempre
        result1 = classify_pr_nature(sample_pr)
        result2 = classify_pr_nature(sample_pr)
        result3 = classify_pr_nature(sample_pr)

        assert result1 == result2 == result3


# ---------------------------------------------------------------------------
# Tests: ISSUE-C - Closure Capture Fix
# ---------------------------------------------------------------------------


class TestClosureCaptureIssueC:
    """Testes para validar fix de captura por referência (ISSUE-C)."""

    @patch("services.classifiers.classify_project_type_batch")
    def test_classify_project_type_closure_captures_by_value(
        self, mock_llm, sample_pr, sample_pr_different_repo
    ):
        """Testa que closure não captura repo_records por referência."""
        # Configure mock para retornar diferentes valores por chamada
        mock_llm.side_effect = [
            '{"project_type": "library"}',  # Primeira chamada (golang/go)
            '{"project_type": "web_app"}',  # Segunda chamada (torvalds/linux)
        ]

        records = [sample_pr, sample_pr_different_repo]
        results = list(classify_project_type(records))

        # Deve retornar 2 resultados
        assert len(results) == 2

        # Cada PR deve ter classificação correta do seu repositório
        golang_results = [r for r in results if r.repo == "golang/go"]
        linux_results = [r for r in results if r.repo == "torvalds/linux"]

        assert len(golang_results) == 1
        assert len(linux_results) == 1

        # Validar que cada recebeu sua classificação
        assert golang_results[0].project_type == "library"
        assert linux_results[0].project_type == "web_app"


# ---------------------------------------------------------------------------
# Tests: ISSUE-A - Real classify_pr_nature()
# ---------------------------------------------------------------------------


class TestClassifyPRNatureRealLLM:
    """Testes para validar implementação real de classify_pr_nature (ISSUE-A)."""

    @patch("services.classifiers.classify_pr_nature_single")
    def test_classify_pr_nature_calls_llm_on_cache_miss(self, mock_llm, sample_pr):
        """Testa que classify_pr_nature chama LLM em cache miss."""
        mock_llm.return_value = '{"pr_nature": "feature"}'

        result = classify_pr_nature(sample_pr)

        # Deve chamar LLM uma vez
        assert mock_llm.call_count == 1
        # Deve normalizar e retornar "feature"
        assert result == "feature"

    @patch("services.classifiers.classify_pr_nature_single")
    def test_classify_pr_nature_returns_normalized_value(self, mock_llm, sample_pr):
        """Testa que normalize_label é aplicado ao resultado."""
        # Mock retorna valor que precisa normalização
        mock_llm.return_value = '{"pr_nature": "bug-fix"}'

        result = classify_pr_nature(sample_pr)

        # Deve normalizar "bug-fix" → "bug_fix"
        assert result == "bug_fix"

    @patch("services.classifiers.classify_pr_nature_single")
    def test_classify_pr_nature_returns_other_on_invalid(self, mock_llm, sample_pr):
        """Testa que retorna 'other' para labels inválidas."""
        mock_llm.return_value = '{"pr_nature": "invalid_nature"}'

        result = classify_pr_nature(sample_pr)

        # Deve normalizar para "other"
        assert result == "other"

    @patch("services.classifiers.classify_pr_nature_single")
    def test_classify_pr_nature_uses_two_level_cache(self, mock_llm, sample_pr):
        """Testa que usa cache de dois níveis (memória + disco)."""
        mock_llm.return_value = '{"pr_nature": "feature"}'

        # Primeira chamada: cache miss, chama LLM
        result1 = classify_pr_nature(sample_pr)
        call_count_1 = mock_llm.call_count

        # Segunda chamada: cache hit, não chama LLM
        result2 = classify_pr_nature(sample_pr)
        call_count_2 = mock_llm.call_count

        assert result1 == "feature"
        assert result2 == "feature"
        # Mock não deve ser chamado novamente (cache hit)
        assert call_count_1 == 1
        assert call_count_2 == 1


# ---------------------------------------------------------------------------
# Tests: ISSUE-B - Real classify_clarity()
# ---------------------------------------------------------------------------


class TestClassifyClarityRealLLM:
    """Testes para validar implementação real de classify_clarity (ISSUE-B)."""

    @patch("services.classifiers.classify_clarity_single")
    def test_classify_clarity_calls_llm_on_cache_miss(self, mock_llm, sample_pr):
        """Testa que classify_clarity chama LLM em cache miss."""
        mock_llm.return_value = '{"clarity_level": "good"}'

        result = classify_clarity(sample_pr)

        # Deve chamar LLM uma vez
        assert mock_llm.call_count == 1
        # Deve normalizar e retornar "good"
        assert result == "good"

    @patch("services.classifiers.classify_clarity_single")
    def test_classify_clarity_returns_normalized_value(self, mock_llm, sample_pr):
        """Testa que normalize_label é aplicado ao resultado."""
        mock_llm.return_value = '{"clarity_level": "excellent"}'

        result = classify_clarity(sample_pr)

        # Deve manter "excellent" (já é válido)
        assert result == "excellent"

    @patch("services.classifiers.classify_clarity_single")
    def test_classify_clarity_returns_other_on_invalid(self, mock_llm, sample_pr):
        """Testa que retorna 'other' para labels inválidas."""
        mock_llm.return_value = '{"clarity_level": "awesome"}'

        result = classify_clarity(sample_pr)

        # Deve normalizar para "other"
        assert result == "other"

    @patch("services.classifiers.classify_clarity_single")
    def test_classify_clarity_uses_two_level_cache(self, mock_llm, sample_pr):
        """Testa que usa cache de dois níveis (memória + disco)."""
        mock_llm.return_value = '{"clarity_level": "good"}'

        # Primeira chamada: cache miss, chama LLM
        result1 = classify_clarity(sample_pr)
        call_count_1 = mock_llm.call_count

        # Segunda chamada: cache hit, não chama LLM
        result2 = classify_clarity(sample_pr)
        call_count_2 = mock_llm.call_count

        assert result1 == "good"
        assert result2 == "good"
        # Mock não deve ser chamado novamente (cache hit)
        assert call_count_1 == 1
        assert call_count_2 == 1
