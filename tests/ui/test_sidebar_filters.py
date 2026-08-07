import pytest
from datetime import datetime, date
from unittest.mock import patch, MagicMock
from ui.sidebar_filters import (
    get_active_filters,
    label_formatter,
    CLARITY_LEVELS,
    CLARITY_LEVEL_LABELS,
    LANGUAGES,
    LANGUAGE_LABELS,
    PROJECT_TYPES,
    PROJECT_TYPE_LABELS,
    PR_NATURES,
    PR_NATURE_LABELS,
    PAGES,
    PAGE_LABELS,
)
from core.models.analysis_result import AnalysisResult
from services.ingestion import _EXTENSION_TO_LANGUAGE


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
        language="python",
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
    ao que é gerado pela classificação (CLAUDE.md §8), incluindo o sentinela
    `unknown` de falha do LLM.
    """
    expected_levels = frozenset(
        ("excellent", "good", "basic", "insufficient", "unknown")
    )
    assert (
        frozenset(CLARITY_LEVELS) == expected_levels
    ), "O vocabulário de CLARITY_LEVELS divergiu da §8 e quebrará os filtros."


def test_project_types_vocabulary_is_correct():
    """Garante que os tipos de projeto sejam os valores canônicos da §8."""
    expected_types = frozenset(
        ("library", "web_app", "framework", "cli", "other", "unknown")
    )
    assert (
        frozenset(PROJECT_TYPES) == expected_types
    ), "O vocabulário de PROJECT_TYPES divergiu da §8 e quebrará os filtros."


def test_pr_natures_vocabulary_is_correct():
    """Garante que as naturezas de PR sejam os valores canônicos da §8."""
    expected_natures = frozenset(
        ("bug_fix", "feature", "refactoring", "documentation", "other", "unknown")
    )
    assert (
        frozenset(PR_NATURES) == expected_natures
    ), "O vocabulário de PR_NATURES divergiu da §8 e quebrará os filtros."


def test_languages_vocabulary_matches_extension_map():
    """
    A lista de linguagens da sidebar deve cobrir exatamente o que a ingestão
    infere da extensão do arquivo — nada inalcançável, nada inexistente.
    """
    assert frozenset(LANGUAGES) == frozenset(
        _EXTENSION_TO_LANGUAGE.values()
    ), "LANGUAGES divergiu de _EXTENSION_TO_LANGUAGE."
    assert "rust" in LANGUAGES, "Rust é inferida pela ingestão e deve ser filtrável."


@pytest.mark.parametrize(
    "vocabulary, labels",
    (
        (PROJECT_TYPES, PROJECT_TYPE_LABELS),
        (PR_NATURES, PR_NATURE_LABELS),
        (CLARITY_LEVELS, CLARITY_LEVEL_LABELS),
        (LANGUAGES, LANGUAGE_LABELS),
        (PAGES, PAGE_LABELS),
    ),
)
def test_every_canonical_value_has_a_display_label(vocabulary, labels):
    """Todo valor canônico exibido no sidebar precisa de um rótulo legível."""
    missing = tuple(value for value in vocabulary if value not in labels)
    assert missing == (), f"Valores sem rótulo de exibição: {missing}"


def test_label_formatter_keeps_canonical_value_when_label_is_missing():
    """Um valor sem rótulo cadastrado é exibido como ele mesmo, não quebra a UI."""
    formatter = label_formatter(PROJECT_TYPE_LABELS)

    assert formatter("web_app") == "Aplicação Web"
    assert formatter("brand_new_value") == "brand_new_value"


def test_pages_vocabulary_not_empty():
    """Verifica que a lista de páginas não está vazia.

    `PAGES` guarda chaves estáveis de roteamento, não rótulos: o texto
    visível sai de `PAGE_LABELS`, via `format_func`.
    """
    assert len(PAGES) > 0, "PAGES deve conter pelo menos uma página."
    assert "upload" in PAGES, "upload deveria estar na lista de PAGES."


def test_pages_are_stable_keys_not_visible_labels():
    """Nenhuma rota carrega texto de tela: trocar um rótulo não muda a rota.

    Chave estável é identificador ASCII em minúsculas — sem emoji, sem
    espaço, sem acento. É o que garante que traduzir a interface não quebre
    a navegação.
    """
    unstable = tuple(page for page in PAGES if not page.isascii() or not page.islower())
    assert unstable == (), f"Rotas com texto visível como identificador: {unstable}"


def test_page_label_formatter_translates_route_to_visible_text():
    """O rótulo de tela é derivado da chave, e não o contrário."""
    formatter = label_formatter(PAGE_LABELS)

    assert formatter("upload") == "📂 Upload"
    assert formatter("correlations") == "🔥 Correlação"


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
        "selected_languages": ("python",),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }

    predicate = get_active_filters()

    # Resultado com Python deve passar
    assert (
        predicate(sample_analysis_result) is True
    ), "Registro com Python deveria passar no filtro."

    # Resultado com outra linguagem deve falhar
    other_result = sample_analysis_result._replace(language="java")
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
        "selected_project_types": ("library",),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }

    predicate = get_active_filters()

    # Resultado com "library" deve passar
    assert predicate(sample_analysis_result) is True

    # Resultado com "framework" deve falhar
    other_result = sample_analysis_result._replace(project_type="framework")
    assert predicate(other_result) is False


@patch("ui.sidebar_filters.st")
def test_get_active_filters_with_pr_nature_selection(mock_st, sample_analysis_result):
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
        "selected_languages": ("python",),
        "selected_project_types": ("library",),
        "selected_natures": ("feature",),
        "selected_clarity": ("good",),
        "use_date_filter": False,
    }

    predicate = get_active_filters()

    # Resultado que satisfaz todos os critérios deve passar
    assert predicate(sample_analysis_result) is True

    # Resultado que falha em um critério deve falhar
    fails_language = sample_analysis_result._replace(language="java")
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


def _empty_session_state() -> dict:
    """Session state sem nenhum filtro ativo, base dos testes de round-trip."""
    return {
        "selected_languages": (),
        "selected_project_types": (),
        "selected_natures": (),
        "selected_clarity": (),
        "use_date_filter": False,
    }


@pytest.mark.parametrize("project_type", PROJECT_TYPES)
@patch("ui.sidebar_filters.st")
def test_every_project_type_selection_matches_canonical_record(
    mock_st, project_type, sample_analysis_result
):
    """
    Selecionar qualquer tipo de projeto na sidebar deve casar com registros cujo
    `project_type` é o valor canônico correspondente — inclusive `web_app`, que
    o rótulo "Web App" jamais alcançava.
    """
    mock_st.session_state = {
        **_empty_session_state(),
        "selected_project_types": (project_type,),
    }

    predicate = get_active_filters()

    matching = sample_analysis_result._replace(project_type=project_type)
    assert predicate(matching) is True, f"{project_type} deveria casar consigo mesmo."

    non_matching = sample_analysis_result._replace(project_type="a_value_never_emitted")
    assert predicate(non_matching) is False


@pytest.mark.parametrize("pr_nature", PR_NATURES)
@patch("ui.sidebar_filters.st")
def test_every_pr_nature_selection_matches_canonical_record(
    mock_st, pr_nature, sample_analysis_result
):
    """Idem para a natureza da contribuição, incluindo `other` e `unknown`."""
    mock_st.session_state = {
        **_empty_session_state(),
        "selected_natures": (pr_nature,),
    }

    predicate = get_active_filters()

    matching = sample_analysis_result._replace(pr_nature=pr_nature)
    assert predicate(matching) is True, f"{pr_nature} deveria casar consigo mesmo."

    non_matching = sample_analysis_result._replace(pr_nature="a_value_never_emitted")
    assert predicate(non_matching) is False


@pytest.mark.parametrize("clarity_level", CLARITY_LEVELS)
@patch("ui.sidebar_filters.st")
def test_every_clarity_level_selection_matches_canonical_record(
    mock_st, clarity_level, sample_analysis_result
):
    """Idem para o nível de clareza, incluindo o sentinela `unknown`."""
    mock_st.session_state = {
        **_empty_session_state(),
        "selected_clarity": (clarity_level,),
    }

    predicate = get_active_filters()

    matching = sample_analysis_result._replace(clarity_level=clarity_level)
    assert predicate(matching) is True, f"{clarity_level} deveria casar consigo mesmo."

    non_matching = sample_analysis_result._replace(
        clarity_level="a_value_never_emitted"
    )
    assert predicate(non_matching) is False


@pytest.mark.parametrize("language", LANGUAGES)
@patch("ui.sidebar_filters.st")
def test_every_language_selection_matches_inferred_language(
    mock_st, language, sample_analysis_result
):
    """
    Toda linguagem ofertada na sidebar deve casar com o valor que
    `_infer_language_from_path` produz para ela.
    """
    mock_st.session_state = {
        **_empty_session_state(),
        "selected_languages": (language,),
    }

    predicate = get_active_filters()

    matching = sample_analysis_result._replace(language=language)
    assert predicate(matching) is True, f"{language} deveria casar consigo mesma."

    non_matching = sample_analysis_result._replace(language=None)
    assert predicate(non_matching) is False


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

    predicate = get_active_filters()

    # Predicado deve ser criado sem erros mesmo com datas faltando
    assert callable(predicate)
