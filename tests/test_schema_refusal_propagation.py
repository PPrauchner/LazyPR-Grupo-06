"""
tests/test_schema_refusal_propagation.py
=========================================
Testes do caminho de erro da recusa de schema, do `services/llm_client.py`
até a página de upload.

Responsabilidades:
    - Provar que a recusa atravessa `services/classifiers.py` sem virar
      sentinela `unknown`, carregando o repositório de origem.
    - Provar que a página de upload apresenta a recusa como mensagem de erro
      legível, e não como traceback cru.
"""

from unittest.mock import MagicMock, patch

import pytest

from services import classifiers
from services.llm_client import SchemaRefusalError


@pytest.fixture
def isolated_cache(tmp_path, monkeypatch):
    """Aponta o cache em disco para um diretório vazio e descartável."""
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    return tmp_path


def test_schema_refusal_propagates_instead_of_classifying_as_unknown(
    sample_pr, isolated_cache
):
    """Desvio de schema não produz registro com classificação `unknown`.

    Silenciar a recusa deixaria `unknown` indistinguível de classificação
    legítima, contaminando a correlação da HU 07 sem deixar rastro.
    """
    refusal = SchemaRefusalError(
        repo=sample_pr.repo, content='{"project_type": "monorepo"}', attempts=2
    )

    with patch.object(classifiers, "classify_project_type_batch", side_effect=refusal):
        with pytest.raises(SchemaRefusalError) as excinfo:
            tuple(classifiers.classify_project_type((sample_pr,)))

    assert excinfo.value.repo == sample_pr.repo


def test_upload_page_shows_schema_refusal_as_a_readable_error(sample_pr):
    """A página nomeia o repositório afetado em vez de estourar o traceback."""
    from views import upload

    refusal = SchemaRefusalError(
        repo=sample_pr.repo, content='{"project_type": "monorepo"}', attempts=2
    )

    with (
        patch.object(upload, "st") as mock_st,
        patch.object(upload, "hash_file_stream", return_value=("hash", None)),
        patch.object(upload, "has_cached_analysis", return_value=False),
        patch.object(upload, "stream_csv", return_value=iter(())),
        patch.object(upload, "run_pipeline", side_effect=refusal),
        patch.object(upload, "save_results") as mock_save,
        patch.object(upload, "read_header_lazily", return_value=["id", "body"]),
        patch.object(upload, "get_missing_columns", return_value=[]),
    ):
        mock_st.session_state = {}
        mock_st.button.return_value = True
        mock_st.file_uploader.return_value = MagicMock()
        mock_st.columns.return_value = (MagicMock(), MagicMock())

        upload.render_upload_page()

    mock_st.error.assert_called_once()
    message = mock_st.error.call_args[0][0]
    assert sample_pr.repo in message
    mock_save.assert_not_called()
