import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from ui.sidebar_filters import (
    get_active_filters,
    CLARITY_LEVELS,
    LANGUAGES,
    PROJECT_TYPES,
    PR_NATURES,
    PAGES,
)
from core.models.analysis_result import AnalysisResult


@pytest.fixture
def sample_analysis_result():
    """Fixture com um resultado de análise completo para testes de filtros."""
    return AnalysisResult(
        id=1,
        html_url="https://github.com/user/repo/pull/1#discussion_r123",
        repo="user/repo",
        path="src/main.py",
        body="This is a test body with sufficient content.",
        diff_hunk="@@ -1,5 +1,10 @@",
        author="testuser",
        author_association="CONTRIBUTOR",
        commit_id="abc123def456",
        line=42,
        language="Python",
        created_at="2024-01-15",
        project_type="library",
        pr_nature="feature",
        clarity_level="good",
        char_count=45,
        word_count=9,
    )


def test_clarity_levels_vocabulary_is_correct():
    """
    Garante que o vocabulário do nível de clareza corresponda exatamente 
    ao que é gerado pela classificação.
    """
    expected_levels = ("excellent", "good", "basic", "insufficient")
    assert (
        CLARITY_LEVELS == expected_levels
    ), "O vocabulário de CLARITY_LEVELS foi alterado e quebrará os filtros."


def test_languages_vocabulary_not_empty():
    """Verifica que a lista de linguagens não está vazia."""
    assert len(LANGUAGES) > 0, "LANGUAGES deve conter pelo menos uma linguagem."
    assert "Python" in LANGUAGES, "Python deveria estar na lista de LANGUAGES."


def test_project_types_vocabulary_not_empty():
    """Verifica que a lista de tipos de projeto não está vazia."""
    assert (
        len(PROJECT_TYPES) > 0
    ), "PROJECT_TYPES deve conter pelo menos um tipo."
    assert "Framework" in PROJECT_TYPES, "Framework deveria estar na lista."


def test_pr_natures_vocabulary_not_empty():
    """Verifica que a lista de naturezas de PR não está vazia."""
    assert (
        len(PR_NATURES) > 0
    ), "PR_NATURES deve conter pelo menos uma natureza."
    assert (
        "bug_fix" in PR_NATURES
    ), "bug_fix deveria estar na lista de PR_NATURES."


def test_pages_vocabulary_not_empty():
    """Verifica que a lista de páginas não está vazia."""
    assert len(PAGES) > 0, "PAGES deve conter pelo menos uma página."
    assert "Upload" in PAGES, "Upload deveria estar na lista de PAGES."


@patch("ui.sidebar_filters.st")
def test_get_active_filters_returns_callable(mock_st):
    """
    Testa se a função consegue ler o session_state do Streamlit mockado
    e construir o predicado composto com sucesso.
    """
    # Simulando retornos vazios/padrões para o session_state
    mock_st.session_state.get.return_value = []

    predicate = get_active_filters()

    # get_active_filters usa compose_predicates/build_filter, que retorna uma função
    assert callable(
        predicate
    ), "A função deve retornar um predicado (função avaliadora)."


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_language_selection(mock_st, sample_analysis_result):
    """
    Testa que um predicado com filtro de linguagem é criado corretamente
    e filtra registros apropriadamente.
    """
    mock_st.session_state = {
        "selected_languages": ("Python",),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Resultado com Python deve passar
    assert (
        predicate(sample_analysis_result) is True
    ), "Registro com Python deveria passar no filtro."

    # Resultado com outra linguagem deve falhar
    other_result = sample_analysis_result._replace(language="Java")
    assert (
        predicate(other_result) is False
    ), "Registro com Java deveria ser filtrado para linguagem Python."


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_clarity_selection(mock_st, sample_analysis_result):
    """
    Testa que um predicado com filtro de clareza funciona corretamente.
    """
    mock_st.session_state = {
        "selected_languages": (),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": ("good", "excellent"),
        "use_date_filter": False,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Resultado com "good" deve passar
    assert predicate(sample_analysis_result) is True

    # Resultado com "basic" deve falhar
    basic_result = sample_analysis_result._replace(clarity_level="basic")
    assert predicate(basic_result) is False


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_project_type_selection(
    mock_st, sample_analysis_result
):
    """
    Testa que um predicado com filtro de tipo de projeto funciona corretamente.
    """
    mock_st.session_state = {
        "selected_languages": (),
        "selected_project_types": ("Library",),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Resultado com "library" deve passar
    assert predicate(sample_analysis_result) is True

    # Resultado com "framework" deve falhar
    other_result = sample_analysis_result._replace(project_type="framework")
    assert predicate(other_result) is False


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_pr_nature_selection(
    mock_st, sample_analysis_result
):
    """
    Testa que um predicado com filtro de natureza de PR funciona corretamente.
    """
    mock_st.session_state = {
        "selected_languages": (),
        "selected_project_types": (),
        "selected_natures": ("feature",),
        "selected_clarity": (),
        "use_date_filter": False,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Resultado com "feature" deve passar
    assert predicate(sample_analysis_result) is True

    # Resultado com "bug_fix" deve falhar
    other_result = sample_analysis_result._replace(pr_nature="bug_fix")
    assert predicate(other_result) is False


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_multiple_criteria(mock_st, sample_analysis_result):
    """
    Testa que múltiplos filtros são aplicados com conjunção lógica (AND).
    Apenas registros que satisfazem TODOS os critérios devem passar.
    """
    mock_st.session_state = {
        "selected_languages": ("Python",),
        "selected_project_types": ("Library",),
        "selected_natures": ("feature",),
        "selected_clarity": ("good",),
        "use_date_filter": False,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Resultado que satisfaz todos os critérios deve passar
    assert predicate(sample_analysis_result) is True

    # Resultado que falha em um critério deve falhar
    fails_language = sample_analysis_result._replace(language="Java")
    assert predicate(fails_language) is False

    fails_clarity = sample_analysis_result._replace(clarity_level="basic")
    assert predicate(fails_clarity) is False

    fails_nature = sample_analysis_result._replace(pr_nature="bug_fix")
    assert predicate(fails_nature) is False


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_no_filters_returns_identity(mock_st):
    """
    Testa que quando nenhum filtro está selecionado, o predicado
    aceita todos os registros (predicado identidade).
    """
    mock_st.session_state = {
        "selected_languages": (),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Qualquer resultado deve passar
    test_result = AnalysisResult(
        id=999,
        html_url="https://example.com",
        repo="any/repo",
        path="any/path.txt",
        body="Any body",
        diff_hunk="@@ -1,1 +1,1 @@",
        author="anyone",
        author_association="OWNER",
        commit_id="xyz789",
        line=1,
        language="Unknown",
        created_at=None,
        project_type="unknown",
        pr_nature="unknown",
        clarity_level="unknown",
        char_count=8,
        word_count=2,
    )

    assert predicate(test_result) is True


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_date_filter_missing_dates(mock_st):
    """
    Testa que quando o filtro de data está habilitado mas as datas não estão
    definidas, o filtro de data não é adicionado aos predicados ativos.
    """
    mock_st.session_state = {
        "selected_languages": (),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": True,
        "start_date": None,
        "end_date": None,
    }
    mock_st.session_state.get = mock_st.session_state.__getitem__

    predicate = get_active_filters()

    # Predicado deve ser criado sem erros mesmo com datas faltando
    assert callable(predicate)