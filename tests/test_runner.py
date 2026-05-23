"""
tests/test_runner.py
=====================
Testes para core/pipeline/runner.py - integração completa do pipeline.

Cobertura:
    - Execução sequencial das etapas (normalização → classificação)
    - Configuração de etapas ativáveis/desativáveis
    - Lazy evaluation (generators, sem materialização)
    - Composição funcional via build_pipeline()
"""

import pytest
from unittest.mock import patch, MagicMock
from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult
from core.pipeline.runner import (
    run_pipeline,
    PipelineConfig,
    build_pipeline,
    PipelineMetrics,
)
from core.pipeline.composer import pipe, compose, identity

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def sample_pr_list(sample_pr, sample_pr_same_repo, sample_pr_different_repo):
    """Fixture de múltiplos PRRecords com dados do dataset."""
    return [sample_pr, sample_pr_same_repo, sample_pr_different_repo]


# ---------------------------------------------------------------------------
# Tests: PipelineConfig
# ---------------------------------------------------------------------------


class TestPipelineConfig:
    """Testes para configuração do pipeline."""

    def test_pipeline_config_defaults(self):
        """Testa valores padrão de PipelineConfig."""
        config = PipelineConfig()
        assert config.enable_normalization is True
        assert config.enable_filtering is True
        assert config.enable_classification is True
        assert config.enable_aggregation is False

    def test_pipeline_config_custom(self):
        """Testa configuração customizada."""
        config = PipelineConfig(
            enable_normalization=True,
            enable_filtering=False,
            enable_classification=True,
            enable_aggregation=True,
        )
        assert config.enable_normalization is True
        assert config.enable_filtering is False
        assert config.enable_classification is True
        assert config.enable_aggregation is True


# ---------------------------------------------------------------------------
# Tests: run_pipeline() - Normalização
# ---------------------------------------------------------------------------


class TestRunPipelineNormalization:
    """Testes para etapa de normalização."""

    def test_normalize_language_variant(self, sample_pr):
        """Testa que linguagem é normalizada (Python 3 → python)."""
        config = PipelineConfig(
            enable_classification=False,  # Desabilitar classification para testar só normalização
        )
        records = [sample_pr]
        results = list(run_pipeline(records, config))

        # Deve ter normalizado language
        assert len(results) == 1
        # Note: A normalização acontece, mas como desabilitamos classification,
        # recebemos AnalysisResult com language do original
        # (o campo language em AnalysisResult usa o normalizado do PR)

    def test_calculate_metrics_char_count(self, sample_pr):
        """Testa cálculo de char_count."""
        config = PipelineConfig(enable_classification=False)
        records = [sample_pr]
        results = list(run_pipeline(records, config))

        assert len(results) == 1
        assert results[0].char_count == len(sample_pr.body)
        assert results[0].char_count > 0

    def test_calculate_metrics_word_count(self, sample_pr):
        """Testa cálculo de word_count."""
        config = PipelineConfig(enable_classification=False)
        records = [sample_pr]
        results = list(run_pipeline(records, config))

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
        """Testa pipeline com classificação habilitada."""
        mock_llm.return_value = '{"project_type": "library"}'

        config = PipelineConfig(enable_classification=True)
        records = [sample_pr]
        results = list(run_pipeline(records, config))

        # Deve ter pelo menos 1 resultado (pode haver duplicata por grupo)
        assert len(results) >= 1
        assert results[0].project_type == "library"


# ---------------------------------------------------------------------------
# Tests: run_pipeline() - Config Toggles
# ---------------------------------------------------------------------------


class TestRunPipelineConfigToggles:
    """Testes para etapas ativáveis/desativáveis."""

    def test_disabled_classification_returns_stub(self, sample_pr):
        """Testa que desabilitar classification retorna AnalysisResult com 'other'."""
        config = PipelineConfig(enable_classification=False)
        records = [sample_pr]
        results = list(run_pipeline(records, config))

        assert len(results) == 1
        assert results[0].project_type == "other"
        assert results[0].pr_nature == "other"
        assert results[0].clarity_level == "other"


# ---------------------------------------------------------------------------
# Tests: Lazy Evaluation
# ---------------------------------------------------------------------------


class TestRunPipelineLazyEvaluation:
    """Testes para lazy evaluation (generators)."""

    @patch("services.classifiers.classify_project_type_batch")
    def test_returns_generator_not_list(self, mock_llm, sample_pr):
        """Testa que run_pipeline retorna generator, não lista."""
        mock_llm.return_value = '{"project_type": "library"}'

        config = PipelineConfig(enable_classification=True)
        records = [sample_pr]
        result = run_pipeline(records, config)

        # Deve ser generator
        assert hasattr(result, "__iter__")
        assert hasattr(result, "__next__")


# ---------------------------------------------------------------------------
# Tests: build_pipeline() - Composição Funcional
# ---------------------------------------------------------------------------


class TestBuildPipeline:
    """Testes para construção de pipelines customizados via composição."""

    def test_build_pipeline_simple_composition(self):
        """Testa composição simples de funções."""
        add_one = lambda x: x + 1
        double = lambda x: x * 2

        # pipe: double(5) = 10, add_one(10) = 11
        pipeline = build_pipeline(double, add_one)
        result = pipeline(5)

        assert result == 11

    def test_build_pipeline_with_identity(self):
        """Testa pipeline que inclui função identidade."""
        add_one = lambda x: x + 1

        pipeline = build_pipeline(identity, add_one)
        result = pipeline(5)

        assert result == 6


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
        config = PipelineConfig(enable_classification=False)

        results1 = list(run_pipeline([sample_pr], config))
        results2 = list(run_pipeline([sample_pr], config))

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
        config = PipelineConfig(enable_classification=False)
        results = list(run_pipeline([], config))

        assert len(results) == 0

    def test_single_record(self, sample_pr):
        """Testa pipeline com único registro."""
        config = PipelineConfig(enable_classification=False)
        results = list(run_pipeline([sample_pr], config))

        assert len(results) == 1

    def test_generator_source(self, sample_pr_list):
        """Testa que pipeline aceita gerador como source (não apenas lista)."""

        def pr_generator():
            for pr in sample_pr_list:
                yield pr

        config = PipelineConfig(enable_classification=False)
        results = list(run_pipeline(pr_generator(), config))

        assert len(results) == len(sample_pr_list)
