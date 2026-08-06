"""
tests/test_analysis_persistence.py
==================================
Regressão da issue #82: a Análise persistida cobre sempre o dataset inteiro.

O defeito original: `run_pipeline` lia os filtros da sidebar de
`st.session_state` e recortava o stream **antes** da persistência, mas a
Análise era gravada sob o hash do dataset completo — truncando o cache de
forma silenciosa e permanente.

Cobertura:
    - Análise persistida não é recortada pelos filtros da sidebar.
    - Filtragem continua disponível como etapa, com predicados por argumento.
    - A chave de cache é versionada, invalidando Análises truncadas antigas.
"""

from unittest.mock import patch

import pytest

from core.models.pr_record import PRRecord
from core.pipeline.runner import run_pipeline
from core.pipeline.stages import (
    enrich_without_classification,
    filter_results,
    normalize_records,
)
from core.transforms.filtering import by_language
from services import storage


def _pr_record(record_id: int, path: str, language: str) -> PRRecord:
    """Constrói um PRRecord mínimo para os testes de persistência."""
    return PRRecord(
        id=record_id,
        html_url=f"https://github.com/owner/repo/pull/{record_id}",
        repo="owner/repo",
        path=path,
        body="Comentário de revisão com conteúdo suficiente.",
        diff_hunk="@@ -1,5 +1,10 @@",
        author="reviewer",
        author_association="CONTRIBUTOR",
        commit_id="abc123",
        line=10,
        language=language,
        created_at="2024-01-15",
    )


@pytest.fixture
def cache_dir(tmp_path, monkeypatch):
    """Aponta CACHE_DIR para um diretório temporário."""
    monkeypatch.setenv("CACHE_DIR", str(tmp_path))
    return tmp_path


@pytest.fixture
def dataset() -> tuple[PRRecord, ...]:
    """Dataset com duas linguagens distintas."""
    return (
        _pr_record(1, "src/main.py", "Python"),
        _pr_record(2, "src/Main.java", "Java"),
    )


# A classificação fica de fora para manter o teste offline; a filtragem era
# aplicada independentemente dela, então o defeito se reproduz igual.
_UPLOAD_STEPS = (normalize_records, enrich_without_classification)


@patch("ui.sidebar_filters.st")
def test_persisted_analysis_covers_full_dataset_despite_active_sidebar_filter(
    mock_st,
    cache_dir,
    dataset,
):
    """A Análise gravada cobre o dataset inteiro mesmo com filtro na sidebar.

    O mock da sidebar deixa "Python" selecionado durante a análise — o estado
    exato que antes recortava o stream antes de `save_results`.
    """
    mock_st.session_state = {
        "selected_languages": ("Python",),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }

    results = tuple(run_pipeline(_UPLOAD_STEPS, dataset))
    storage.save_results("dataset_hash", results)

    loaded = tuple(storage.load_results("dataset_hash"))

    assert {record.id for record in loaded} == {1, 2}


def test_pipeline_filters_when_predicates_arrive_by_argument(dataset):
    """Filtragem continua sendo etapa utilizável — via argumento, não estado."""
    steps = _UPLOAD_STEPS + (filter_results((by_language(("python",)),)),)

    results = tuple(run_pipeline(steps, dataset))

    assert tuple(record.id for record in results) == (1,)


def test_cache_key_is_versioned(cache_dir, dataset):
    """Uma Análise gravada com a chave antiga não é tratada como válida."""
    legacy_path = cache_dir / "dataset_hash.json"
    legacy_path.write_text("[]", encoding="utf-8")

    assert not storage.has_cached_analysis("dataset_hash")
