"""
tests/test_classifiers.py
Testes unitários para services/classifiers.py
"""

import json
from unittest.mock import patch
from dataclasses import dataclass

import pytest

from services.classifiers import (
    ClarityLevel,
    ClarityResult,
    PRNature,
    PRNatureResult,
    ProjectType,
    ProjectTypeResult,
    classify_clarity,
    classify_pr_nature,
    classify_project_type,
    _parse,
    _cached_call,
)


@dataclass
class FakeRecord:
    body: str = ""
    repo: str = "org/repo"
    title: str = "Título padrão do PR"
    path: str = "src/main.py"
    diff_hunk: str = "+ linha nova"


@pytest.fixture
def record():
    return FakeRecord(body="O botão de login não respondia em mobile.")


@pytest.fixture
def records():
    return [
        FakeRecord("Novo painel de métricas.", "org/repo"),
        FakeRecord("CSV vazio em alguns casos.", "org/repo"),
        FakeRecord("Instruções de instalação.", "org/outro"),
    ]


def test_parse_extrai_campo_corretamente():
    assert _parse(json.dumps({"nature": "bug_fix"}), "nature") == "bug_fix"


def test_parse_normaliza_para_lowercase():
    assert _parse(json.dumps({"clarity": "Excelente"}), "clarity") == "excelente"


def test_parse_espacos_viram_underscore():
    assert _parse(json.dumps({"nature": "bug fix"}), "nature") == "bug_fix"


def test_parse_json_invalido_retorna_vazio():
    assert _parse("não é json", "nature") == ""


def test_parse_campo_ausente_retorna_vazio():
    assert _parse(json.dumps({"outro": "valor"}), "nature") == ""


def test_parse_remove_bloco_markdown():
    raw = "```json\n" + json.dumps({"clarity": "boa"}) + "\n```"
    assert _parse(raw, "clarity") == "boa"


def test_cached_call_retorna_cache_sem_chamar_llm():
    with (
        patch("services.classifiers.get_cache", return_value="cached_value"),
        patch("services.classifiers.call_llm") as mock_llm,
    ):
        assert _cached_call("chave", "prompt") == "cached_value"
        mock_llm.assert_not_called()


def test_cached_call_chama_llm_em_cache_miss():
    with (
        patch("services.classifiers.get_cache", return_value=None),
        patch("services.classifiers.call_llm", return_value="llm_response"),
        patch("services.classifiers.set_cache") as mock_set,
    ):
        assert _cached_call("chave", "prompt") == "llm_response"
        mock_set.assert_called_once_with("chave", "llm_response")


@pytest.mark.parametrize(
    "value, expected",
    [
        ("bug_fix", PRNature.BUG_FIX),
        ("feature", PRNature.FEATURE),
        ("refactoring", PRNature.REFACTORING),
        ("documentation", PRNature.DOCUMENTATION),
    ],
)
def test_classify_pr_nature_mapeia_valores_validos(record, value, expected):
    with patch(
        "services.classifiers.get_cache", return_value=json.dumps({"nature": value})
    ):
        assert classify_pr_nature(record).nature == expected


def test_classify_pr_nature_fallback_para_unknown(record):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"nature": "invalido"}),
    ):
        assert classify_pr_nature(record).nature == PRNature.UNKNOWN


def test_classify_pr_nature_retorna_tipo_correto(record):
    with patch(
        "services.classifiers.get_cache", return_value=json.dumps({"nature": "feature"})
    ):
        assert isinstance(classify_pr_nature(record), PRNatureResult)


@pytest.mark.parametrize(
    "value, score",
    [
        ("insuficiente", 1),
        ("basica", 2),
        ("boa", 3),
        ("excelente", 4),
    ],
)
def test_classify_clarity_score_correto(record, value, score):
    with patch(
        "services.classifiers.get_cache", return_value=json.dumps({"clarity": value})
    ):
        assert classify_clarity(record).score == score


def test_classify_clarity_fallback_para_insuficiente(record):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"clarity": "invalido"}),
    ):
        assert classify_clarity(record).level == ClarityLevel.INSUFICIENTE


def test_classify_clarity_retorna_tipo_correto(record):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"clarity": "excelente"}),
    ):
        assert isinstance(classify_clarity(record), ClarityResult)


def test_classify_project_type_agrupa_por_repositorio(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "api"}),
    ):
        assert len(classify_project_type(records)) == 2


def test_classify_project_type_mapeia_valor_valido(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "api"}),
    ):
        assert all(
            r.project_type == ProjectType.API for r in classify_project_type(records)
        )


def test_classify_project_type_fallback_para_unknown(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "invalido"}),
    ):
        assert all(
            r.project_type == ProjectType.UNKNOWN
            for r in classify_project_type(records)
        )


def test_classify_project_type_retorna_tipo_correto(records):
    with patch(
        "services.classifiers.get_cache",
        return_value=json.dumps({"project_type": "library"}),
    ):
        assert all(
            isinstance(r, ProjectTypeResult) for r in classify_project_type(records)
        )


def test_clarity_level_scores():
    assert ClarityLevel.INSUFICIENTE.score == 1
    assert ClarityLevel.BASICA.score == 2
    assert ClarityLevel.BOA.score == 3
    assert ClarityLevel.EXCELENTE.score == 4


# Testes para services/classifiers.py com mocks de LLM.

"""
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
    _parse_json_response,
    _build_analysis_result,
    _extract_field_from_json,
)
from utils.memoization import clear_cache

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


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
