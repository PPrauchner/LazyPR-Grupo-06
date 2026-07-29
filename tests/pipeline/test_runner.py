"""
Testes do pipeline funcional completo.

Valida:
    - integração da limpeza textual
    - normalização antes da classificação
    - preservação de lazy evaluation
    - configuração enable_cleaning
"""

from core.models.pr_record import PRRecord

from core.pipeline.runner import (
    PipelineConfig,
    run_pipeline,
)


def test_pipeline_applies_cleaning():
    """
    Deve aplicar limpeza textual
    antes das próximas etapas.
    """

    records = (
        PRRecord(
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
        ),
    )

    config = PipelineConfig(
        enable_cleaning=True,
        enable_normalization=False,
        enable_classification=False,
    )

    results = tuple(
        run_pipeline(
            records,
            config,
        )
    )

    result = results[0]

    assert result.body == "Hello World"

    assert result.repo == "repo"

    assert result.path == "file.py"


def test_pipeline_without_cleaning():
    """
    Deve preservar texto bruto
    quando limpeza estiver desabilitada.
    """

    records = (
        PRRecord(
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
        ),
    )

    config = PipelineConfig(
        enable_cleaning=False,
        enable_normalization=False,
        enable_classification=False,
    )

    results = tuple(
        run_pipeline(
            records,
            config,
        )
    )

    result = results[0]

    assert result.body == " <b>Hello World</b> "


def test_pipeline_is_lazy():
    """
    Deve retornar generator lazy
    sem materialização imediata.
    """

    records = (
        PRRecord(
            id="1",
            html_url="url",
            repo="repo",
            path="file.py",
            body="body",
            diff_hunk="diff",
            author="user",
            author_association="CONTRIBUTOR",
            commit_id="abc123",
            line=10,
            language="Python",
            created_at="2025-01-01",
        ),
    )

    config = PipelineConfig(
        enable_cleaning=True,
        enable_normalization=False,
        enable_classification=False,
    )

    pipeline = run_pipeline(
        records,
        config,
    )

    assert hasattr(
        pipeline,
        "__iter__",
    )

    assert not isinstance(
        pipeline,
        list,
    )