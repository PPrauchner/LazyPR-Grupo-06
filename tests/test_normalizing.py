"""
tests/test_normalizing.py
==========================
Testes unitários para funções puras de normalização em core/transforms/normalizing.py

Cobertura:
    - Normalização de linguagem (variações, None, unknown)
    - Cálculo de char_count e word_count (normal, vazio, None)
    - Normalização de labels (válidos, inválidos, variações)
    - Normalização de PRRecord e AnalysisResult (imutabilidade, novos valores)
    - Edge cases: strings vazias, None, caracteres especiais
"""

import pytest
from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult
from core.transforms.normalizing import (
    normalize_language,
    calculate_char_count,
    calculate_word_count,
    normalize_label,
    normalize_pr_record,
    normalize_analysis_result,
)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pr():
    """Fixture de um PRRecord para testes."""
    return PRRecord(
        id=178204099,
        html_url="https://github.com/golang/go/pull/23805#discussion_r178204099",
        repo="golang/go",
        path="src/math/rand/rand.go",
        body="This is a test body with some content.",
        diff_hunk="@@ -210,6 +210,11 @@ again:",
        author="test_user",
        author_association="CONTRIBUTOR",
        commit_id="f200cd75ab7c3fd16e046fa3cbc76565c4063cec",
        line=213,
        language="go",
        created_at="2020-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_analysis_result(sample_pr):
    """Fixture de um AnalysisResult para testes."""
    return AnalysisResult(
        id=sample_pr.id,
        html_url=sample_pr.html_url,
        repo=sample_pr.repo,
        path=sample_pr.path,
        body=sample_pr.body,
        diff_hunk=sample_pr.diff_hunk,
        author=sample_pr.author,
        author_association=sample_pr.author_association,
        commit_id=sample_pr.commit_id,
        line=sample_pr.line,
        language=sample_pr.language,
        created_at=sample_pr.created_at,
        project_type="library",
        pr_nature="feature",
        clarity_level="good",
        char_count=37,
        word_count=8,
    )


# ---------------------------------------------------------------------------
# Tests: normalize_language()
# ---------------------------------------------------------------------------


class TestNormalizeLanguage:
    """Testes para normalize_language()."""

    def test_normalize_language_canonical_form(self):
        """Testa normalização de forma canônica já válida."""
        assert normalize_language("python") == "python"
        assert normalize_language("javascript") == "javascript"
        assert normalize_language("go") == "go"

    def test_normalize_language_uppercase_variation(self):
        """Testa normalização de variações em maiúsculas."""
        assert normalize_language("Python") == "python"
        assert normalize_language("PYTHON") == "python"
        assert normalize_language("JavaScript") == "javascript"

    def test_normalize_language_shorthand_variation(self):
        """Testa normalização de abreviações conhecidas."""
        assert normalize_language("py") == "python"
        assert normalize_language("py3") == "python"
        assert normalize_language("js") == "javascript"
        assert normalize_language("ts") == "typescript"
        assert normalize_language("rs") == "rust"
        assert normalize_language("cpp") == "cpp"
        assert normalize_language("c++") == "cpp"

    def test_normalize_language_version_variant(self):
        """Testa normalização com informação de versão."""
        assert normalize_language("Python 3") == "python"
        assert normalize_language("python3") == "python"
        assert normalize_language("ES6") == "javascript"

    def test_normalize_language_with_spaces(self):
        """Testa normalização com espaços em branco."""
        assert normalize_language("  python  ") == "python"
        assert normalize_language("\tjavascript\n") == "javascript"

    def test_normalize_language_unknown(self):
        """Testa normalização de linguagem desconhecida."""
        assert normalize_language("unknown_lang") is None
        assert normalize_language("xyz") is None
        assert normalize_language("cobol") is None

    def test_normalize_language_none(self):
        """Testa normalização de None."""
        assert normalize_language(None) is None

    def test_normalize_language_empty_string(self):
        """Testa normalização de string vazia."""
        assert normalize_language("") is None

    def test_normalize_language_caching(self):
        """Testa que lru_cache funciona corretamente."""
        # Mesma entrada deve retornar em cache
        result1 = normalize_language("Python")
        result2 = normalize_language("Python")
        assert result1 is result2  # mesmo objeto em cache


# ---------------------------------------------------------------------------
# Tests: calculate_char_count()
# ---------------------------------------------------------------------------


class TestCalculateCharCount:
    """Testes para calculate_char_count()."""

    def test_calculate_char_count_normal(self):
        """Testa cálculo básico de caracteres."""
        assert calculate_char_count("hello") == 5
        assert calculate_char_count("hello world") == 11

    def test_calculate_char_count_with_spaces(self):
        """Testa cálculo incluindo espaços."""
        assert calculate_char_count("a b c") == 5  # 3 letras + 2 espaços

    def test_calculate_char_count_with_special_chars(self):
        """Testa cálculo com caracteres especiais."""
        assert calculate_char_count("hello, world!") == 13
        # Emoji em Python é 1 caractere (mesmo sendo multi-byte em UTF-8)
        assert calculate_char_count("🎉 emoji") == 7

    def test_calculate_char_count_unicode(self):
        """Testa cálculo com unicode multibyte."""
        assert calculate_char_count("café") == 4
        assert calculate_char_count("日本語") == 3

    def test_calculate_char_count_empty_string(self):
        """Testa cálculo de string vazia."""
        assert calculate_char_count("") == 0

    def test_calculate_char_count_none(self):
        """Testa cálculo com None."""
        assert calculate_char_count(None) == 0  # type: ignore

    def test_calculate_char_count_newlines(self):
        """Testa cálculo com quebras de linha."""
        assert calculate_char_count("line1\nline2") == 11


# ---------------------------------------------------------------------------
# Tests: calculate_word_count()
# ---------------------------------------------------------------------------


class TestCalculateWordCount:
    """Testes para calculate_word_count()."""

    def test_calculate_word_count_normal(self):
        """Testa cálculo básico de palavras."""
        assert calculate_word_count("hello") == 1
        assert calculate_word_count("hello world") == 2
        assert calculate_word_count("one two three") == 3

    def test_calculate_word_count_multiple_spaces(self):
        """Testa cálculo com múltiplos espaços."""
        assert (
            calculate_word_count("hello  world") == 2
        )  # split() ignora espaços extras
        assert calculate_word_count("  hello  ") == 1

    def test_calculate_word_count_tabs_newlines(self):
        """Testa cálculo com tabs e newlines."""
        assert calculate_word_count("hello\tworld") == 2
        assert calculate_word_count("hello\nworld\ntest") == 3

    def test_calculate_word_count_empty_string(self):
        """Testa cálculo de string vazia."""
        assert calculate_word_count("") == 0

    def test_calculate_word_count_none(self):
        """Testa cálculo com None."""
        assert calculate_word_count(None) == 0  # type: ignore

    def test_calculate_word_count_only_spaces(self):
        """Testa cálculo com apenas whitespace."""
        assert calculate_word_count("   ") == 0
        assert calculate_word_count("\n\n\n") == 0

    def test_calculate_word_count_with_punctuation(self):
        """Testa cálculo com pontuação (pontuação é parte da palavra)."""
        assert calculate_word_count("hello, world!") == 2
        assert calculate_word_count("one-two three") == 2  # hífen não separa


# ---------------------------------------------------------------------------
# Tests: normalize_label()
# ---------------------------------------------------------------------------


class TestNormalizeLabel:
    """Testes para normalize_label()."""

    def test_normalize_label_project_type_valid(self):
        """Testa normalização de project_type válido."""
        assert normalize_label("library", "project_type") == "library"
        assert normalize_label("web_app", "project_type") == "web_app"
        assert normalize_label("framework", "project_type") == "framework"
        assert normalize_label("cli", "project_type") == "cli"
        assert normalize_label("other", "project_type") == "other"

    def test_normalize_label_project_type_uppercase(self):
        """Testa normalização de project_type em maiúsculas."""
        assert normalize_label("LIBRARY", "project_type") == "library"
        assert normalize_label("Web_App", "project_type") == "web_app"

    def test_normalize_label_project_type_invalid(self):
        """Testa normalização de project_type inválido."""
        assert normalize_label("biblioteca", "project_type") == "other"
        assert normalize_label("invalid_type", "project_type") == "other"

    def test_normalize_label_pr_nature_valid(self):
        """Testa normalização de pr_nature válido."""
        assert normalize_label("bug_fix", "pr_nature") == "bug_fix"
        assert normalize_label("feature", "pr_nature") == "feature"
        assert normalize_label("refactoring", "pr_nature") == "refactoring"
        assert normalize_label("documentation", "pr_nature") == "documentation"
        assert normalize_label("other", "pr_nature") == "other"

    def test_normalize_label_pr_nature_hyphen_variant(self):
        """Testa normalização de pr_nature com variação de hífen."""
        assert normalize_label("bug-fix", "pr_nature") == "bug_fix"
        assert normalize_label("BUG-FIX", "pr_nature") == "bug_fix"

    def test_normalize_label_clarity_valid(self):
        """Testa normalização de clarity_level válido."""
        assert normalize_label("insufficient", "clarity_level") == "insufficient"
        assert normalize_label("basic", "clarity_level") == "basic"
        assert normalize_label("good", "clarity_level") == "good"
        assert normalize_label("excellent", "clarity_level") == "excellent"

    def test_normalize_label_unknown_field(self):
        """Testa normalização com campo desconhecido (padrão seguro)."""
        # Campo desconhecido usa project_type como padrão seguro
        assert normalize_label("library", "unknown_field") == "library"
        assert normalize_label("invalid", "unknown_field") == "other"

    def test_normalize_label_with_spaces(self):
        """Testa normalização com espaços em branco."""
        assert normalize_label("  library  ", "project_type") == "library"
        assert normalize_label("\tbug_fix\n", "pr_nature") == "bug_fix"

    def test_normalize_label_caching(self):
        """Testa que lru_cache funciona corretamente."""
        result1 = normalize_label("library", "project_type")
        result2 = normalize_label("library", "project_type")
        assert result1 is result2  # mesmo objeto em cache


# ---------------------------------------------------------------------------
# Tests: normalize_pr_record()
# ---------------------------------------------------------------------------


class TestNormalizePRRecord:
    """Testes para normalize_pr_record()."""

    def test_normalize_pr_record_language_normalization(self, sample_pr):
        """Testa normalização do campo language em PRRecord."""
        pr_with_variant = sample_pr._replace(language="Go")
        normalized = normalize_pr_record(pr_with_variant)
        assert normalized.language == "go"

    def test_normalize_pr_record_language_unknown(self, sample_pr):
        """Testa normalização de linguagem desconhecida."""
        pr_with_unknown = sample_pr._replace(language="unknown")
        normalized = normalize_pr_record(pr_with_unknown)
        assert normalized.language is None

    def test_normalize_pr_record_language_none(self, sample_pr):
        """Testa que None em language permanece None."""
        pr_with_none = sample_pr._replace(language=None)
        normalized = normalize_pr_record(pr_with_none)
        assert normalized.language is None

    def test_normalize_pr_record_immutability(self, sample_pr):
        """Testa que original não é modificado (imutabilidade)."""
        original_language = sample_pr.language
        normalized = normalize_pr_record(sample_pr)
        assert sample_pr.language == original_language
        assert normalized is not sample_pr

    def test_normalize_pr_record_other_fields_unchanged(self, sample_pr):
        """Testa que outros campos não são alterados."""
        normalized = normalize_pr_record(sample_pr)
        assert normalized.id == sample_pr.id
        assert normalized.repo == sample_pr.repo
        assert normalized.body == sample_pr.body
        assert normalized.author == sample_pr.author


# ---------------------------------------------------------------------------
# Tests: normalize_analysis_result()
# ---------------------------------------------------------------------------


class TestNormalizeAnalysisResult:
    """Testes para normalize_analysis_result()."""

    def test_normalize_analysis_result_valid_labels(self, sample_analysis_result):
        """Testa normalização com labels já válidos."""
        normalized = normalize_analysis_result(sample_analysis_result)
        assert normalized.project_type == "library"
        assert normalized.pr_nature == "feature"
        assert normalized.clarity_level == "good"

    def test_normalize_analysis_result_invalid_project_type(
        self, sample_analysis_result
    ):
        """Testa normalização de project_type inválido."""
        ar_invalid = sample_analysis_result._replace(project_type="biblioteca")
        normalized = normalize_analysis_result(ar_invalid)
        assert normalized.project_type == "other"

    def test_normalize_analysis_result_invalid_pr_nature(self, sample_analysis_result):
        """Testa normalização de pr_nature inválido."""
        ar_invalid = sample_analysis_result._replace(pr_nature="bugfix")
        normalized = normalize_analysis_result(ar_invalid)
        assert normalized.pr_nature == "other"

    def test_normalize_analysis_result_invalid_clarity(self, sample_analysis_result):
        """Testa normalização de clarity_level inválido."""
        ar_invalid = sample_analysis_result._replace(clarity_level="excelente")
        normalized = normalize_analysis_result(ar_invalid)
        assert normalized.clarity_level == "other"

    def test_normalize_analysis_result_multiple_invalid(self, sample_analysis_result):
        """Testa normalização com múltiplos fields inválidos."""
        ar_invalid = sample_analysis_result._replace(
            project_type="invalid1",
            pr_nature="invalid2",
            clarity_level="invalid3",
        )
        normalized = normalize_analysis_result(ar_invalid)
        assert normalized.project_type == "other"
        assert normalized.pr_nature == "other"
        assert normalized.clarity_level == "other"

    def test_normalize_analysis_result_immutability(self, sample_analysis_result):
        """Testa que original não é modificado (imutabilidade)."""
        original_type = sample_analysis_result.project_type
        normalized = normalize_analysis_result(sample_analysis_result)
        assert sample_analysis_result.project_type == original_type
        assert normalized is not sample_analysis_result

    def test_normalize_analysis_result_char_word_count_preserved(
        self, sample_analysis_result
    ):
        """Testa que char_count e word_count são preservados."""
        normalized = normalize_analysis_result(sample_analysis_result)
        assert normalized.char_count == sample_analysis_result.char_count
        assert normalized.word_count == sample_analysis_result.word_count

    def test_normalize_analysis_result_other_fields_unchanged(
        self, sample_analysis_result
    ):
        """Testa que outros campos não são alterados."""
        normalized = normalize_analysis_result(sample_analysis_result)
        assert normalized.id == sample_analysis_result.id
        assert normalized.repo == sample_analysis_result.repo
        assert normalized.body == sample_analysis_result.body
        assert normalized.author == sample_analysis_result.author


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestNormalizationIntegration:
    """Testes de integração entre funções de normalização."""

    def test_normalize_workflow_pr_record_to_analysis_result(self):
        """Testa fluxo completo: normalizar PR e depois AnalysisResult."""
        # 1. Criar PRRecord bruto
        pr = PRRecord(
            id=1,
            html_url="https://example.com",
            repo="test/repo",
            path="test.py",
            body="This is a test with 5 words total.",
            diff_hunk="@@ -1,1 @@",
            author="user",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=1,
            language="Python",  # Variação
            created_at=None,
        )

        # 2. Normalizar PR
        normalized_pr = normalize_pr_record(pr)
        assert normalized_pr.language == "python"

        # 3. Criar AnalysisResult com labels inválidos
        analysis = AnalysisResult(
            id=normalized_pr.id,
            html_url=normalized_pr.html_url,
            repo=normalized_pr.repo,
            path=normalized_pr.path,
            body=normalized_pr.body,
            diff_hunk=normalized_pr.diff_hunk,
            author=normalized_pr.author,
            author_association=normalized_pr.author_association,
            commit_id=normalized_pr.commit_id,
            line=normalized_pr.line,
            language=normalized_pr.language,
            created_at=normalized_pr.created_at,
            project_type="Web Application",  # Inválido
            pr_nature="bug-fix",  # Variação com hífen (será convertida para underscore)
            clarity_level="muy bueno",  # Inválido
            char_count=calculate_char_count(normalized_pr.body),
            word_count=calculate_word_count(normalized_pr.body),
        )

        # 4. Normalizar AnalysisResult
        normalized_analysis = normalize_analysis_result(analysis)
        assert normalized_analysis.project_type == "other"
        assert normalized_analysis.pr_nature == "bug_fix"
        assert normalized_analysis.clarity_level == "other"
        assert normalized_analysis.char_count == 34
        assert normalized_analysis.word_count == 8

    def test_deterministic_normalization(self):
        """Testa que normalização é determinística (mesmo input → mesmo output)."""
        label = "Bug-Fix"
        field = "pr_nature"

        result1 = normalize_label(label, field)
        result2 = normalize_label(label, field)
        result3 = normalize_label(label, field)

        assert result1 == result2 == result3
