"""
tests/test_runner.py
=====================
Testes para core/pipeline/runner.py - integração completa do pipeline.

Cobertura:
    - Execução sequencial das Etapas recebidas como argumento
    - Etapas ativáveis: só roda o que está na tupla
    - Lazy evaluation (generators, sem materialização)
    - Composição funcional via composer
"""

import pytest
from unittest.mock import patch, MagicMock
from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult
from core.pipeline.runner import run_pipeline
from core.pipeline.stages import (
    enrich_without_classification,
    filter_results,
    normalize_records,
)
from core.pipeline.composer import pipe, compose, identity
from core.transforms.filtering import is_language
from services.classifiers import classify_project_type
from utils.memoization import clear_cache

# Etapas usadas nos testes offline: normalizam e enriquecem sem tocar no LLM.
_OFFLINE_STEPS = (normalize_records, enrich_without_classification)

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pr_list(sample_pr, sample_pr_same_repo, sample_pr_different_repo):
    """Fixture de múltiplos PRRecords com dados do dataset."""
    return [sample_pr, sample_pr_same_repo, sample_pr_different_repo]


# ---------------------------------------------------------------------------
# Tests: run_pipeline() - Normalização
# ---------------------------------------------------------------------------


class TestRunPipelineNormalization:
    """Testes para etapa de normalização."""

    def test_calculate_metrics_char_count(self, sample_pr):
        """Testa cálculo de char_count."""
        results = list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))

        assert len(results) == 1
        assert results[0].char_count == len(sample_pr.body)
        assert results[0].char_count > 0

    def test_calculate_metrics_word_count(self, sample_pr):
        """Testa cálculo de word_count."""
        results = list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))

        assert len(results) == 1
        assert results[0].word_count == len(sample_pr.body.split())
        assert results[0].word_count > 0


# ---------------------------------------------------------------------------
# Tests: run_pipeline() - Classificação
# ---------------------------------------------------------------------------


class TestRunPipelineClassification:
    """Testes para etapa de classificação."""

    @patch("services.classifiers.classify_project_type_batch")
    def test_classify_project_type_full_pipeline(self, mock_llm, sample_pr):
        """Testa pipeline com a Etapa de classificação na tupla."""
        mock_llm.return_value = '{"project_type": "library"}'

        steps = (normalize_records, classify_project_type)
        results = list(run_pipeline(steps, [sample_pr]))

        # Deve ter pelo menos 1 resultado (pode haver duplicata por grupo)
        assert len(results) >= 1
        assert results[0].project_type == "library"


# ---------------------------------------------------------------------------
# Tests: run_pipeline() - Etapas ativáveis
# ---------------------------------------------------------------------------


class TestRunPipelineSelectableStages:
    """Testes para etapas ativáveis/desativáveis."""

    def test_omitted_classification_yields_unknown_labels(self, sample_pr):
        """Sem a Etapa de classificação, as três classificações são 'unknown'."""
        results = list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))

        assert len(results) == 1
        assert results[0].project_type == "unknown"
        assert results[0].pr_nature == "unknown"
        assert results[0].clarity_level == "unknown"

    def test_filter_stage_only_runs_when_included(self, sample_pr):
        """A Etapa de filtragem só recorta o stream quando está na tupla."""
        never_matches = filter_results((is_language("__nenhuma__"),))

        assert len(list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))) == 1
        assert list(run_pipeline(_OFFLINE_STEPS + (never_matches,), [sample_pr])) == []


# ---------------------------------------------------------------------------
# Tests: Lazy Evaluation
# ---------------------------------------------------------------------------


class TestRunPipelineLazyEvaluation:
    """Testes para lazy evaluation (generators)."""

    @patch("services.classifiers.classify_project_type_batch")
    def test_returns_generator_not_list(self, mock_llm, sample_pr):
        """Testa que run_pipeline retorna generator, não lista."""
        mock_llm.return_value = '{"project_type": "library"}'

        result = run_pipeline((normalize_records, classify_project_type), [sample_pr])

        # Deve ser generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")


# ---------------------------------------------------------------------------
# Tests: Composer (pipe, compose, identity)
# ---------------------------------------------------------------------------


class TestComposer:
    """Testes para core/pipeline/composer.py."""

    def test_pipe_left_to_right(self):
        """Testa que pipe aplica funções da esquerda para direita."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2

        # pipe: (x) -> double(x) -> add_one(double(x))
        piped = pipe(double, add_one)
        result = piped(5)

        # double(5) = 10, add_one(10) = 11
        assert result == 11

    def test_compose_right_to_left(self):
        """Testa que compose aplica funções da direita para esquerda."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2

        # compose: (x) -> add_one(double(x))
        composed = compose(add_one, double)
        result = composed(5)

        # double(5) = 10, add_one(10) = 11
        assert result == 11

    def test_identity_function(self):
        """Testa função identidade."""
        assert identity(42) == 42
        assert identity("hello") == "hello"
        assert identity(None) is None

    def test_compose_empty(self):
        """Testa composição vazia retorna identidade."""
        composed = compose()
        assert composed(5) == 5

    def test_pipe_single_function(self):
        """Testa pipe com única função retorna a função."""
        add_one = lambda x: x + 1
        piped = pipe(add_one)
        assert piped(5) == 6


# ---------------------------------------------------------------------------
# Integration Tests
# ---------------------------------------------------------------------------


class TestRunPipelineIntegration:
    """Testes de integração completos do pipeline."""

    def test_deterministic_results(self, sample_pr):
        """Testa que execuções repetidas produzem mesmos resultados."""
        results1 = list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))
        results2 = list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))

        assert results1[0].id == results2[0].id
        assert results1[0].char_count == results2[0].char_count
        assert results1[0].word_count == results2[0].word_count


# ---------------------------------------------------------------------------
# Edge Cases
# ---------------------------------------------------------------------------


class TestRunPipelineEdgeCases:
    """Testes para casos extremos."""

    def test_empty_source(self):
        """Testa pipeline com source vazio."""
        results = list(run_pipeline(_OFFLINE_STEPS, []))

        assert len(results) == 0

    def test_single_record(self, sample_pr):
        """Testa pipeline com único registro."""
        results = list(run_pipeline(_OFFLINE_STEPS, [sample_pr]))

        assert len(results) == 1

    def test_generator_source(self, sample_pr_list):
        """Testa que pipeline aceita gerador como source (não apenas lista)."""

        def pr_generator():
            for pr in sample_pr_list:
                yield pr

        results = list(run_pipeline(_OFFLINE_STEPS, pr_generator()))

        assert len(results) == len(sample_pr_list)
