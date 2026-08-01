"""
tests/test_schema_refusal_degradation.py
=========================================
Testes do caminho de recusa de schema, do `services/llm_client.py` até a
página de upload.

Responsabilidades:
    - Provar que a recusa degrada para o sentinela `unknown` em vez de
      abortar a Análise, deixando rastro em log.
    - Provar que os demais registros chegam ao fim e que `save_results()`
      é chamado mesmo quando um registro foi recusado.
"""

import json
import logging
from unittest.mock import MagicMock, patch

import pytest

from core.models.analysis_result import UNKNOWN_PROJECT_TYPE
from services import classifiers
from services import llm_client


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Aponta o cache em disco para um diretório vazio e descartável."""
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    return tmp_path


def test_schema_refusal_degrades_to_the_unknown_sentinel(
    sample_pr, isolated_cache, monkeypatch
):
    """Recusa persistente vira `unknown` e o registro continua no resultado.

    Abortar a Análise inteira por causa de um registro descartaria tudo o que
    já foi pago em cota do Groq (ADR-0004).
    """
    degraded = json.dumps({"project_type": UNKNOWN_PROJECT_TYPE})
    monkeypatch.setattr(
        classifiers, "classify_project_type_batch", lambda records: degraded
    )
    monkeypatch.setattr(
        classifiers,
        "classify_pr_nature_and_clarity_single",
        lambda record: json.dumps({"pr_nature": "feature", "clarity_level": "good"}),
    )

    results = tuple(classifiers.classify_project_type((sample_pr,)))

    assert len(results) == 1
    assert results[0].project_type == UNKNOWN_PROJECT_TYPE
    assert results[0].pr_nature == "feature"


def test_the_refusal_is_recorded_in_the_log(sample_pr, caplog, monkeypatch):
    """A recusa não some: repositório e conteúdo recusado ficam registrados."""
    monkeypatch.setattr(llm_client.time, "sleep", lambda seconds: None)
    monkeypatch.setenv("GROQ_API_KEY", "test-key")

    class _RefusingAgent:
        def run(self, prompt: str) -> object:
            return type(
                "FakeRunOutput", (), {"content": '{"project_type": "monorepo"}'}
            )

    monkeypatch.setattr(llm_client, "_build_agent", lambda *a, **kw: _RefusingAgent())

    with caplog.at_level(logging.ERROR, logger=llm_client.__name__):
        raw = llm_client.classify_project_type_batch((sample_pr,))

    assert json.loads(raw) == {"project_type": UNKNOWN_PROJECT_TYPE}
    assert sample_pr.repo in caplog.text
    assert "monorepo" in caplog.text


def test_upload_page_saves_the_analysis_despite_a_refused_record(sample_pr):
    """A Análise chega ao fim e é persistida mesmo com registro degradado."""
    from views import upload

    with (
        patch.object(upload, "st") as mock_st,
        patch.object(upload, "hash_file_stream", return_value=("hash", None)),
        patch.object(upload, "has_cached_analysis", return_value=False),
        patch.object(upload, "stream_csv", return_value=iter(())),
        patch.object(upload, "run_pipeline", return_value=iter((sample_pr,))),
        patch.object(upload, "save_results") as mock_save,
        patch.object(upload, "read_header_lazily", return_value=["id", "body"]),
        patch.object(upload, "get_missing_columns", return_value=[]),
    ):
        mock_st.session_state = {}
        mock_st.button.return_value = True
        mock_st.file_uploader.return_value = MagicMock()
        mock_st.columns.return_value = (MagicMock(), MagicMock())

        upload.render_upload_page()

    mock_st.error.assert_not_called()
    mock_save.assert_called_once()
    assert mock_save.call_args[0][1] == (sample_pr,)
