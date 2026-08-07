"""
Testes do pipeline funcional completo.

Valida:
    - etapas recebidas como argumento e compostas por `run_pipeline`
    - desligar uma etapa é observável no resultado
    - preservação de lazy evaluation
"""

from inspect import GEN_CREATED, GEN_SUSPENDED, getgeneratorstate

from core.models.pr_record import PRRecord

from core.pipeline.runner import run_pipeline
from core.pipeline.stages import (
    clean_records,
    enrich_without_classification,
    normalize_records,
)


def _raw_record() -> PRRecord:
    """PRRecord bruto, com HTML e espaços que só a limpeza remove."""
    return PRRecord(
        id="1",
        html_url=" https://github.com/test ",
        repo=" repo ",
        path=" file.py ",
        body=" <b>Hello World</b> ",
        diff_hunk=" diff ",
        author=" user ",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=10,
        language="Python",
        created_at="2025-01-01",
    )


def test_pipeline_applies_stage_received_as_argument():
    """A etapa passada como argumento é aplicada ao stream."""
    results = tuple(run_pipeline((clean_records,), (_raw_record(),)))

    result = results[0]

    assert result.body == "Hello World"
    assert result.repo == "repo"
    assert result.path == "file.py"


def test_pipeline_runs_only_the_stages_it_received():
    """Um subconjunto de Etapas roda; as ausentes não deixam efeito algum."""
    steps = (normalize_records, enrich_without_classification)

    result = tuple(run_pipeline(steps, (_raw_record(),)))[0]

    # Normalização rodou: language canônica.
    assert result.language == "python"
    # Enriquecimento neutro rodou: virou AnalysisResult sem consultar o LLM.
    assert result.project_type == "unknown"
    # Limpeza ficou de fora: o corpo bruto atravessou intacto.
    assert result.body == " <b>Hello World</b> "


def test_pipeline_is_lazy():
    """Nenhum registro é lido da origem antes do primeiro consumo."""
    source = (record for record in (_raw_record(), _raw_record()))

    pipeline = run_pipeline((clean_records,), source)

    assert getgeneratorstate(source) == GEN_CREATED

    next(pipeline)

    assert getgeneratorstate(source) == GEN_SUSPENDED


def test_pipeline_without_stages_returns_source_untouched():
    """Sem Etapas, o stream de origem atravessa inalterado."""
    record = _raw_record()

    assert tuple(run_pipeline((), (record,))) == (record,)
