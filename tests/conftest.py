"""
tests/conftest.py
==================
Fixtures compartilhadas entre módulos de teste.

Contém fixtures base para PRRecord e AnalysisResult usando dados reais do dataset Kaggle,
evitando duplicação entre test_classifiers.py, test_runner.py e test_normalizing.py.

Responsabilidades:
    - Definir sample_pr e sample_analysis_result com dados que refletem o schema Kaggle
    - Fornecer clear_memoization_cache fixture para limpeza entre testes
    - Permitir reutilização de fixtures comuns entre módulos
"""

import pytest
from core.models.pr_record import PRRecord
from core.models.analysis_result import AnalysisResult
from utils.memoization import clear_cache


@pytest.fixture
def sample_pr():
    """
    Fixture de um PRRecord com dados reais do dataset Kaggle.

    Reflete o schema do dataset: campo 'author' (não 'user'), sem campo 'language'
    para comentários onde a linguagem não pôde ser inferida.
    """
    return PRRecord(
        id=178204099,
        html_url="https://github.com/golang/go/pull/23805#discussion_r178204099",
        repo="golang/go",
        path="src/math/rand/rand.go",
        body="This fixes an issue with random number generation in the standard library.",
        diff_hunk="@@ -210,6 +210,11 @@ again:",
        author="test_user",
        author_association="CONTRIBUTOR",
        commit_id="f200cd75ab7c3fd16e046fa3cbc76565c4063cec",
        line=213,
        language="go",
        created_at="2020-01-01T00:00:00Z",
    )


@pytest.fixture
def sample_pr_same_repo():
    """Fixture de um segundo PRRecord no mesmo repositório."""
    return PRRecord(
        id=178204100,
        html_url="https://github.com/golang/go/pull/23806#discussion_r178204100",
        repo="golang/go",
        path="src/math/rand/rand.go",
        body="This adds support for new random distributions.",
        diff_hunk="@@ -220,6 +220,11 @@",
        author="another_user",
        author_association="MEMBER",
        commit_id="e200cd75ab7c3fd16e046fa3cbc76565c4063cef",
        line=223,
        language="go",
        created_at="2020-01-02T00:00:00Z",
    )


@pytest.fixture
def sample_pr_different_repo():
    """Fixture de um PRRecord em repositório diferente."""
    return PRRecord(
        id=178204101,
        html_url="https://github.com/torvalds/linux/pull/12345#discussion_r178204101",
        repo="torvalds/linux",
        path="drivers/gpu/drm/nouveau/nouveau_drv.c",
        body="This fixes a GPU driver issue that affects NVIDIA hardware.",
        diff_hunk="@@ -100,6 +100,11 @@",
        author="kernel_dev",
        author_association="OWNER",
        commit_id="d200cd75ab7c3fd16e046fa3cbc76565c4063ced",
        line=105,
        language="c",
        created_at="2020-01-03T00:00:00Z",
    )


@pytest.fixture
def sample_analysis_result(sample_pr):
    """
    Fixture de um AnalysisResult enriquecido com dados reais.

    Estende os dados do sample_pr com classificações e métricas calculadas.
    """
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
        pr_nature="bug_fix",
        clarity_level="good",
        char_count=len(sample_pr.body),
        word_count=len(sample_pr.body.split()),
    )


@pytest.fixture(autouse=True)
def clear_memoization_cache():
    """
    Limpa cache de memoização antes e depois de cada teste.

    Evita efeitos colaterais de cache entre testes, garantindo que cada teste
    execute em estado limpo.
    """
    clear_cache()
    yield
    clear_cache()
